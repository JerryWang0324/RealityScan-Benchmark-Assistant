from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

_QUALITY_VALUES = {"High", "Normal"}
_OVERLAP_VALUES = {"Low", "Medium", "High"}


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """User-facing alignment parameters for one experiment.

    RealityScan's CLI key strings intentionally live in ``realityscan.commands``.
    """

    name: str
    feature_detection_quality: str = "High"
    max_features_per_image: int = 40_000
    image_overlap: str = "Medium"
    max_feature_reprojection_error: float = 2.0

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        return cls(**data)
