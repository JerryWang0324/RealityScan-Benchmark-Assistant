from __future__ import annotations

from collections import defaultdict

from rs_benchmark.analysis.comparison import SUCCESS_STATUSES
from rs_benchmark.analysis.metrics import MarginalGain, SweepSensitivityResult
from rs_benchmark.models import ExperimentConfig, ExperimentResult
from rs_benchmark.reports.sweep_analysis import relative_to_baseline, varied_parameters


def analyze_sweeps(
    experiments: list[ExperimentConfig], results: list[ExperimentResult]
) -> tuple[list[SweepSensitivityResult], list[dict[str, object]]]:
    result_by_id = {row.experiment_id: row for row in results if row.experiment_id}
    groups: dict[str, list[ExperimentConfig]] = defaultdict(list)
    for config in experiments:
        if config.sweep_id:
            groups[config.sweep_id].append(config)

    analyses: list[SweepSensitivityResult] = []
    relative_rows: list[dict[str, object]] = []
    for sweep_id, configs in groups.items():
        baseline_config = next((c for c in configs if c.experiment_role == "BASELINE"), None)
        baseline = result_by_id.get(baseline_config.experiment_id) if baseline_config else None
        if baseline:
            for config in configs:
                result = result_by_id.get(config.experiment_id)
                if not result:
                    continue
                relative = relative_to_baseline(result, baseline)
                relative_rows.append({
                    "sweep_id": sweep_id,
                    "experiment_id": config.experiment_id,
                    "experiment_name": config.name,
                    "registration_rate_delta_pp": relative.registration_rate_delta_pp,
                    "runtime_delta_seconds": relative.runtime_delta_seconds,
                    "runtime_ratio": relative.runtime_ratio,
                    "reprojection_error_delta": relative.reprojection_error_delta,
                    "sparse_point_delta": relative.sparse_point_delta,
                })

        varied = varied_parameters(configs)
        if len(varied) != 1:
            continue
        parameter = varied[0]
        points: list[dict[str, object]] = []
        for config in configs:
            result = result_by_id.get(config.experiment_id)
            if not result or result.status not in SUCCESS_STATUSES:
                continue
            points.append({
                "experiment_id": config.experiment_id,
                "experiment_name": config.name,
                "parameter_value": getattr(config, parameter),
                "registration_rate_percent": (
                    result.registration_rate * 100
                    if result.registration_rate is not None else None
                ),
                "runtime_seconds": result.runtime_seconds,
            })
        points.sort(key=lambda p: _sort_key(p["parameter_value"]))
        gains = [
            _marginal(left, right)
            for left, right in zip(points, points[1:], strict=False)
        ]
        observations = [text for gain in gains if (text := _diminishing_return(gain))]
        analyses.append(SweepSensitivityResult(
            sweep_id=sweep_id,
            parameter=parameter,
            points=points,
            marginal_gains=gains,
            observations=observations,
        ))
    return analyses, relative_rows


def _sort_key(value: object) -> tuple[int, object]:
    return (0, value) if isinstance(value, (int, float)) else (1, str(value))


def _marginal(left: dict[str, object], right: dict[str, object]) -> MarginalGain:
    left_rate = left["registration_rate_percent"]
    right_rate = right["registration_rate_percent"]
    left_runtime = left["runtime_seconds"]
    right_runtime = right["runtime_seconds"]
    delta_rate = (
        float(right_rate) - float(left_rate)
        if left_rate is not None and right_rate is not None else None
    )
    delta_runtime = (
        float(right_runtime) - float(left_runtime)
        if left_runtime is not None and right_runtime is not None else None
    )
    runtime_percent = (
        delta_runtime / float(left_runtime) * 100
        if delta_runtime is not None and left_runtime not in (None, 0) else None
    )
    gain_per_minute = (
        delta_rate / (delta_runtime / 60)
        if delta_rate is not None and delta_runtime is not None and delta_runtime > 0 else None
    )
    return MarginalGain(
        from_experiment_id=str(left["experiment_id"]),
        to_experiment_id=str(right["experiment_id"]),
        from_value=left["parameter_value"],
        to_value=right["parameter_value"],
        delta_registration_pp=delta_rate,
        delta_runtime_seconds=delta_runtime,
        runtime_change_percent=runtime_percent,
        registration_gain_per_extra_minute=gain_per_minute,
    )


def _diminishing_return(gain: MarginalGain) -> str | None:
    if (
        gain.delta_registration_pp is None
        or gain.runtime_change_percent is None
        or gain.delta_runtime_seconds is None
    ):
        return None
    if gain.delta_registration_pp <= 1.0 and gain.runtime_change_percent >= 50:
        return (
            f"參數由 {gain.from_value} 增加至 {gain.to_value} 時，註冊率僅增加 "
            f"{gain.delta_registration_pp:.1f} 個百分點，執行時間增加 "
            f"{gain.runtime_change_percent:.1f}%；此為報酬遞減的描述性跡象。"
        )
    return None
