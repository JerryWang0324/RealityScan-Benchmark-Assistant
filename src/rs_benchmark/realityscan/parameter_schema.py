from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    internal_name: str
    cli_key: str
    value_type: type
    allowed_values: tuple[object, ...] = ()
    min_value: float | None = None
    default_value: object | None = None

    def validate(self, value: object) -> None:
        if self.value_type is int and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError(f"{self.internal_name} must be an integer")
        if self.value_type is float and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            raise ValueError(f"{self.internal_name} must be a number")
        if self.value_type is str and not isinstance(value, str):
            raise ValueError(f"{self.internal_name} must be text")
        if self.allowed_values and value not in self.allowed_values:
            allowed = ", ".join(map(str, self.allowed_values))
            raise ValueError(f"{self.internal_name} must be one of: {allowed}")
        if self.min_value is not None and float(value) < self.min_value:
            if self.min_value > 0 and float(value) <= 0:
                raise ValueError(f"{self.internal_name} must be positive")
            raise ValueError(f"{self.internal_name} must be at least {self.min_value:g}")


PARAMETER_SCHEMA: dict[str, ParameterDefinition] = {
    "feature_detection_quality": ParameterDefinition(
        "feature_detection_quality", "sfmFeatureDetectionQuality", str,
        ("High", "Normal"), default_value="High",
    ),
    "max_features_per_image": ParameterDefinition(
        "max_features_per_image", "sfmMaxFeaturesPerImage", int,
        min_value=1, default_value=40_000,
    ),
    "image_overlap": ParameterDefinition(
        "image_overlap", "sfmImagesOverlap", str,
        ("Low", "Medium", "High"), default_value="Medium",
    ),
    "max_feature_reprojection_error": ParameterDefinition(
        "max_feature_reprojection_error", "sfmMaxFeatureReprojectionError", float,
        min_value=0.000001, default_value=2.0,
    ),
}


def validate_parameter(name: str, value: Any) -> None:
    try:
        definition = PARAMETER_SCHEMA[name]
    except KeyError as exc:
        raise ValueError(f"Unknown RealityScan parameter: {name}") from exc
    definition.validate(value)
