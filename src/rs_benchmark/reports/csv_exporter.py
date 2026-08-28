from __future__ import annotations

import csv
from pathlib import Path

from rs_benchmark.models import ExperimentConfig, ExperimentResult

CSV_FIELDS = (
    "experiment_name",
    "status",
    "feature_detection_quality",
    "max_features_per_image",
    "image_overlap",
    "max_feature_reprojection_error",
    "total_images",
    "registered_images",
    "registration_rate",
    "component_count",
    "largest_component_camera_count",
    "sparse_point_count",
    "mean_reprojection_error",
    "runtime_seconds",
    "runtime_per_registered_image",
)


def result_row(
    result: ExperimentResult, config: ExperimentConfig | None = None
) -> dict[str, object]:
    return {
        "experiment_name": result.experiment_name,
        "status": result.status.value,
        "feature_detection_quality": config.feature_detection_quality if config else None,
        "max_features_per_image": config.max_features_per_image if config else None,
        "image_overlap": config.image_overlap if config else None,
        "max_feature_reprojection_error": (
            config.max_feature_reprojection_error if config else None
        ),
        "total_images": result.total_images,
        "registered_images": result.registered_images,
        "registration_rate": (
            round(result.registration_rate * 100, 6)
            if result.registration_rate is not None else None
        ),
        "component_count": result.component_count,
        "largest_component_camera_count": result.largest_component_camera_count,
        "sparse_point_count": result.sparse_point_count,
        "mean_reprojection_error": result.mean_reprojection_error,
        "runtime_seconds": result.runtime_seconds,
        "runtime_per_registered_image": result.runtime_per_registered_image,
    }


def export_results_csv(
    path: Path,
    results: list[ExperimentResult],
    experiments: list[ExperimentConfig],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    configs = {experiment.name: experiment for experiment in experiments}
    # UTF-8 with BOM keeps Traditional Chinese names readable in Excel.
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            row = result_row(result, configs.get(result.experiment_name))
            writer.writerow({key: "N/A" if value is None else value for key, value in row.items()})
    return path


class CsvExporter:
    """Compatibility-friendly object API for callers that prefer services."""

    export = staticmethod(export_results_csv)


CSVExporter = CsvExporter
