from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from rs_benchmark.models import BenchmarkProject, ExperimentConfig
from rs_benchmark.services.benchmark_runner import BenchmarkRunner
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner


class SingleExperimentWorker(QObject):
    completed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, config: ExperimentConfig) -> None:
        super().__init__()
        self.config = config

    @Slot()
    def run(self) -> None:
        runner = SingleExperimentRunner()
        try:
            result = runner.run_experiment(self.config)
        except Exception as exc:  # Qt boundary: never let worker exceptions terminate the GUI.
            self.failed.emit(str(exc))
            return
        self.completed.emit(result, runner.last_experiment_directory)


class BenchmarkWorker(QObject):
    progress = Signal(object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, project: BenchmarkProject) -> None:
        super().__init__()
        self.project = project
        self.runner = BenchmarkRunner()

    @Slot()
    def run(self) -> None:
        try:
            project = self.runner.run_benchmark(self.project, self.progress.emit)
        except Exception as exc:  # Qt boundary: keep worker failures away from the GUI loop.
            self.failed.emit(str(exc))
            return
        self.completed.emit(project)

    def cancel(self) -> None:
        self.runner.cancel()
