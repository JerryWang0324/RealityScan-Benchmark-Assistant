from __future__ import annotations

from rs_benchmark.models import ExperimentResult


def compare_results(results: list[ExperimentResult]) -> dict[str, ExperimentResult | None]:
    return {
        "highest_registration_rate": _select(results, "registration_rate", max),
        "lowest_runtime": _select(results, "runtime_seconds", min),
        "lowest_reprojection_error": _select(results, "mean_reprojection_error", min),
        "highest_sparse_point_count": _select(results, "sparse_point_count", max),
    }


def _select(
    results: list[ExperimentResult], attribute: str, chooser: object
) -> ExperimentResult | None:
    valid = [result for result in results if getattr(result, attribute) is not None]
    if not valid:
        return None
    return chooser(valid, key=lambda result: getattr(result, attribute))  # type: ignore[operator]
