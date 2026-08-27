from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rs_benchmark.gui.workers import SingleExperimentWorker
from rs_benchmark.models import ExperimentConfig, ExperimentResult
from rs_benchmark.realityscan.dataset import validate_dataset
from rs_benchmark.services.settings_service import AppSettings, SettingsService
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner
from rs_benchmark.utils.paths import benchmark_runs_directory


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RealityScan Benchmark Assistant — Single Alignment Test")
        self.resize(780, 680)
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self.thread: QThread | None = None
        self.worker: SingleExperimentWorker | None = None
        self._build_ui()
        self._update_image_count()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._paths_group())
        layout.addWidget(self._parameters_group())

        actions = QHBoxLayout()
        self.dry_run_check = QCheckBox("Dry Run（只建立實驗檔案，不啟動 RealityScan）")
        self.preview_button = QPushButton("Preview CLI Command")
        self.preview_button.clicked.connect(self._preview_command)
        self.run_button = QPushButton("Run Single Alignment Test")
        self.run_button.clicked.connect(self._run_experiment)
        actions.addWidget(self.dry_run_check)
        actions.addStretch()
        actions.addWidget(self.preview_button)
        actions.addWidget(self.run_button)
        layout.addLayout(actions)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText("Alignment result will appear here.")
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_view, stretch=1)
        self.setCentralWidget(central)

    def _paths_group(self) -> QGroupBox:
        group = QGroupBox("Input")
        form = QFormLayout(group)
        self.name_edit = QLineEdit("default")
        self.image_folder_edit = QLineEdit(self.settings.last_image_folder)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image_folder_edit)
        image_button = QPushButton("Browse…")
        image_button.clicked.connect(self._browse_image_folder)
        image_row.addWidget(image_button)
        self.image_count_label = QLabel("Images: 0")
        image_row.addWidget(self.image_count_label)

        self.executable_edit = QLineEdit(self.settings.realityscan_executable)
        executable_row = QHBoxLayout()
        executable_row.addWidget(self.executable_edit)
        executable_button = QPushButton("Browse…")
        executable_button.clicked.connect(self._browse_executable)
        executable_row.addWidget(executable_button)
        form.addRow("Experiment name", self.name_edit)
        form.addRow("Image Folder", image_row)
        form.addRow("RealityScan Executable", executable_row)
        return group

    def _parameters_group(self) -> QGroupBox:
        group = QGroupBox("Alignment Parameters")
        form = QFormLayout(group)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["High", "Normal"])
        self.features_spin = QSpinBox()
        self.features_spin.setRange(1, 10_000_000)
        self.features_spin.setValue(40_000)
        self.features_spin.setSingleStep(5_000)
        self.overlap_combo = QComboBox()
        self.overlap_combo.addItems(["Low", "Medium", "High"])
        self.overlap_combo.setCurrentText("Medium")
        self.reprojection_spin = QDoubleSpinBox()
        self.reprojection_spin.setRange(0.01, 100.0)
        self.reprojection_spin.setDecimals(2)
        self.reprojection_spin.setValue(2.0)
        form.addRow("Feature Detection Quality", self.quality_combo)
        form.addRow("Max Features Per Image", self.features_spin)
        form.addRow("Image Overlap", self.overlap_combo)
        form.addRow("Max Reprojection Error (px)", self.reprojection_spin)
        return group

    def _config(self) -> ExperimentConfig:
        return ExperimentConfig(
            name=self.name_edit.text().strip() or "default",
            image_folder=Path(self.image_folder_edit.text()),
            realityscan_executable=Path(self.executable_edit.text()),
            feature_detection_quality=self.quality_combo.currentText(),
            max_features_per_image=self.features_spin.value(),
            image_overlap=self.overlap_combo.currentText(),
            max_feature_reprojection_error=self.reprojection_spin.value(),
            output_directory=benchmark_runs_directory(),
            dry_run=self.dry_run_check.isChecked(),
        )

    def _browse_image_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select image folder")
        if selected:
            self.image_folder_edit.setText(selected)
            self._save_settings()
            self._update_image_count()

    def _browse_executable(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select RealityScan executable", filter="RealityScan (*.exe)"
        )
        if selected:
            self.executable_edit.setText(selected)
            self._save_settings()

    def _update_image_count(self) -> None:
        try:
            count = validate_dataset(Path(self.image_folder_edit.text())).total_images
        except (FileNotFoundError, ValueError, OSError):
            count = 0
        self.image_count_label.setText(f"Images: {count}")

    def _preview_command(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("RealityScan CLI Preview")
        dialog.resize(720, 300)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit(SingleExperimentRunner.preview_command(self._config()))
        view.setReadOnly(True)
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _run_experiment(self) -> None:
        if self.thread is not None:
            return
        self._save_settings()
        self.status_label.setText("Running…")
        self.result_view.clear()
        self.run_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = SingleExperimentWorker(self._config())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.completed.connect(self._experiment_completed)
        self.worker.failed.connect(self._experiment_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _experiment_completed(self, result: ExperimentResult, directory: Path | None) -> None:
        self.status_label.setText(f"Status: {result.status.value}")
        self.result_view.setPlainText(self._format_result(result, directory))

    def _experiment_failed(self, message: str) -> None:
        self.status_label.setText("Status: FAILED")
        self.result_view.setPlainText(message)

    def _thread_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None
        self.run_button.setEnabled(True)
        self.preview_button.setEnabled(True)

    @staticmethod
    def _format_result(result: ExperimentResult, directory: Path | None) -> str:
        def value(item: object, suffix: str = "") -> str:
            return "N/A" if item is None else f"{item}{suffix}"

        rate = result.registration_rate
        runtime = f"{result.runtime_seconds:.1f}" if result.runtime_seconds is not None else None
        lines = [
            f"Status: {result.status.value}", "", f"Images: {value(result.total_images)}",
            f"Registered: {value(result.registered_images)}",
            f"Registration Rate: {value(f'{rate * 100:.1f}' if rate is not None else None, '%')}",
            f"Components: {value(result.component_count)}",
            f"Largest Component Cameras: {value(result.largest_component_camera_count)}",
            f"Sparse Points (largest component): {value(result.sparse_point_count)}",
            "Reprojection Error (largest component): "
            f"{value(result.mean_reprojection_error, ' px')}",
            f"Runtime: {value(runtime, ' s')}",
        ]
        if result.error_message:
            lines.extend(["", result.error_message])
        if directory:
            lines.extend(["", f"Experiment output: {directory}"])
            if result.error_message:
                lines.append(f"See: {directory / 'stderr.log'}")
        return "\n".join(lines)

    def _save_settings(self) -> None:
        self.settings_service.save(AppSettings(
            realityscan_executable=self.executable_edit.text(),
            last_image_folder=self.image_folder_edit.text(),
        ))

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._save_settings()
        super().closeEvent(event)
