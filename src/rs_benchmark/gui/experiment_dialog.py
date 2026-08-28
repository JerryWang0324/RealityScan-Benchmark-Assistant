from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from rs_benchmark.gui.localization import OVERLAP_OPTIONS, QUALITY_OPTIONS
from rs_benchmark.models import ExperimentConfig


class ExperimentDialog(QDialog):
    def __init__(self, config: ExperimentConfig | None = None, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("編輯對齊實驗" if config else "新增對齊實驗")
        self._source = config or ExperimentConfig(name="新實驗")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.enabled_check = QCheckBox("啟用此實驗")
        self.enabled_check.setChecked(self._source.enabled)
        self.name_edit = QLineEdit(self._source.name)
        self.quality_combo = QComboBox()
        for label, value in QUALITY_OPTIONS:
            self.quality_combo.addItem(label, value)
        self.quality_combo.setCurrentIndex(
            self.quality_combo.findData(self._source.feature_detection_quality)
        )
        self.features_spin = QSpinBox()
        self.features_spin.setRange(1, 10_000_000)
        self.features_spin.setSingleStep(5_000)
        self.features_spin.setValue(self._source.max_features_per_image)
        self.overlap_combo = QComboBox()
        for label, value in OVERLAP_OPTIONS:
            self.overlap_combo.addItem(label, value)
        self.overlap_combo.setCurrentIndex(self.overlap_combo.findData(self._source.image_overlap))
        self.reprojection_spin = QDoubleSpinBox()
        self.reprojection_spin.setRange(0.01, 100.0)
        self.reprojection_spin.setDecimals(2)
        self.reprojection_spin.setValue(self._source.max_feature_reprojection_error)
        form.addRow("狀態", self.enabled_check)
        form.addRow("實驗名稱", self.name_edit)
        form.addRow("特徵偵測品質", self.quality_combo)
        form.addRow("每張影像最大特徵數", self.features_spin)
        form.addRow("影像重疊程度", self.overlap_combo)
        form.addRow("最大重投影誤差（像素）", self.reprojection_spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("確定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def config(self) -> ExperimentConfig:
        return replace(
            self._source,
            name=self.name_edit.text().strip(),
            enabled=self.enabled_check.isChecked(),
            feature_detection_quality=self.quality_combo.currentData(),
            max_features_per_image=self.features_spin.value(),
            image_overlap=self.overlap_combo.currentData(),
            max_feature_reprojection_error=self.reprojection_spin.value(),
        )
