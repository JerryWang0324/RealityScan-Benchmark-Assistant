from __future__ import annotations

from dataclasses import dataclass

from rs_benchmark.models import ExperimentConfig, ExperimentResult


@dataclass(frozen=True, slots=True)
class RelativeMetrics:
    registration_rate_delta_pp: float | None
    runtime_delta_seconds: float | None
    runtime_ratio: float | None
    reprojection_error_delta: float | None
    sparse_point_delta: int | None


def relative_to_baseline(
    result: ExperimentResult, baseline: ExperimentResult
) -> RelativeMetrics:
    def delta(left: float | int | None, right: float | int | None) -> float | None:
        return None if left is None or right is None else float(left - right)

    registration = delta(result.registration_rate, baseline.registration_rate)
    runtime_ratio = (
        result.runtime_seconds / baseline.runtime_seconds
        if result.runtime_seconds is not None
        and baseline.runtime_seconds is not None
        and baseline.runtime_seconds != 0
        else None
    )
    sparse = delta(result.sparse_point_count, baseline.sparse_point_count)
    return RelativeMetrics(
        registration_rate_delta_pp=registration * 100 if registration is not None else None,
        runtime_delta_seconds=delta(result.runtime_seconds, baseline.runtime_seconds),
        runtime_ratio=runtime_ratio,
        reprojection_error_delta=delta(
            result.mean_reprojection_error, baseline.mean_reprojection_error
        ),
        sparse_point_delta=int(sparse) if sparse is not None else None,
    )


def varied_parameters(experiments: list[ExperimentConfig]) -> list[str]:
    names = (
        "feature_detection_quality", "max_features_per_image", "image_overlap",
        "max_feature_reprojection_error",
    )
    return [name for name in names if len({getattr(item, name) for item in experiments}) > 1]
