from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from rs_benchmark.realityscan.commands import build_report_export_command, format_command
from rs_benchmark.realityscan.controller import RealityScanController
from rs_benchmark.realityscan.report_parser import ReportParser
from rs_benchmark.realityscan.report_template import ALIGNMENT_REPORT_TEMPLATE

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
