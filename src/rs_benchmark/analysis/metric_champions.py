from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import mean

from rs_benchmark.analysis.comparison import successful_results
from rs_benchmark.models import ExperimentResult


@dataclass(frozen=True, slots=True)
class ChampionMetric:
    key: str
    label: str
    maximize: bool


CHAMPION_METRICS = (
    ChampionMetric("registered_images", "已註冊影像數", True),
    ChampionMetric("registration_rate", "註冊率", True),
    ChampionMetric("component_count", "元件數", False),
    ChampionMetric("largest_component_camera_count", "最大元件相機數", True),
    ChampionMetric("sparse_point_count", "稀疏點數", True),
    ChampionMetric("mean_reprojection_error", "重投影誤差", False),
    ChampionMetric("runtime_seconds", "執行時間", False),
)


@dataclass(frozen=True, slots=True)
class ParameterChampion:
    experiment_id: str
    experiment_name: str
    successful_count: int
    total_count: int
    values: dict[str, float | None]
    winning_metrics: tuple[str, ...] = ()


def parameter_champions(results: list[ExperimentResult]) -> list[ParameterChampion]:
    """Select at most one parameter group for each of the seven result metrics."""
    groups: dict[str, list[ExperimentResult]] = {}
    for row in results:
        groups.setdefault(row.experiment_id or row.experiment_name, []).append(row)

    summaries: list[ParameterChampion] = []
    for identifier, rows in groups.items():
        usable = successful_results(rows)
        if not usable:
            continue
        values: dict[str, float | None] = {}
        for metric in CHAMPION_METRICS:
            samples = [
                float(value) for row in usable
                if (value := getattr(row, metric.key)) is not None
                and (metric.key != "component_count" or value >= 1)
            ]
            values[metric.key] = mean(samples) if samples else None
        summaries.append(ParameterChampion(
            experiment_id=identifier,
            experiment_name=rows[0].experiment_name,
            successful_count=len(usable),
            total_count=len(rows),
            values=values,
        ))

    wins: dict[str, list[str]] = {row.experiment_id: [] for row in summaries}
    for metric in CHAMPION_METRICS:
        eligible = [row for row in summaries if row.values[metric.key] is not None]
        if eligible:
            winner = min(eligible, key=lambda row: _rank(row, metric))
            wins[winner.experiment_id].append(metric.key)

    champions = [
        replace(row, winning_metrics=tuple(wins[row.experiment_id]))
        for row in summaries if wins[row.experiment_id]
    ]
    return sorted(champions, key=lambda row: (-len(row.winning_metrics), row.experiment_id))


def _rank(
    row: ParameterChampion, metric: ChampionMetric
) -> tuple[float, float, float, float, str]:
    value = row.values[metric.key]
    assert value is not None
    return (
        -value if metric.maximize else value,
        -_value_or(row.values["registration_rate"], float("-inf")),
        _value_or(row.values["runtime_seconds"], float("inf")),
        _value_or(row.values["component_count"], float("inf")),
        row.experiment_id,
    )


def _value_or(value: float | None, fallback: float) -> float:
    return value if value is not None else fallback
