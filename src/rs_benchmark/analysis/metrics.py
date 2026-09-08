from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricLeader:
    metric: str
    experiment_ids: list[str]
    experiment_names: list[str]
    value: float | int
    unit: str


@dataclass(frozen=True, slots=True)
class MarginalGain:
    from_experiment_id: str
    to_experiment_id: str
    from_value: object
    to_value: object
    delta_registration_pp: float | None
    delta_runtime_seconds: float | None
    runtime_change_percent: float | None
    registration_gain_per_extra_minute: float | None


@dataclass(frozen=True, slots=True)
class SweepSensitivityResult:
    sweep_id: str
    parameter: str
    points: list[dict[str, Any]]
    marginal_gains: list[MarginalGain]
    observations: list[str]


@dataclass(slots=True)
class BenchmarkAnalysisResult:
    experiment_count: int
    result_count: int
    successful_count: int
    failed_count: int
    total_runtime_seconds: float
    metric_leaders: dict[str, MetricLeader] = field(default_factory=dict)
    pareto_experiment_ids: list[str] = field(default_factory=list)
    pareto_reprojection_experiment_ids: list[str] = field(default_factory=list)
    relative_metrics: list[dict[str, Any]] = field(default_factory=list)
    sweep_analysis: list[SweepSensitivityResult] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
