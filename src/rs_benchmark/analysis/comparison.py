from __future__ import annotations

from collections.abc import Callable

from rs_benchmark.analysis.metrics import MetricLeader
from rs_benchmark.models import ExperimentResult, ExperimentStatus

SUCCESS_STATUSES = {ExperimentStatus.SUCCESS, ExperimentStatus.DRY_RUN}


def successful_results(results: list[ExperimentResult]) -> list[ExperimentResult]:
    return [result for result in results if result.status in SUCCESS_STATUSES]


def metric_leaders(results: list[ExperimentResult]) -> dict[str, MetricLeader]:
    specifications: tuple[
        tuple[str, str, str, Callable[[list[float | int]], float | int]], ...
    ] = (
        ("highest_registration_rate", "registration_rate", "%", max),
        ("fastest_runtime", "runtime_seconds", "s", min),
        ("lowest_reported_reprojection_error", "mean_reprojection_error", "px", min),
        ("highest_sparse_point_count", "sparse_point_count", "points", max),
    )
    leaders: dict[str, MetricLeader] = {}
    usable = successful_results(results)
    for key, attribute, unit, chooser in specifications:
        rows = [(row, getattr(row, attribute)) for row in usable]
        valid = [(row, value) for row, value in rows if value is not None]
        if not valid:
            continue
        target = chooser([value for _, value in valid])
        tied = [row for row, value in valid if value == target]
        identifiers = [_identifier(row) for row in tied]
        leaders[key] = MetricLeader(
            metric=key,
            experiment_ids=_unique(identifiers),
            experiment_names=_unique([row.experiment_name for row in tied]),
            value=target,
            unit=unit,
        )
    return leaders


def _identifier(result: ExperimentResult) -> str:
    return result.experiment_id or result.experiment_name


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))

