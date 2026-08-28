from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from rs_benchmark.realityscan.parameter_schema import PARAMETER_SCHEMA, validate_parameter

SWEEP_WARNING_THRESHOLD = 20
SWEEP_CONFIRM_THRESHOLD = 50


class SweepMode(StrEnum):
    FULL_FACTORIAL = "full_factorial"
    ONE_FACTOR_AT_A_TIME = "one_factor_at_a_time"


@dataclass(frozen=True, slots=True)
class BaselineConfig:
    feature_detection_quality: str = "High"
    max_features_per_image: int = 40_000
    image_overlap: str = "Medium"
    max_feature_reprojection_error: float = 2.0

    def __post_init__(self) -> None:
        for name in PARAMETER_SCHEMA:
            validate_parameter(name, getattr(self, name))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineConfig:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ParameterSweepConfig:
    feature_detection_qualities: list[str]
    max_features_per_image: list[int]
    image_overlaps: list[str]
    max_feature_reprojection_errors: list[float]
    mode: SweepMode = SweepMode.FULL_FACTORIAL
    baseline: BaselineConfig | None = None
    sweep_id: str = field(default_factory=lambda: f"sweep_{uuid4().hex[:10]}")
    generated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", SweepMode(self.mode))
        fields = {
            "feature_detection_quality": self.feature_detection_qualities,
            "max_features_per_image": self.max_features_per_image,
            "image_overlap": self.image_overlaps,
            "max_feature_reprojection_error": self.max_feature_reprojection_errors,
        }
        for name, values in fields.items():
            if not values:
                raise ValueError(f"{name} values cannot be empty")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} values cannot contain duplicates")
            for value in values:
                validate_parameter(name, value)
        if self.mode is SweepMode.ONE_FACTOR_AT_A_TIME and self.baseline is None:
            raise ValueError("OFAT mode requires a baseline configuration")

    @property
    def parameter_values(self) -> dict[str, list[object]]:
        return {
            "feature_detection_quality": list(self.feature_detection_qualities),
            "max_features_per_image": list(self.max_features_per_image),
            "image_overlap": list(self.image_overlaps),
            "max_feature_reprojection_error": list(self.max_feature_reprojection_errors),
        }

    @property
    def experiment_count(self) -> int:
        if self.mode is SweepMode.FULL_FACTORIAL:
            count = 1
            for values in self.parameter_values.values():
                count *= len(values)
            return count
        assert self.baseline is not None
        baseline = self.baseline.to_dict()
        return 1 + sum(
            len({value for value in values if value != baseline[name]})
            for name, values in self.parameter_values.items()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sweep_id": self.sweep_id,
            "mode": self.mode.value,
            "generated_at": self.generated_at,
            "parameters": self.parameter_values,
            "baseline": self.baseline.to_dict() if self.baseline else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParameterSweepConfig:
        parameters = data["parameters"]
        return cls(
            feature_detection_qualities=list(parameters["feature_detection_quality"]),
            max_features_per_image=list(parameters["max_features_per_image"]),
            image_overlaps=list(parameters["image_overlap"]),
            max_feature_reprojection_errors=list(
                parameters["max_feature_reprojection_error"]
            ),
            mode=SweepMode(data.get("mode", SweepMode.FULL_FACTORIAL)),
            baseline=(BaselineConfig.from_dict(data["baseline"]) if data.get("baseline") else None),
            sweep_id=data.get("sweep_id", f"sweep_{uuid4().hex[:10]}"),
            generated_at=data.get("generated_at", datetime.now().astimezone().isoformat()),
        )


@dataclass(slots=True)
class SweepDefinition:
    config: ParameterSweepConfig
    experiment_ids: list[str]
    varied_parameters: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = self.config.to_dict()
        payload["experiment_ids"] = self.experiment_ids
        payload["varied_parameters"] = self.varied_parameters
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SweepDefinition:
        return cls(
            config=ParameterSweepConfig.from_dict(data),
            experiment_ids=list(data.get("experiment_ids", [])),
            varied_parameters=list(data.get("varied_parameters", [])),
        )

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> SweepDefinition:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
