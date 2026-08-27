from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rs_benchmark.models import ExperimentConfig
from rs_benchmark.models.benchmark import SUPPORTED_IMAGE_EXTENSIONS
from rs_benchmark.services.settings_service import AppSettings, SettingsService

_QUALITY_LABELS = {
    "High": "高",
    "Normal": "一般",
}

_OVERLAP_LABELS = {
    "Low": "低",
    "Medium": "中",
    "High": "高",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RealityScan 效能測試助手")
        self.resize(900, 620)
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self.experiments = [
            ExperimentConfig(name="預設"),
            ExperimentConfig(name="高特徵數", max_features_per_image=80_000),
            ExperimentConfig(
                name="嚴格幾何條件",
                image_overlap="High",
                max_feature_reprojection_error=1.0,
            ),
        ]
        self._build_ui()
        self._populate_experiments()
        self._update_image_count()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._dataset_group())
        layout.addWidget(self._realityscan_group())
        layout.addWidget(self._experiments_group(), stretch=1)

        self.run_button = QPushButton("執行效能測試")
        self.run_button.setEnabled(False)
        self.run_button.setToolTip("完整的效能測試執行功能將於下一階段加入。")
        self.status_label = QLabel("基礎功能已就緒——效能測試執行功能尚未啟用。")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

    def _dataset_group(self) -> QGroupBox:
        group = QGroupBox("資料集")
        layout = QGridLayout(group)
        self.image_folder_edit = QLineEdit(self.settings.last_image_folder)
        browse_button = QPushButton("瀏覽…")
        browse_button.clicked.connect(self._browse_image_folder)
        self.image_count_label = QLabel("影像數量：0")
        layout.addWidget(QLabel("影像資料夾："), 0, 0)
        layout.addWidget(self.image_folder_edit, 0, 1)
        layout.addWidget(browse_button, 0, 2)
        layout.addWidget(self.image_count_label, 1, 1)
        return group

    def _realityscan_group(self) -> QGroupBox:
        group = QGroupBox("RealityScan")
        layout = QHBoxLayout(group)
        self.executable_edit = QLineEdit(self.settings.realityscan_executable)
        browse_button = QPushButton("瀏覽…")
        browse_button.clicked.connect(self._browse_executable)
        layout.addWidget(QLabel("執行檔："))
        layout.addWidget(self.executable_edit, stretch=1)
        layout.addWidget(browse_button)
        return group

    def _experiments_group(self) -> QGroupBox:
        group = QGroupBox("實驗設定")
        layout = QVBoxLayout(group)
        self.experiment_table = QTableWidget(0, 5)
        self.experiment_table.setHorizontalHeaderLabels(
            ["名稱", "品質", "特徵數", "重疊程度", "重投影誤差"]
        )
        self.experiment_table.horizontalHeader().setStretchLastSection(True)
        self.experiment_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.experiment_table)
        actions = QHBoxLayout()
        for label in ("新增實驗", "編輯", "複製", "刪除"):
            button = QPushButton(label)
            button.setEnabled(False)
            button.setToolTip("實驗編輯功能將於下一階段加入。")
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        return group

    def _populate_experiments(self) -> None:
        self.experiment_table.setRowCount(len(self.experiments))
        for row, experiment in enumerate(self.experiments):
            values = (
                experiment.name,
                _QUALITY_LABELS.get(
                    experiment.feature_detection_quality,
                    experiment.feature_detection_quality,
                ),
                str(experiment.max_features_per_image),
                _OVERLAP_LABELS.get(experiment.image_overlap, experiment.image_overlap),
                str(experiment.max_feature_reprojection_error),
            )
            for column, value in enumerate(values):
                self.experiment_table.setItem(row, column, QTableWidgetItem(value))
        self.experiment_table.resizeColumnsToContents()

    def _browse_image_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "選擇影像資料夾")
        if selected:
            self.image_folder_edit.setText(selected)
            self.settings.last_image_folder = selected
            self.settings_service.save(self.settings)
            self._update_image_count()

    def _browse_executable(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 RealityScan 執行檔",
            filter=(
                "RealityScan 執行檔 (RealityScan.exe RealityCapture.exe);;執行檔 (*.exe)"
            ),
        )
        if selected:
            self.executable_edit.setText(selected)
            self.settings.realityscan_executable = selected
            self.settings_service.save(self.settings)

    def _update_image_count(self) -> None:
        folder = Path(self.image_folder_edit.text())
        count = 0
        if folder.is_dir():
            count = sum(
                path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
                for path in folder.iterdir()
            )
        self.image_count_label.setText(f"影像數量：{count}")

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.settings = AppSettings(
            realityscan_executable=self.executable_edit.text(),
            last_image_folder=self.image_folder_edit.text(),
        )
        self.settings_service.save(self.settings)
        super().closeEvent(event)
