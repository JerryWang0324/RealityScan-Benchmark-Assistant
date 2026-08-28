from pathlib import Path

from rs_benchmark.models import ExperimentConfig
from rs_benchmark.realityscan.commands import (
    AlignmentOutputPaths,
    build_alignment_command,
    build_report_export_command,
)


def _outputs(root: Path) -> AlignmentOutputPaths:
    return AlignmentOutputPaths(
        project_file=root / "project.rsproj",
        report_file=root / "alignment_report.html",
        report_template=root / "template.html",
        components_directory=root / "components",
        crash_reports_directory=root / "crash reports",
    )


def test_command_uses_official_keys_and_output_paths() -> None:
    config = ExperimentConfig(
        name="Test", image_folder=Path("images"),
        realityscan_executable=Path("RealityScan.exe"), max_features_per_image=80_000,
        feature_detection_quality="Normal", image_overlap="High",
        max_feature_reprojection_error=1.5,
    )
    command = build_alignment_command(config, _outputs(Path("output")))

    assert command[0] == "RealityScan.exe"
    assert "sfmFeatureDetectionQuality=Normal" in command
    assert "sfmMaxFeaturesPerImage=80000" in command
    assert "sfmImagesOverlap=High" in command
    assert "sfmMaxFeatureReprojectionError=1.5" in command
    assert ["-save", "output\\project.rsproj"] == command[
        command.index("-save") : command.index("-save") + 2
    ]
    assert "-exportLatestComponents" in command
    assert "-exportReport" in command
    quit_on_error = command.index("appQuitOnError=true")
    assert command[quit_on_error - 1] == "-set"
    assert quit_on_error < command.index("-newScene")
    assert command[-1] == "-quit"


def test_paths_with_spaces_remain_single_arguments() -> None:
    config = ExperimentConfig(
        name="Spaces", image_folder=Path("folder with spaces"),
        realityscan_executable=Path("Program Files/RealityScan.exe"),
    )
    command = build_alignment_command(config, _outputs(Path("output with spaces")))

    assert "folder with spaces" in command
    assert "output with spaces\\project.rsproj" in command
    assert all('"' not in argument for argument in command)


def test_report_only_command_uses_error_exit_and_argument_list() -> None:
    command = build_report_export_command(
        executable=Path("D:/Epic Games/RealityScan.exe"),
        project_file=Path("existing project/project.rsproj"),
        report_file=Path("new output/report.html"),
        report_template=Path("new output/template.html"),
        crash_reports_directory=Path("new output/crashes"),
    )

    assert command[0] == "D:\\Epic Games\\RealityScan.exe"
    assert command[command.index("-set") + 1] == "appQuitOnError=true"
    assert command[command.index("-load") + 1] == "existing project\\project.rsproj"
    assert command[-1] == "-quit"
    assert all('"' not in argument for argument in command)
