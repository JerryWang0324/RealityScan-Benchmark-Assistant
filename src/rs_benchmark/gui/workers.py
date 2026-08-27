from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from rs_benchmark.models import ExperimentConfig
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
