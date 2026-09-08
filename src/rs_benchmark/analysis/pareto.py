from __future__ import annotations

from collections.abc import Callable

from rs_benchmark.analysis.comparison import successful_results
from rs_benchmark.models import ExperimentResult


def registration_runtime_frontier(results: list[ExperimentResult]) -> list[str]:
    """Return every non-dominated ID for registration up and runtime down.

    Exact coordinate ties remain non-dominated together because domination requires
    at least one strictly better metric.
    """
    return _frontier(
        results,
        lambda row: row.registration_rate,
        lambda row: row.runtime_seconds,
    )


def registration_reprojection_frontier(results: list[ExperimentResult]) -> list[str]:
    return _frontier(
        results,
        lambda row: row.registration_rate,
        lambda row: row.mean_reprojection_error,
    )


def _frontier(
    results: list[ExperimentResult],
    benefit: Callable[[ExperimentResult], float | None],
    cost: Callable[[ExperimentResult], float | None],
) -> list[str]:
    valid = [
        row for row in successful_results(results)
        if benefit(row) is not None and cost(row) is not None
    ]
    if len(valid) < 2:
        return []
    frontier: list[str] = []
    for candidate in valid:
        candidate_benefit = benefit(candidate)
        candidate_cost = cost(candidate)
        dominated = any(
            benefit(other) >= candidate_benefit
            and cost(other) <= candidate_cost
            and (
                benefit(other) > candidate_benefit
                or cost(other) < candidate_cost
            )
            for other in valid
            if other is not candidate
        )
        if not dominated:
            identifier = candidate.experiment_id or candidate.experiment_name
            if identifier not in frontier:
                frontier.append(identifier)
    return frontier

