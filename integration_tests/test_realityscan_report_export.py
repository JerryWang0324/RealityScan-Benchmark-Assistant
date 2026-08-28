from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from rs_benchmark.models import BenchmarkProject, ExperimentConfig, ExperimentStatus
from rs_benchmark.realityscan.commands import build_report_export_command, format_command
from rs_benchmark.realityscan.controller import RealityScanController
from rs_benchmark.realityscan.report_parser import ReportParser
from rs_benchmark.realityscan.report_template import ALIGNMENT_REPORT_TEMPLATE
from rs_benchmark.services.benchmark_runner import BenchmarkRunner
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner

pytestmark = pytest.mark.integration


def _required_path(variable: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        pytest.skip(f"Set {variable} to opt in to the real RealityScan integration test")
    path = Path(value)
    if not path.exists():
        pytest.fail(f"{variable} does not exist: {path}")
    return path


def test_realityscan_22_report_only_export() -> None:
    if os.environ.get("RSBA_RUN_REALITYSCAN_INTEGRATION") != "1":
        pytest.skip("Set RSBA_RUN_REALITYSCAN_INTEGRATION=1 to run RealityScan")

    executable = _required_path("RSBA_INTEGRATION_EXECUTABLE")
    project = _required_path("RSBA_INTEGRATION_PROJECT")
    output_value = os.environ.get("RSBA_INTEGRATION_OUTPUT_DIRECTORY")
    if not output_value:
        pytest.fail("Set RSBA_INTEGRATION_OUTPUT_DIRECTORY to a dedicated output directory")
    output = Path(output_value)
    output.mkdir(parents=True, exist_ok=True)
    crashes = output / "crash_reports"
    crashes.mkdir(exist_ok=True)
    template = output / "alignment_report_template.html"
    report = output / "alignment_report.html"
    template.write_text(ALIGNMENT_REPORT_TEMPLATE, encoding="utf-8")

    command = build_report_export_command(executable, project, report, template, crashes)
    (output / "command.txt").write_text(format_command(command) + "\n", encoding="utf-8")
    controller = RealityScanController(executable)
    process = controller.run_command(command[1:], timeout_seconds=120)
    (output / "stdout.log").write_text(process.stdout, encoding="utf-8")
    (output / "stderr.log").write_text(process.stderr, encoding="utf-8")

    assert process.timed_out is False
    assert process.return_code == 0
    assert report.is_file()
    assert report.stat().st_size > 0
    report_text = report.read_text(encoding="utf-8-sig")
    assert "RSBA_PROJECT" in report_text
    assert "RSBA_COMPONENT_INFO" in report_text
    result = ReportParser().parse(report, "RealityScan 2.2 report-only integration")
    (output / "runtime.json").write_text(
        json.dumps(
            {
                "return_code": process.return_code,
                "runtime_seconds": process.runtime_seconds,
                "timed_out": process.timed_out,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output / "parsed_result.json").write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert result.total_images == 68
    assert result.registered_images is not None
    assert result.component_count is not None


def test_two_experiment_alignment_benchmark() -> None:
    if os.environ.get("RSBA_RUN_REALITYSCAN_BENCHMARK_INTEGRATION") != "1":
        pytest.skip("Set RSBA_RUN_REALITYSCAN_BENCHMARK_INTEGRATION=1 to run two alignments")
    executable = _required_path("RSBA_INTEGRATION_EXECUTABLE")
    images = _required_path("RSBA_INTEGRATION_IMAGE_FOLDER")
    output = _required_path("RSBA_INTEGRATION_OUTPUT_DIRECTORY")
    project = BenchmarkProject(
        name="integration_two_experiments",
        image_folder=images,
        realityscan_executable=executable,
        output_directory=output,
        experiments=[
            ExperimentConfig(name="Default"),
            ExperimentConfig(name="High Features", max_features_per_image=80_000),
        ],
    )

    completed = BenchmarkRunner().run_benchmark(project)

    assert len(completed.results) == 2
    assert completed.run_directory is not None
    assert (completed.run_directory / "summary" / "results.csv").is_file()
    assert (completed.run_directory / "summary" / "charts" / "registration_rate.png").is_file()


def test_single_experiment_uses_cold_isolated_cache() -> None:
    if os.environ.get("RSBA_RUN_REALITYSCAN_CACHE_INTEGRATION") != "1":
        pytest.skip("Set RSBA_RUN_REALITYSCAN_CACHE_INTEGRATION=1 to verify cold cache")
    executable = _required_path("RSBA_INTEGRATION_EXECUTABLE")
    images = _required_path("RSBA_INTEGRATION_IMAGE_FOLDER")
    output = _required_path("RSBA_INTEGRATION_OUTPUT_DIRECTORY")
    runner = SingleExperimentRunner()

    result = runner.run_experiment(
        ExperimentConfig(
            name="cold_cache_validation",
            image_folder=images,
            realityscan_executable=executable,
            output_directory=output,
        )
    )

    assert result.status is ExperimentStatus.SUCCESS
    assert runner.last_experiment_directory is not None
    stdout = (runner.last_experiment_directory / "stdout.log").read_text(encoding="utf-8")
    alignment_section = stdout.split("Executing command 'align'", 1)[1].split(
        "Finalizing", 1
    )[0]
    assert "Detected " in alignment_section
    assert "Feature detection completed in 0 seconds." not in alignment_section
    policy = json.loads(
        (runner.last_experiment_directory / "cache_policy.json").read_text(encoding="utf-8")
    )
    assert policy["strategy"] == "isolated_process_temp"
    assert not Path(policy["cache_directory"]).exists()
