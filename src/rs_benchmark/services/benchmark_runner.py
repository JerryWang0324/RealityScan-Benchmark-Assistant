from __future__ import annotations

import inspect
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rs_benchmark.analysis import analyze_benchmark
from rs_benchmark.models import (
    BenchmarkProject,
    BenchmarkStatus,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)
from rs_benchmark.models.benchmark import slug
from rs_benchmark.realityscan.controller import RealityScanController
from rs_benchmark.reports import (
    export_reproducibility_package,
    export_results_csv,
    generate_charts,
    generate_html_report,
    generate_pareto_chart,
)
from rs_benchmark.reports.csv_exporter import result_row
from rs_benchmark.reports.sweep_analysis import relative_to_baseline
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner
from rs_benchmark.utils.path_sanitizer import PathDisplaySanitizer

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[["BenchmarkProgress"], None]


@dataclass(frozen=True, slots=True)
class BenchmarkProgress:
    current: int
    total: int
    experiment_name: str
    phase: str
    repeat_index: int = 1
    repeat_count: int = 1

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
        queue = [
            (experiment, repeat_index)
            for experiment in enabled
            for repeat_index in range(1, project.repeat_count + 1)
        ]
        stop_queue = False
        for index, (experiment, repeat_index) in enumerate(queue, start=1):
            if self._cancel_requested.is_set():
                self._append_remaining(
                    project, queue[index - 1 :], ExperimentStatus.CANCELLED, project.repeat_count
                )
                project.status = BenchmarkStatus.CANCELLED
                break
            if stop_queue:
                self._append_remaining(
                    project, queue[index - 1 :], ExperimentStatus.SKIPPED, project.repeat_count
                )
                break

            self._emit(
                progress_callback, index, len(queue), experiment.name, "RUNNING",
                repeat_index, project.repeat_count,
            )
            directory = (
                root / "experiments"
                / f"{index:03d}_{experiment.experiment_id}_repeat_{repeat_index:02d}"
            )
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
            result.experiment_id = experiment.experiment_id
            result.repeat_index = repeat_index
            result.repeat_count = project.repeat_count
            (directory / "result.json").write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            project.results.append(result)
            project.save(root / "benchmark.json")
            self._log(
                root,
                f"Experiment {index}/{len(queue)} {experiment.name} "
                f"repeat {repeat_index}/{project.repeat_count}: {result.status.value}",
            )
            self._emit(
                progress_callback, index, len(queue), experiment.name, "FINISHED",
                repeat_index, project.repeat_count,
            )

            if self._cancel_requested.is_set():
                self._append_remaining(
                    project, queue[index:], ExperimentStatus.CANCELLED, project.repeat_count
                )
                project.status = BenchmarkStatus.CANCELLED
                break
            if project.stop_on_failure and result.status in {
                ExperimentStatus.FAILED,
                ExperimentStatus.TIMEOUT,
            }:
                self._append_remaining(
                    project, queue[index:], ExperimentStatus.SKIPPED, project.repeat_count
                )
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
        definitions = project.metadata.get("sweep_definitions", [])
        if definitions:
            sweeps = root / "sweeps"
            sweeps.mkdir()
            for definition in definitions:
                sweep_id = definition.get("sweep_id", "sweep")
                (sweeps / f"{sweep_id}.json").write_text(
                    json.dumps(definition, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        project.run_directory = root
        return root

    @staticmethod
    def _append_remaining(
        project: BenchmarkProject,
        queue: list[tuple[ExperimentConfig, int]],
        status: ExperimentStatus,
        repeat_count: int,
    ) -> None:
        project.results.extend(
            ExperimentResult(
                experiment_name=experiment.name,
                status=status,
                experiment_id=experiment.experiment_id,
                repeat_index=repeat_index,
                repeat_count=repeat_count,
            )
            for experiment, repeat_index in queue
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
        repeat_index: int = 1,
        repeat_count: int = 1,
    ) -> None:
        if callback:
            callback(
                BenchmarkProgress(
                    current, total, name, phase, repeat_index, repeat_count
                )
            )

    @staticmethod
    def _write_reports(project: BenchmarkProject, root: Path) -> None:
        summary = root / "summary"
        export_results_csv(summary / "results.csv", project.results, project.enabled_experiments)
        analysis = analyze_benchmark(project)
        (summary / "analysis.json").write_text(
            json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        chart_paths = generate_charts(
            summary / "charts", project.results, project.enabled_experiments
        )
        pareto_path = generate_pareto_chart(
            summary / "charts" / "pareto_registration_runtime.png",
            project.results,
        )
        if pareto_path:
            chart_paths.append(pareto_path)
        payload = {
            "benchmark_name": project.name,
            "dataset": PathDisplaySanitizer.sanitize(project.image_folder),
            "experiment_count": len(project.enabled_experiments),
            "repeat_count": project.repeat_count,
            "total_run_count": len(project.enabled_experiments) * project.repeat_count,
            "success_count": analysis.successful_count,
            "failed_count": analysis.failed_count,
            "total_runtime_seconds": analysis.total_runtime_seconds,
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
            "sweep_analysis": analysis.to_dict()["sweep_analysis"],
        }
        (summary / "benchmark_summary.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        generate_html_report(summary / "report.html", project, analysis, chart_paths)
        export_reproducibility_package(
            summary / f"{slug(project.name)}_reproducibility.zip", project, root
        )

    @staticmethod
    def _sweep_analysis(project: BenchmarkProject) -> list[dict[str, object]]:
        results = {item.experiment_id: item for item in project.results if item.experiment_id}
        groups: dict[str, list[ExperimentConfig]] = {}
        for experiment in project.enabled_experiments:
            if experiment.sweep_id:
                groups.setdefault(experiment.sweep_id, []).append(experiment)
        payload: list[dict[str, object]] = []
        for sweep_id, experiments in groups.items():
            baseline_config = next(
                (item for item in experiments if item.experiment_role == "BASELINE"), None
            )
            baseline = results.get(baseline_config.experiment_id) if baseline_config else None
            rows = []
            if baseline:
                for config in experiments:
                    result = results.get(config.experiment_id)
                    if not result:
                        continue
                    relative = relative_to_baseline(result, baseline)
                    rows.append({
                        "experiment_id": config.experiment_id,
                        "experiment_name": config.name,
                        "registration_rate_delta_pp": relative.registration_rate_delta_pp,
                        "runtime_delta_seconds": relative.runtime_delta_seconds,
                        "runtime_ratio": relative.runtime_ratio,
                        "reprojection_error_delta": relative.reprojection_error_delta,
                        "sparse_point_delta": relative.sparse_point_delta,
                    })
            payload.append({
                "sweep_id": sweep_id,
                "mode": experiments[0].sweep_mode,
                "varied_parameters": list(experiments[0].varied_parameters),
                "relative_to_baseline": rows,
            })
        return payload

    @staticmethod
    def _log(root: Path, message: str) -> None:
        with (root / "benchmark.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().astimezone().isoformat()} {message}\n")
