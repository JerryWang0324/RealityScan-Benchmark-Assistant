from datetime import UTC, datetime
from pathlib import Path

import pytest

from rs_benchmark.models import BenchmarkProject, ExperimentConfig


def test_missing_image_folder_is_rejected(tmp_path: Path) -> None:
    project = BenchmarkProject(
        name="Missing",
        image_folder=tmp_path / "does-not-exist",
        experiments=[ExperimentConfig(name="Default")],
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        project.validate()


def test_folder_without_supported_images_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")
    project = BenchmarkProject(
        name="Empty",
        image_folder=tmp_path,
        experiments=[ExperimentConfig(name="Default")],
    )

    with pytest.raises(ValueError, match="No supported images"):
        project.validate()


def test_benchmark_folder_creation(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    (images / "one.JPG").touch()
    (images / "two.tiff").touch()
    project = BenchmarkProject(
        name="Building Test",
        image_folder=images,
        experiments=[ExperimentConfig(name="Default")],
        created_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
    )

    run_directory = project.create_run_directory(tmp_path / "runs")

    assert run_directory.name == "2026-08-27_120000_building_test"
    assert (run_directory / "benchmark.json").is_file()
    assert (run_directory / "experiment_001_default" / "config.json").is_file()
    assert (run_directory / "experiment_001_default" / "realityscan_output").is_dir()
    assert (run_directory / "summary" / "charts").is_dir()
