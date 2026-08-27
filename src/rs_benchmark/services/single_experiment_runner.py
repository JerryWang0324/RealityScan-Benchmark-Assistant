from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from rs_benchmark.models import ExperimentConfig, ExperimentResult, ExperimentStatus
from rs_benchmark.realityscan.commands import (
    AlignmentOutputPaths,
    build_alignment_command,
    format_command,
)
from rs_benchmark.realityscan.controller import (
    RealityScanController,
    RealityScanControllerProtocol,
    RealityScanError,
)
from rs_benchmark.realityscan.dataset import validate_dataset
from rs_benchmark.realityscan.report_parser import ReportParseError, ReportParser
from rs_benchmark.realityscan.report_template import ALIGNMENT_REPORT_TEMPLATE

LOGGER = logging.getLogger(__name__)
ControllerFactory = Callable[[Path], RealityScanControllerProtocol]


class SingleExperimentRunner:
    """Run one self-contained, reproducible RealityScan alignment experiment."""

    def __init__(
        self,
        controller_factory: ControllerFactory = RealityScanController,
        parser: ReportParser | None = None,
    ) -> None:
        self.controller_factory = controller_factory
        self.parser = parser or ReportParser()
        self.last_experiment_directory: Path | None = None

    def run_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        dataset = validate_dataset(config.image_folder)
        controller = self.controller_factory(config.realityscan_executable)
        controller.validate_executable()

        experiment_directory = self._create_experiment_directory(config)
        self.last_experiment_directory = experiment_directory
        output_paths = self._create_output_paths(experiment_directory)
        output_paths.report_template.write_text(ALIGNMENT_REPORT_TEMPLATE, encoding="utf-8")
        self._write_json(experiment_directory / "config.json", config.to_dict())
        command = build_alignment_command(config, output_paths)
        (experiment_directory / "command.txt").write_text(
            format_command(command) + "\n", encoding="utf-8"
        )

        started = datetime.now().astimezone()
        if config.dry_run:
            result = ExperimentResult(
                experiment_name=config.name,
                status=ExperimentStatus.DRY_RUN,
                total_images=dataset.total_images,
                started_at=started.isoformat(),
                finished_at=datetime.now().astimezone().isoformat(),
            )
            self._write_json(experiment_directory / "result.json", result.to_dict())
            return result

        stdout_path = experiment_directory / "stdout.log"
        stderr_path = experiment_directory / "stderr.log"
        process = None
        result: ExperimentResult
        try:
            process = controller.run_command(command[1:], config.timeout_seconds)
            stdout_path.write_text(process.stdout, encoding="utf-8")
            stderr_path.write_text(process.stderr, encoding="utf-8")
            if process.timed_out:
                result = ExperimentResult(
                    experiment_name=config.name, status=ExperimentStatus.TIMEOUT,
                    total_images=dataset.total_images, runtime_seconds=process.runtime_seconds,
                    exit_code=process.return_code, error_message="RealityScan process timed out",
                )
            elif process.return_code != 0:
                result = ExperimentResult(
                    experiment_name=config.name, status=ExperimentStatus.FAILED,
                    total_images=dataset.total_images, runtime_seconds=process.runtime_seconds,
                    exit_code=process.return_code,
                    error_message=f"RealityScan exited with code {process.return_code}",
                )
            else:
                result = self.parser.parse(output_paths.report_file, config.name)
                result.total_images = dataset.total_images
                result.runtime_seconds = process.runtime_seconds
                result.exit_code = process.return_code
        except (RealityScanError, ReportParseError, OSError) as exc:
            LOGGER.exception("Single alignment experiment failed")
            stdout_path.touch(exist_ok=True)
            with stderr_path.open("a", encoding="utf-8") as stderr_file:
                stderr_file.write(f"\nRSBA runner error: {exc}\n")
            result = ExperimentResult(
                experiment_name=config.name,
                status=ExperimentStatus.FAILED,
                total_images=dataset.total_images,
                runtime_seconds=process.runtime_seconds if process else None,
                exit_code=process.return_code if process else None,
                error_message=str(exc),
            )

        finished = datetime.now().astimezone()
        result.started_at = started.isoformat()
        result.finished_at = finished.isoformat()
        self._write_json(experiment_directory / "result.json", result.to_dict())
        self._write_json(
            experiment_directory / "runtime.json",
            {
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "runtime_seconds": result.runtime_seconds,
                "exit_code": result.exit_code,
                "timed_out": result.status is ExperimentStatus.TIMEOUT,
                "realityscan_version": controller.get_version(),
            },
        )
        return result

    @staticmethod
    def preview_command(config: ExperimentConfig) -> str:
        preview_root = config.output_directory / "experiment_<timestamp>_<name>"
        output = AlignmentOutputPaths(
            project_file=preview_root / "realityscan_output" / "project.rsproj",
            report_file=preview_root / "realityscan_output" / "alignment_report.html",
            report_template=preview_root / "alignment_report_template.html",
            components_directory=preview_root / "realityscan_output" / "components",
            crash_reports_directory=preview_root / "realityscan_output" / "crash_reports",
        )
        return format_command(build_alignment_command(config, output))

    @staticmethod
    def _create_experiment_directory(config: ExperimentConfig) -> Path:
        config.output_directory.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", config.name.strip()).strip("_") or "experiment"
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        candidate = config.output_directory / f"experiment_{stamp}_{slug}"
        suffix = 1
        while candidate.exists():
            candidate = config.output_directory / f"experiment_{stamp}_{slug}_{suffix:02d}"
            suffix += 1
        candidate.mkdir()
        return candidate

    @staticmethod
    def _create_output_paths(experiment_directory: Path) -> AlignmentOutputPaths:
        output = experiment_directory / "realityscan_output"
        components = output / "components"
        crash_reports = output / "crash_reports"
        components.mkdir(parents=True)
        crash_reports.mkdir()
        return AlignmentOutputPaths(
            project_file=output / "project.rsproj",
            report_file=output / "alignment_report.html",
            report_template=experiment_directory / "alignment_report_template.html",
            components_directory=components,
            crash_reports_directory=crash_reports,
        )

    @staticmethod
    def _write_json(path: Path, data: object) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
