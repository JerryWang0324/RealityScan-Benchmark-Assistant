from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rs_benchmark.models import ExperimentResult, ExperimentStatus


class ReportParseError(ValueError):
    """Raised for an empty or unrecognized RealityScan report."""


@dataclass(slots=True)
class _Component:
    cameras: int | None = None
    points: int | None = None
    mean_error: float | None = None


class ReportParser:
    """Parse the stable RSBA markers emitted by our custom RealityScan template."""

    def parse(self, path: Path, experiment_name: str | None = None) -> ExperimentResult:
        report_path = Path(path)
        try:
            text = report_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise ReportParseError(f"Unable to read report: {report_path}: {exc}") from exc
        if not text.strip():
            raise ReportParseError(f"Alignment report is empty: {report_path}")
        if "RSBA_" not in text:
            raise ReportParseError(f"Unrecognized alignment report format: {report_path}")

        project: dict[str, str] = {}
        components: dict[str, _Component] = {}
        for marker, payload in re.findall(r"RSBA_([A-Z_]+)\|([^<\r\n]+)", text):
            fields = self._fields(payload)
            if marker == "PROJECT":
                project.update(fields)
            elif marker in {"COMPONENT_INFO", "COMPONENT_STATS"}:
                component_id = fields.get("id", "").strip()
                if not component_id:
                    continue
                component = components.setdefault(component_id, _Component())
                if marker == "COMPONENT_INFO":
                    component.cameras = self._integer(fields.get("cameras"))
                    component.points = self._integer(fields.get("points"))
                else:
                    component.mean_error = self._float(fields.get("mean_error"))

        total_images = self._integer(project.get("total_images"))
        component_count = self._integer(project.get("component_count"))
        if component_count is None and components:
            component_count = len(components)
        camera_counts = [item.cameras for item in components.values() if item.cameras is not None]
        registered_images = sum(camera_counts) if camera_counts else None
        largest = max(
            components.values(), key=lambda item: item.cameras if item.cameras is not None else -1,
            default=None,
        )
        return ExperimentResult(
            experiment_name=experiment_name or report_path.stem,
            status=ExperimentStatus.SUCCESS,
            total_images=total_images,
            registered_images=registered_images,
            component_count=component_count,
            largest_component_camera_count=largest.cameras if largest else None,
            sparse_point_count=largest.points if largest else None,
            mean_reprojection_error=largest.mean_error if largest else None,
        )

    @staticmethod
    def _fields(payload: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for part in payload.split("|"):
            if "=" in part:
                key, value = part.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    @staticmethod
    def _integer(value: str | None) -> int | None:
        try:
            return int(value) if value is not None and value != "" else None
        except ValueError:
            return None

    @staticmethod
    def _float(value: str | None) -> float | None:
        try:
            return float(value) if value is not None and value != "" else None
        except ValueError:
            return None
