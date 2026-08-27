from pathlib import Path

from rs_benchmark.models import ExperimentConfig
from rs_benchmark.realityscan.commands import RealityScanCommandBuilder


def test_alignment_command_uses_official_cli_keys() -> None:
    command = RealityScanCommandBuilder.alignment_command(
        executable=Path("RealityScan.exe"),
        image_folder=Path("images"),
        project_file=Path("output.rsproj"),
        config=ExperimentConfig(name="Test", max_features_per_image=80_000),
    )

    assert command[0] == "RealityScan.exe"
    assert "sfmFeatureDetectionQuality=High" in command
    assert "sfmMaxFeaturesPerImage=80000" in command
    assert "sfmImagesOverlap=Medium" in command
    assert "sfmMaxFeatureReprojectionError=2.0" in command
    assert command[-3:] == ["-save", "output.rsproj", "-quit"]


def test_command_is_an_argument_list_not_a_shell_string() -> None:
    arguments = RealityScanCommandBuilder.alignment_arguments(
        Path("folder with spaces"),
        Path("output with spaces.rsproj"),
        ExperimentConfig(name="Test"),
    )

    assert "folder with spaces" in arguments
    assert all('"' not in argument for argument in arguments)

