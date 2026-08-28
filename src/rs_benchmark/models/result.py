from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ExperimentStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    SUCCEEDED = "SUCCESS"  # Backward-compatible alias from phase one.
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    DRY_RUN = "DRY_RUN"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class ExperimentResult:
    """Alignment metrics. Unavailable report values remain ``None``."""

    experiment_name: str
    status: ExperimentStatus = ExperimentStatus.PENDING
    total_images: int | None = None
    registered_images: int | None = None
    component_count: int | None = None
    largest_component_camera_count: int | None = None
    sparse_point_count: int | None = None
    mean_reprojection_error: float | None = None
    runtime_seconds: float | None = None
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None
    experiment_id: str | None = None

    @property
    def number_of_components(self) -> int | None:
        return self.component_count

    @property
    def alignment_runtime_seconds(self) -> float | None:
        return self.runtime_seconds

    @property
    def registration_rate(self) -> float | None:
        if not self.total_images or self.registered_images is None:
            return None
        return self.registered_images / self.total_images

    @property
    def runtime_per_registered_image(self) -> float | None:
        if not self.registered_images or self.runtime_seconds is None:
            return None
        return self.runtime_seconds / self.registered_images

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["registration_rate"] = self.registration_rate
        data["runtime_per_registered_image"] = self.runtime_per_registered_image
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentResult:
        values = dict(data)
        values.pop("registration_rate", None)
        values.pop("runtime_per_registered_image", None)
        if "number_of_components" in values and "component_count" not in values:
            values["component_count"] = values.pop("number_of_components")
        if "alignment_runtime_seconds" in values and "runtime_seconds" not in values:
            values["runtime_seconds"] = values.pop("alignment_runtime_seconds")
        values["status"] = ExperimentStatus(values.get("status", ExperimentStatus.PENDING))
        return cls(**values)
