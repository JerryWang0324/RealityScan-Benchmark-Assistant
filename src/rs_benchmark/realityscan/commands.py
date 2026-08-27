from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from rs_benchmark.models import ExperimentConfig

ALIGNMENT_KEYS = {
    "feature_detection_quality": "sfmFeatureDetectionQuality",
    "max_features_per_image": "sfmMaxFeaturesPerImage",
    "image_overlap": "sfmImagesOverlap",
    "max_feature_reprojection_error": "sfmMaxFeatureReprojectionError",
}
ALIGNMENT_PARAMETER_KEYS = ALIGNMENT_KEYS

CLI = {
    "headless": "-headless", "silent": "-silent", "std_console": "-stdConsole",
    "new_scene": "-newScene", "add_folder": "-addFolder", "set": "-set",
    "align": "-align", "save": "-save", "set_min_component_size": "-setMinComponentSize",
    "export_latest_components": "-exportLatestComponents", "export_report": "-exportReport",
    "quit": "-quit",
}


@dataclass(frozen=True, slots=True)
class AlignmentOutputPaths:
    project_file: Path
    report_file: Path
    report_template: Path
    components_directory: Path
    crash_reports_directory: Path


def build_alignment_command(
    config: ExperimentConfig, output_paths: AlignmentOutputPaths
) -> list[str]:
    """Return a shell-free argv list for one complete alignment run."""
    parameter_values = {
        "feature_detection_quality": config.feature_detection_quality,
        "max_features_per_image": config.max_features_per_image,
        "image_overlap": config.image_overlap,
        "max_feature_reprojection_error": config.max_feature_reprojection_error,
    }
    command = [
        str(config.realityscan_executable), CLI["headless"], CLI["silent"],
        str(output_paths.crash_reports_directory), CLI["std_console"], CLI["new_scene"],
        CLI["add_folder"], str(config.image_folder),
    ]
    for internal_name, cli_key in ALIGNMENT_KEYS.items():
        command.extend([CLI["set"], f"{cli_key}={parameter_values[internal_name]}"])
    command.extend([
        CLI["align"], CLI["save"], str(output_paths.project_file),
        CLI["set_min_component_size"], "1", CLI["export_latest_components"],
        str(output_paths.components_directory), CLI["export_report"],
        str(output_paths.report_file), str(output_paths.report_template), CLI["quit"],
    ])
    return command


def format_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


class RealityScanCommandBuilder:
    """Build argument lists without shell-specific quoting or execution."""

    @staticmethod
    def alignment_arguments(
        image_folder: Path,
        project_file: Path,
        config: ExperimentConfig,
    ) -> list[str]:
        return cls_command(Path("RealityScan.exe"), image_folder, project_file, config)[1:]

    @classmethod
    def alignment_command(
        cls,
        executable: Path,
        image_folder: Path,
        project_file: Path,
        config: ExperimentConfig,
    ) -> list[str]:
        return cls_command(executable, image_folder, project_file, config)


def cls_command(
    executable: Path, image_folder: Path, project_file: Path, config: ExperimentConfig
) -> list[str]:
    values = config.to_dict()
    values.update(image_folder=str(image_folder), realityscan_executable=str(executable))
    updated = ExperimentConfig.from_dict(values)
    output = AlignmentOutputPaths(
        project_file=project_file,
        report_file=project_file.with_name("alignment_report.html"),
        report_template=project_file.with_name("alignment_report_template.html"),
        components_directory=project_file.with_name("components"),
        crash_reports_directory=project_file.with_name("crash_reports"),
    )
    return build_alignment_command(updated, output)
