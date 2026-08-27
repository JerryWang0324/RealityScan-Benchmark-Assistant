from pathlib import Path

import pytest

from rs_benchmark.models import ExperimentStatus
from rs_benchmark.realityscan.report_parser import ReportParseError, ReportParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_complete_report() -> None:
    result = ReportParser().parse(FIXTURES / "sample_alignment_report.html", "Default")

    assert result.status is ExperimentStatus.SUCCESS
    assert result.total_images == 10
    assert result.registered_images == 9
    assert result.registration_rate == pytest.approx(0.9)
    assert result.component_count == 2
    assert result.largest_component_camera_count == 7
    assert result.sparse_point_count == 1200
    assert result.mean_reprojection_error == pytest.approx(0.64)


def test_missing_fields_are_none() -> None:
    result = ReportParser().parse(FIXTURES / "sample_alignment_report_missing.html")
    assert result.registered_images == 8
    assert result.sparse_point_count is None
    assert result.mean_reprojection_error is None


@pytest.mark.parametrize(
    "name", ["sample_alignment_report_malformed.html", "sample_alignment_report_empty.html"]
)
def test_malformed_and_empty_reports_have_clear_error(name: str) -> None:
    with pytest.raises(ReportParseError):
        ReportParser().parse(FIXTURES / name)
