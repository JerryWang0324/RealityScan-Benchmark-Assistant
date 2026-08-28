from datetime import UTC, datetime
from pathlib import Path

import pytest

from rs_benchmark.models import (
    BenchmarkProject,
    BenchmarkStatus,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)


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


def test_project_json_round_trip_with_multiple_experiments(tmp_path: Path) -> None:
    project = BenchmarkProject(
        name="建築測試",
        image_folder=tmp_path / "images",
        realityscan_executable=tmp_path / "RealityScan.exe",
        output_directory=tmp_path / "runs",
        experiments=[
            ExperimentConfig(name="預設"),
            ExperimentConfig(name="高特徵數", max_features_per_image=80_000),
        ],
        results=[
            ExperimentResult("預設", ExperimentStatus.SUCCESS, total_images=10, registered_images=9)
        ],
        status=BenchmarkStatus.PARTIAL_SUCCESS,
    )

    restored = BenchmarkProject.from_dict(project.to_dict())

    assert restored.benchmark_id == project.benchmark_id
    assert restored.status is BenchmarkStatus.PARTIAL_SUCCESS
    assert [item.name for item in restored.experiments] == ["預設", "高特徵數"]
    assert restored.results[0].registration_rate == pytest.approx(0.9)


def test_identical_parameters_produce_warning(tmp_path: Path) -> None:
    (tmp_path / "one.jpg").touch()
    project = BenchmarkProject(
        name="測試",
        image_folder=tmp_path,
        experiments=[ExperimentConfig(name="甲"), ExperimentConfig(name="乙")],
    )

    warnings = project.validate()

    assert len(warnings) == 1
    assert '"甲"' in warnings[0] and '"乙"' in warnings[0]
