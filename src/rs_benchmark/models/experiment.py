from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from rs_benchmark.realityscan.parameter_schema import validate_parameter


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """User-facing alignment parameters for one experiment.

    RealityScan's CLI key strings intentionally live in ``realityscan.commands``.
    """

    name: str
    image_folder: Path = Path()
    realityscan_executable: Path = Path()
    feature_detection_quality: str = "High"
    max_features_per_image: int = 40_000
    image_overlap: str = "Medium"
    max_feature_reprojection_error: float = 2.0
    output_directory: Path = Path("benchmark_runs")
    timeout_seconds: float | None = None
    dry_run: bool = False
    enabled: bool = True
    experiment_id: str = field(default_factory=lambda: f"exp_{uuid4().hex[:12]}")
    machine_name: str = ""
    experiment_role: str = "MANUAL"
    sweep_id: str | None = None
    sweep_mode: str | None = None
    generated_at: str | None = None
    baseline_config: dict[str, object] | None = None
    varied_parameters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Experiment name cannot be empty")
        if not self.experiment_id.strip():
            raise ValueError("Experiment ID cannot be empty")
        validate_parameter("feature_detection_quality", self.feature_detection_quality)
        validate_parameter("max_features_per_image", self.max_features_per_image)
        validate_parameter("image_overlap", self.image_overlap)
        validate_parameter(
            "max_feature_reprojection_error", self.max_feature_reprojection_error
        )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "image_folder": str(self.image_folder),
            "realityscan_executable": str(self.realityscan_executable),
            "feature_detection_quality": self.feature_detection_quality,
            "max_features_per_image": self.max_features_per_image,
            "image_overlap": self.image_overlap,
            "max_feature_reprojection_error": self.max_feature_reprojection_error,
            "output_directory": str(self.output_directory),
            "timeout_seconds": self.timeout_seconds,
            "dry_run": self.dry_run,
            "enabled": self.enabled,
            "experiment_id": self.experiment_id,
            "machine_name": self.machine_name,
            "experiment_role": self.experiment_role,
            "sweep_id": self.sweep_id,
            "sweep_mode": self.sweep_mode,
            "generated_at": self.generated_at,
            "baseline_config": self.baseline_config,
            "varied_parameters": list(self.varied_parameters),
        }

    @property
    def parameter_signature(self) -> tuple[object, ...]:
        return (
            self.feature_detection_quality,
            self.max_features_per_image,
            self.image_overlap,
            self.max_feature_reprojection_error,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        values = dict(data)
        for key in ("image_folder", "realityscan_executable", "output_directory"):
            if key in values:
                values[key] = Path(values[key])
        values["varied_parameters"] = tuple(values.get("varied_parameters", ()))
        return cls(**values)
