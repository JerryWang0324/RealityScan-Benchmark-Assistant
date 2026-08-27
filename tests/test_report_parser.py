from rs_benchmark.models import ExperimentStatus
from rs_benchmark.realityscan.report_parser import ReportParser


def test_incomplete_report_does_not_crash() -> None:
    result = ReportParser().parse("Default", "incomplete output")

    assert result.status is ExperimentStatus.SUCCEEDED
    assert result.total_images is None
    assert result.mean_reprojection_error is None
