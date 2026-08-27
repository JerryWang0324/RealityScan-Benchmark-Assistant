from __future__ import annotations

from pathlib import Path

from rs_benchmark.models import ExperimentConfig

ALIGNMENT_PARAMETER_KEYS = {
    "feature_detection_quality": "sfmFeatureDetectionQuality",
    "max_features_per_image": "sfmMaxFeaturesPerImage",
    "image_overlap": "sfmImagesOverlap",
    "max_feature_reprojection_error": "sfmMaxFeatureReprojectionError",
}


class RealityScanCommandBuilder:
    """Build argument lists without shell-specific quoting or execution."""

    @staticmethod
    def alignment_arguments(
        image_folder: Path,
        project_file: Path,
        config: ExperimentConfig,
    ) -> list[str]:
        parameter_values = {
            "feature_detection_quality": config.feature_detection_quality,
            "max_features_per_image": config.max_features_per_image,
            "image_overlap": config.image_overlap,
            "max_feature_reprojection_error": config.max_feature_reprojection_error,
        }
        arguments = ["-headless", "-newScene", "-addFolder", str(image_folder)]
        for internal_name, cli_key in ALIGNMENT_PARAMETER_KEYS.items():
            arguments.extend(["-set", f"{cli_key}={parameter_values[internal_name]}"])
        arguments.extend(["-align", "-save", str(project_file), "-quit"])
        return arguments

    @classmethod
    def alignment_command(
        cls,
        executable: Path,
        image_folder: Path,
        project_file: Path,
        config: ExperimentConfig,
    ) -> list[str]:
        return [str(executable), *cls.alignment_arguments(image_folder, project_file, config)]
