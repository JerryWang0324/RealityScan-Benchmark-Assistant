from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_QUALITY_VALUES = {"High", "Normal"}
_OVERLAP_VALUES = {"Low", "Medium", "High"}


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

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Experiment name cannot be empty")
        if self.feature_detection_quality not in _QUALITY_VALUES:
            raise ValueError("Feature detection quality must be High or Normal")
        if self.max_features_per_image <= 0:
            raise ValueError("Max features per image must be positive")
        if self.image_overlap not in _OVERLAP_VALUES:
            raise ValueError("Image overlap must be Low, Medium, or High")
        if self.max_feature_reprojection_error <= 0:
            raise ValueError("Max feature reprojection error must be positive")
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
        return cls(**values)
