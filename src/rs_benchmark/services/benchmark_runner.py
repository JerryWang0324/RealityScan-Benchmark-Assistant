from __future__ import annotations

import inspect
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rs_benchmark.models import (
    BenchmarkProject,
    BenchmarkStatus,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)
from rs_benchmark.models.benchmark import slug
from rs_benchmark.realityscan.controller import RealityScanController
from rs_benchmark.reports import export_results_csv, generate_charts
from rs_benchmark.reports.csv_exporter import result_row
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[["BenchmarkProgress"], None]


@dataclass(frozen=True, slots=True)
class BenchmarkProgress:
    current: int
    total: int
    experiment_name: str
    phase: str

    @property
    def percent(self) -> int:
        return round((self.current - (1 if self.phase == "RUNNING" else 0)) / self.total * 100)


class BenchmarkRunner:
    """Thin queue orchestrator around the existing SingleExperimentRunner."""

    def __init__(self, single_experiment_runner: SingleExperimentRunner | None = None) -> None:
        self.single_experiment_runner = single_experiment_runner or SingleExperimentRunner()
        self._cancel_requested = threading.Event()

    def cancel(self) -> None:
        """Stop before the next experiment; completed results are never discarded."""
        self._cancel_requested.set()

    def run_benchmark(
        self,
        project: BenchmarkProject,
        progress_callback: ProgressCallback | None = None,
    ) -> BenchmarkProject:
        project.validate(require_executable=True)
        self._cancel_requested.clear()
        project.status = BenchmarkStatus.RUNNING
        project.started_at = datetime.now().astimezone()
        project.finished_at = None
        project.results = []
        project.collect_metadata(
            RealityScanController(project.realityscan_executable).get_version()
        )
        root = self._create_root(project)
        project.save(root / "benchmark.json")
        self._log(root, f"Benchmark started: {project.name}")

        enabled = project.enabled_experiments
        stop_queue = False
        for index, experiment in enumerate(enabled, start=1):
            if self._cancel_requested.is_set():
                self._append_remaining(project, enabled[index - 1 :], ExperimentStatus.CANCELLED)
                project.status = BenchmarkStatus.CANCELLED
                break
            if stop_queue:
                self._append_remaining(project, enabled[index - 1 :], ExperimentStatus.SKIPPED)
                break

            self._emit(progress_callback, index, len(enabled), experiment.name, "RUNNING")
            directory = root / "experiments" / f"{index:03d}_{slug(experiment.name)}"
            config = project.experiment_config(experiment, directory.parent)
            try:
                result = self._run_single(config, directory)
            except Exception as exc:
                LOGGER.exception("Experiment queue item failed unexpectedly")
                result = ExperimentResult(
                    experiment_name=experiment.name,
                    status=ExperimentStatus.FAILED,
                    total_images=project.metadata.get("dataset_image_count"),
                    error_message=str(exc),
                )
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "result.json").write_text(
                    json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
                )
                (directory / "stderr.log").write_text(str(exc), encoding="utf-8")
            project.results.append(result)
            project.save(root / "benchmark.json")
            self._log(
                root,
                f"Experiment {index}/{len(enabled)} {experiment.name}: {result.status.value}",
            )
            self._emit(progress_callback, index, len(enabled), experiment.name, "FINISHED")

            if self._cancel_requested.is_set():
                self._append_remaining(project, enabled[index:], ExperimentStatus.CANCELLED)
                project.status = BenchmarkStatus.CANCELLED
                break
            if project.stop_on_failure and result.status in {
                ExperimentStatus.FAILED,
                ExperimentStatus.TIMEOUT,
            }:
                self._append_remaining(project, enabled[index:], ExperimentStatus.SKIPPED)
                stop_queue = True
                break

        if project.status is not BenchmarkStatus.CANCELLED:
            project.status = self._final_status(project.results)
        project.finished_at = datetime.now().astimezone()
        project.save(root / "benchmark.json")
        try:
            self._write_reports(project, root)
        except Exception:
            self._log(root, "Report generation failed; final benchmark.json was preserved")
            raise
        project.save(root / "benchmark.json")
        self._log(root, f"Benchmark finished: {project.status.value}")
        return project

    def _run_single(self, config: ExperimentConfig, directory: Path) -> ExperimentResult:
        method = self.single_experiment_runner.run_experiment
        try:
            parameters = inspect.signature(method).parameters
        except (TypeError, ValueError):
            parameters = {}
        if len(parameters) >= 2 or any(
            parameter.kind is inspect.Parameter.VAR_POSITIONAL
            for parameter in parameters.values()
        ):
            return method(config, directory)
        # Supports minimal Phase 3 test doubles exposing run_experiment(config).
        return method(config)

    @staticmethod
    def _create_root(project: BenchmarkProject) -> Path:
        base = project.output_directory / f"{slug(project.name)}_{project.started_at:%Y%m%d_%H%M%S}"
        root = base
        suffix = 1
        while root.exists():
            root = Path(f"{base}_{suffix:02d}")
            suffix += 1
        (root / "experiments").mkdir(parents=True)
        (root / "summary" / "charts").mkdir(parents=True)
        project.run_directory = root
        return root

    @staticmethod
    def _append_remaining(
        project: BenchmarkProject,
        experiments: list[ExperimentConfig],
        status: ExperimentStatus,
    ) -> None:
        project.results.extend(
            ExperimentResult(experiment_name=experiment.name, status=status)
            for experiment in experiments
        )

    @staticmethod
    def _final_status(results: list[ExperimentResult]) -> BenchmarkStatus:
        statuses = {result.status for result in results}
        failures = statuses & {ExperimentStatus.FAILED, ExperimentStatus.TIMEOUT}
        successes = statuses & {ExperimentStatus.SUCCESS, ExperimentStatus.DRY_RUN}
        if failures and successes:
            return BenchmarkStatus.PARTIAL_SUCCESS
        if failures:
            return BenchmarkStatus.FAILED
        return BenchmarkStatus.COMPLETED

    @staticmethod
    def _emit(
        callback: ProgressCallback | None,
        current: int,
        total: int,
        name: str,
        phase: str,
    ) -> None:
        if callback:
            callback(BenchmarkProgress(current, total, name, phase))

    @staticmethod
    def _write_reports(project: BenchmarkProject, root: Path) -> None:
        summary = root / "summary"
        export_results_csv(summary / "results.csv", project.results, project.enabled_experiments)
        generate_charts(summary / "charts", project.results)
        success_count = sum(
            result.status in {ExperimentStatus.SUCCESS, ExperimentStatus.DRY_RUN}
            for result in project.results
        )
        failed_count = sum(
            result.status in {ExperimentStatus.FAILED, ExperimentStatus.TIMEOUT}
            for result in project.results
        )
        payload = {
            "benchmark_name": project.name,
            "dataset": str(project.image_folder),
            "experiment_count": len(project.enabled_experiments),
            "success_count": success_count,
            "failed_count": failed_count,
            "total_runtime_seconds": sum(
                result.runtime_seconds or 0 for result in project.results
            ),
            "status": project.status.value,
            "results": [
                result_row(
                    result,
                    next(
                        (
                            item for item in project.enabled_experiments
                            if item.name == result.experiment_name
                        ),
                        None,
                    ),
                )
                for result in project.results
            ],
        }
        (summary / "benchmark_summary.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _log(root: Path, message: str) -> None:
        with (root / "benchmark.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().astimezone().isoformat()} {message}\n")
