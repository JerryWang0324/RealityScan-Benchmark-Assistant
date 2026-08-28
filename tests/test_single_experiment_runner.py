import json
from pathlib import Path
from typing import Any

from rs_benchmark.models import ExperimentConfig, ExperimentStatus
from rs_benchmark.realityscan.controller import ProcessResult
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner


class FakeController:
    def __init__(
        self,
        executable: Path,
        return_code: int | None = 0,
        *,
        timed_out: bool = False,
        empty_report: bool = False,
    ) -> None:
        self.executable = executable
        self.return_code = return_code
        self.timed_out = timed_out
        self.empty_report = empty_report
        self.was_run = False

    def validate_executable(self) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(self.executable)

    def get_version(self) -> str | None:
        return "1.5-test"

    def run_command(
        self, arguments: list[str], timeout_seconds: float | None = None
    ) -> ProcessResult:
        del timeout_seconds
        self.was_run = True
        if self.return_code == 0 and not self.timed_out:
            report = Path(arguments[arguments.index("-exportReport") + 1])
            fixture = Path(__file__).parent / "fixtures" / "sample_alignment_report.html"
            report_text = "" if self.empty_report else fixture.read_text(encoding="utf-8")
            report.write_text(report_text, encoding="utf-8")
        return ProcessResult(
            command=(str(self.executable), *arguments), return_code=self.return_code,
            stdout="fake stdout", stderr="fake stderr", runtime_seconds=1.25,
            timed_out=self.timed_out,
        )


def _config(tmp_path: Path, **updates: Any) -> ExperimentConfig:
    images = tmp_path / "images"
    images.mkdir()
    (images / "one.jpg").touch()
    executable = tmp_path / "RealityScan.exe"
    executable.touch()
    values: dict[str, Any] = {
        "name": "Default", "image_folder": images,
        "realityscan_executable": executable, "output_directory": tmp_path / "runs",
    }
    values.update(updates)
    return ExperimentConfig(**values)


def test_success_creates_complete_artifacts(tmp_path: Path) -> None:
    fake = FakeController(tmp_path / "RealityScan.exe")
    runner = SingleExperimentRunner(controller_factory=lambda _: fake)
    result = runner.run_experiment(_config(tmp_path))
    directory = runner.last_experiment_directory

    assert result.status is ExperimentStatus.SUCCESS
    assert result.total_images == 1  # Dataset validation is authoritative.
    assert directory is not None
    artifact_names = (
        "config.json", "command.txt", "stdout.log", "stderr.log", "result.json", "runtime.json"
    )
    for name in artifact_names:
        assert (directory / name).is_file()
    assert (directory / "realityscan_output" / "alignment_report.html").is_file()
    saved_result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert saved_result["status"] == "SUCCESS"


def test_failed_process_still_leaves_result_and_logs(tmp_path: Path) -> None:
    fake = FakeController(tmp_path / "RealityScan.exe", return_code=4)
    runner = SingleExperimentRunner(controller_factory=lambda _: fake)
    result = runner.run_experiment(_config(tmp_path))
    directory = runner.last_experiment_directory

    assert result.status is ExperimentStatus.FAILED
    assert result.exit_code == 4
    assert directory is not None
    assert (directory / "stdout.log").read_text(encoding="utf-8") == "fake stdout"
    stderr = (directory / "stderr.log").read_text(encoding="utf-8")
    assert "fake stderr" in stderr
    assert "RealityScan exited with code 4" in stderr
    assert (directory / "result.json").is_file()


def test_dry_run_validates_and_builds_but_does_not_execute(tmp_path: Path) -> None:
    fake = FakeController(tmp_path / "RealityScan.exe")
    runner = SingleExperimentRunner(controller_factory=lambda _: fake)
    result = runner.run_experiment(_config(tmp_path, dry_run=True))
    directory = runner.last_experiment_directory

    assert result.status is ExperimentStatus.DRY_RUN
    assert fake.was_run is False
    assert directory is not None
    assert (directory / "config.json").is_file()
    assert (directory / "command.txt").is_file()
    assert (directory / "result.json").is_file()


def test_timeout_creates_result_runtime_and_logs(tmp_path: Path) -> None:
    fake = FakeController(tmp_path / "RealityScan.exe", return_code=None, timed_out=True)
    runner = SingleExperimentRunner(controller_factory=lambda _: fake)
    result = runner.run_experiment(_config(tmp_path, timeout_seconds=10))
    directory = runner.last_experiment_directory

    assert result.status is ExperimentStatus.TIMEOUT
    assert result.error_message == "RealityScan process timed out"
    assert directory is not None
    assert (directory / "result.json").is_file()
    assert (directory / "runtime.json").is_file()
    assert "timed out" in (directory / "stderr.log").read_text(encoding="utf-8")


def test_empty_report_marks_saved_alignment_as_failed(tmp_path: Path) -> None:
    fake = FakeController(tmp_path / "RealityScan.exe", empty_report=True)
    runner = SingleExperimentRunner(controller_factory=lambda _: fake)
    config = _config(tmp_path)

    original_run_command = fake.run_command

    def run_and_create_project(
        arguments: list[str], timeout_seconds: float | None = None
    ) -> ProcessResult:
        project = Path(arguments[arguments.index("-save") + 1])
        project.touch()
        return original_run_command(arguments, timeout_seconds)

    fake.run_command = run_and_create_project  # type: ignore[method-assign]
    result = runner.run_experiment(config)
    directory = runner.last_experiment_directory

    assert result.status is ExperimentStatus.FAILED
    assert result.error_message is not None
    assert result.error_message.startswith(
        "Alignment completed, but report export or parsing failed:"
    )
    assert directory is not None
    assert (directory / "realityscan_output" / "project.rsproj").is_file()
    assert (directory / "result.json").is_file()
