from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ExperimentStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(slots=True)
class ExperimentResult:
    """Alignment metrics. Unavailable report values remain ``None``."""

    experiment_name: str
    status: ExperimentStatus = ExperimentStatus.PENDING
    total_images: int | None = None
    registered_images: int | None = None
    number_of_components: int | None = None
    largest_component_camera_count: int | None = None
    sparse_point_count: int | None = None
    mean_reprojection_error: float | None = None
    alignment_runtime_seconds: float | None = None
    exit_code: int | None = None
    error_message: str | None = None

    @property
    def registration_rate(self) -> float | None:
        if not self.total_images or self.registered_images is None:
            return None
        return self.registered_images / self.total_images

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["registration_rate"] = self.registration_rate
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentResult:
        values = dict(data)
        values.pop("registration_rate", None)
        values["status"] = ExperimentStatus(values.get("status", ExperimentStatus.PENDING))
        return cls(**values)
