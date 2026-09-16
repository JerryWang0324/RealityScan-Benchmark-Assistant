from __future__ import annotations

from collections.abc import Callable

from rs_benchmark.analysis.comparison import successful_results
from rs_benchmark.models import ExperimentResult


def registration_runtime_frontier(results: list[ExperimentResult]) -> list[str]:
    """Compare registration, runtime, and component count by Pareto dominance.

    Exact coordinate ties remain non-dominated together because domination requires
    at least one strictly better metric.
    """
    return _identifiers(registration_runtime_frontier_rows(results))


def registration_runtime_frontier_rows(
    results: list[ExperimentResult],
) -> list[ExperimentResult]:
    """Return individual runs on the three-metric Pareto frontier."""
    return _frontier_rows(
        results,
        lambda row: row.registration_rate,
        lambda row: row.runtime_seconds,
    )


def registration_reprojection_frontier(results: list[ExperimentResult]) -> list[str]:
    return _identifiers(_frontier_rows(
        results,
        lambda row: row.registration_rate,
        lambda row: row.mean_reprojection_error,
    ))


def _frontier_rows(
    results: list[ExperimentResult],
    benefit: Callable[[ExperimentResult], float | None],
    cost: Callable[[ExperimentResult], float | None],
) -> list[ExperimentResult]:
    valid = [
        row for row in successful_results(results)
        if benefit(row) is not None and cost(row) is not None
    ]
    if len(valid) < 2:
        return []
    frontier: list[ExperimentResult] = []
    for candidate in valid:
        candidate_benefit = benefit(candidate)
        candidate_cost = cost(candidate)
        dominated = any(
            benefit(other) >= candidate_benefit
            and cost(other) <= candidate_cost
            and _component_cost(other) <= _component_cost(candidate)
            and (
                benefit(other) > candidate_benefit
                or cost(other) < candidate_cost
                or _component_cost(other) < _component_cost(candidate)
            )
            for other in valid
            if other is not candidate
        )
        if not dominated:
            frontier.append(candidate)
    frontier.sort(
        key=lambda row: (
            _component_cost(row), -float(benefit(row)), float(cost(row)),
        )
    )
    return frontier


def _component_cost(row: ExperimentResult) -> float:
    if row.component_count is None or row.component_count < 1:
        return float("inf")
    return float(row.component_count)


def _identifiers(rows: list[ExperimentResult]) -> list[str]:
    identifiers: list[str] = []
    for row in rows:
        identifier = row.experiment_id or row.experiment_name
        if identifier not in identifiers:
            identifiers.append(identifier)
    return identifiers
