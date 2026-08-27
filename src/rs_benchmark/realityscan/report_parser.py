from __future__ import annotations

from rs_benchmark.models import ExperimentResult, ExperimentStatus


class ReportParser:
    """Placeholder boundary for the official RealityScan report format.

    Report generation and metric mapping are intentionally deferred until the
    CLI integration phase. Returning optional metrics keeps incomplete output safe.
    """

    def parse(self, experiment_name: str, report_text: str) -> ExperimentResult:
        del report_text
        return ExperimentResult(
            experiment_name=experiment_name,
            status=ExperimentStatus.SUCCEEDED,
        )
