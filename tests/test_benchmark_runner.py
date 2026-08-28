from __future__ import annotations

from pathlib import Path

from rs_benchmark.models import (
    BenchmarkProject,
    BenchmarkStatus,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)
from rs_benchmark.services.benchmark_runner import BenchmarkRunner


class FakeSingleRunner:
    def __init__(self, statuses: dict[str, ExperimentStatus] | None = None) -> None:
        self.statuses = statuses or {}
        self.calls: list[str] = []

    def run_experiment(self, config: ExperimentConfig, directory: Path) -> ExperimentResult:
        self.calls.append(config.name)
        directory.mkdir(parents=True)
        return ExperimentResult(
            experiment_name=config.name,
            status=self.statuses.get(config.name, ExperimentStatus.SUCCESS),
            total_images=10,
            registered_images=9,
            component_count=1,
            sparse_point_count=100,
            mean_reprojection_error=0.5,
            runtime_seconds=2.0,
        )


def project(tmp_path: Path, **updates: object) -> BenchmarkProject:
    images = tmp_path / "images"
    images.mkdir()
    (images / "one.jpg").touch()
    executable = tmp_path / "RealityScan.exe"
    executable.touch()
    values = {
        "name": "queue",
        "image_folder": images,
        "realityscan_executable": executable,
        "output_directory": tmp_path / "runs",
        "experiments": [
            ExperimentConfig(name="A"),
            ExperimentConfig(name="B", max_features_per_image=50_000),
            ExperimentConfig(name="C", max_features_per_image=60_000),
        ],
    }
    values.update(updates)
    return BenchmarkProject(**values)  # type: ignore[arg-type]


def test_three_successes_generate_complete_summary(tmp_path: Path) -> None:
    fake = FakeSingleRunner()
    result = BenchmarkRunner(fake).run_benchmark(project(tmp_path))  # type: ignore[arg-type]

    assert result.status is BenchmarkStatus.COMPLETED
    assert fake.calls == ["A", "B", "C"]
    assert result.run_directory is not None
    assert (result.run_directory / "benchmark.json").is_file()
    assert (result.run_directory / "summary" / "results.csv").is_file()
    assert (result.run_directory / "summary" / "benchmark_summary.json").is_file()


def test_failure_isolated_and_queue_continues(tmp_path: Path) -> None:
    fake = FakeSingleRunner({"B": ExperimentStatus.FAILED})
    result = BenchmarkRunner(fake).run_benchmark(project(tmp_path))  # type: ignore[arg-type]

    assert fake.calls == ["A", "B", "C"]
    assert result.status is BenchmarkStatus.PARTIAL_SUCCESS


def test_stop_on_failure_marks_remaining_skipped(tmp_path: Path) -> None:
    fake = FakeSingleRunner({"B": ExperimentStatus.FAILED})
    result = BenchmarkRunner(fake).run_benchmark(  # type: ignore[arg-type]
        project(tmp_path, stop_on_failure=True)
    )

    assert fake.calls == ["A", "B"]
    assert result.results[-1].status is ExperimentStatus.SKIPPED


def test_disabled_experiment_is_not_called(tmp_path: Path) -> None:
    experiments = [ExperimentConfig(name="停用", enabled=False), ExperimentConfig(name="啟用")]
    fake = FakeSingleRunner()
    result = BenchmarkRunner(fake).run_benchmark(  # type: ignore[arg-type]
        project(tmp_path, experiments=experiments)
    )

    assert fake.calls == ["啟用"]
    assert [item.experiment_name for item in result.results] == ["啟用"]


def test_cancel_after_current_preserves_result_and_stops_queue(tmp_path: Path) -> None:
    fake = FakeSingleRunner()
    runner = BenchmarkRunner(fake)  # type: ignore[arg-type]

    def progress(update) -> None:  # type: ignore[no-untyped-def]
        if update.current == 1 and update.phase == "RUNNING":
            runner.cancel()

    result = runner.run_benchmark(project(tmp_path), progress)

    assert fake.calls == ["A"]
    assert result.status is BenchmarkStatus.CANCELLED
    assert result.results[0].status is ExperimentStatus.SUCCESS
    assert [item.status for item in result.results[1:]] == [
        ExperimentStatus.CANCELLED,
        ExperimentStatus.CANCELLED,
    ]


def test_benchmark_dry_run_prepares_every_command_without_realityscan(tmp_path: Path) -> None:
    completed = BenchmarkRunner().run_benchmark(project(tmp_path, dry_run=True))

    assert completed.status is BenchmarkStatus.COMPLETED
    assert all(item.status is ExperimentStatus.DRY_RUN for item in completed.results)
    assert completed.run_directory is not None
    directories = sorted((completed.run_directory / "experiments").iterdir())
    assert len(directories) == 3
    assert all((directory / "command.txt").is_file() for directory in directories)
    assert all((directory / "result.json").is_file() for directory in directories)
