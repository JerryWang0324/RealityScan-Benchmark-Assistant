from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from rs_benchmark.gui.localization import OVERLAP_OPTIONS, QUALITY_OPTIONS
from rs_benchmark.models import (
    SWEEP_WARNING_THRESHOLD,
    BaselineConfig,
    ExperimentConfig,
    ParameterSweepConfig,
    SweepMode,
)

DEFAULT_FEATURE_VALUES = "20000, 40000, 80000"
DEFAULT_REPROJECTION_VALUES = "1.0, 2.0"


class ParameterSweepDialog(QDialog):
    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("產生參數掃描實驗")
        self.resize(620, 560)
        layout = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("掃描模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("完整因子組合", SweepMode.FULL_FACTORIAL)
        self.mode_combo.addItem("單因子逐次變動（OFAT）", SweepMode.ONE_FACTOR_AT_A_TIME)
        mode_row.addWidget(self.mode_combo, stretch=1)
        layout.addLayout(mode_row)

        choices = QGroupBox("候選參數值")
        form = QFormLayout(choices)
        quality_row = QHBoxLayout()
        self.quality_checks: list[QCheckBox] = []
        for label, value in QUALITY_OPTIONS:
            checkbox = QCheckBox(label)
            checkbox.setProperty("parameterValue", value)
            checkbox.setChecked(value == "High")
            quality_row.addWidget(checkbox)
            self.quality_checks.append(checkbox)
        form.addRow("特徵偵測品質", quality_row)

        self.features_edit = QLineEdit(DEFAULT_FEATURE_VALUES)
        self.features_edit.setPlaceholderText("例如：20000, 40000, 80000")
        form.addRow("每張影像特徵數", self.features_edit)

        overlap_row = QHBoxLayout()
        self.overlap_checks: list[QCheckBox] = []
        for label, value in OVERLAP_OPTIONS:
            checkbox = QCheckBox(label)
            checkbox.setProperty("parameterValue", value)
            checkbox.setChecked(value in {"Medium", "High"})
            overlap_row.addWidget(checkbox)
            self.overlap_checks.append(checkbox)
        form.addRow("影像重疊程度", overlap_row)

        self.reprojection_edit = QLineEdit(DEFAULT_REPROJECTION_VALUES)
        self.reprojection_edit.setPlaceholderText("例如：1.0, 2.0, 3.0")
        form.addRow("最大特徵重投影誤差", self.reprojection_edit)
        layout.addWidget(choices)

        self.baseline_group = QGroupBox("基準組態（OFAT）")
        baseline_form = QFormLayout(self.baseline_group)
        self.baseline_quality = QComboBox()
        for label, value in QUALITY_OPTIONS:
            self.baseline_quality.addItem(label, value)
        baseline_form.addRow("特徵偵測品質", self.baseline_quality)
        self.baseline_features = QSpinBox()
        self.baseline_features.setRange(1, 10_000_000)
        self.baseline_features.setValue(40_000)
        baseline_form.addRow("每張影像特徵數", self.baseline_features)
        self.baseline_overlap = QComboBox()
        for label, value in OVERLAP_OPTIONS:
            self.baseline_overlap.addItem(label, value)
        self.baseline_overlap.setCurrentIndex(self.baseline_overlap.findData("Medium"))
        baseline_form.addRow("影像重疊程度", self.baseline_overlap)
        self.baseline_reprojection = QDoubleSpinBox()
        self.baseline_reprojection.setRange(0.001, 1_000_000)
        self.baseline_reprojection.setDecimals(3)
        self.baseline_reprojection.setValue(2.0)
        baseline_form.addRow("最大特徵重投影誤差", self.baseline_reprojection)
        layout.addWidget(self.baseline_group)

        self.count_label = QLabel("將產生實驗：0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #b05a00; font-weight: bold;")
        self.workload_label = QLabel("將執行 0 次 RealityScan 對齊作業。")
        self.workload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.workload_label)

        buttons = QDialogButtonBox()
        self.preview_button = QPushButton("預覽實驗")
        cancel_button = QPushButton("取消")
        buttons.addButton(self.preview_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        self.preview_button.clicked.connect(self._accept_if_valid)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.mode_combo.currentIndexChanged.connect(self._update_count)
        self.features_edit.textChanged.connect(self._update_count)
        self.reprojection_edit.textChanged.connect(self._update_count)
        for checkbox in self.quality_checks + self.overlap_checks:
            checkbox.toggled.connect(self._update_count)
        for control in (
            self.baseline_quality, self.baseline_features, self.baseline_overlap,
            self.baseline_reprojection,
        ):
            if hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._update_count)
            else:
                control.currentIndexChanged.connect(self._update_count)
        self._update_count()

    @staticmethod
    def _integers(text: str) -> list[int]:
        values = [item.strip() for item in text.replace("，", ",").split(",")]
        if not values or any(not item for item in values):
            raise ValueError("每張影像特徵數不可留空，請以逗號分隔整數。")
        try:
            return list(dict.fromkeys(int(item) for item in values))
        except ValueError as exc:
            raise ValueError("每張影像特徵數必須是以逗號分隔的整數。") from exc

    @staticmethod
    def _floats(text: str) -> list[float]:
        values = [item.strip() for item in text.replace("，", ",").split(",")]
        if not values or any(not item for item in values):
            raise ValueError("重投影誤差不可留空，請以逗號分隔數值。")
        try:
            return list(dict.fromkeys(float(item) for item in values))
        except ValueError as exc:
            raise ValueError("重投影誤差必須是以逗號分隔的數值。") from exc

    def sweep_config(self) -> ParameterSweepConfig:
        qualities = [
            str(item.property("parameterValue")) for item in self.quality_checks
            if item.isChecked()
        ]
        overlaps = [
            str(item.property("parameterValue")) for item in self.overlap_checks
            if item.isChecked()
        ]
        mode = SweepMode(self.mode_combo.currentData())
        baseline = None
        if mode is SweepMode.ONE_FACTOR_AT_A_TIME:
            baseline = BaselineConfig(
                feature_detection_quality=str(self.baseline_quality.currentData()),
                max_features_per_image=self.baseline_features.value(),
                image_overlap=str(self.baseline_overlap.currentData()),
                max_feature_reprojection_error=self.baseline_reprojection.value(),
            )
        return ParameterSweepConfig(
            feature_detection_qualities=qualities,
            max_features_per_image=self._integers(self.features_edit.text()),
            image_overlaps=overlaps,
            max_feature_reprojection_errors=self._floats(self.reprojection_edit.text()),
            mode=mode,
            baseline=baseline,
        )

    def _update_count(self, *_: object) -> None:
        self.baseline_group.setEnabled(
            self.mode_combo.currentData() == SweepMode.ONE_FACTOR_AT_A_TIME
        )
        try:
            count = self.sweep_config().experiment_count
        except ValueError:
            count = 0
        self.count_label.setText(f"將產生實驗：{count}")
        self.workload_label.setText(f"將執行 {count} 次 RealityScan 對齊作業。")
        self.warning_label.setText(
            f"注意：此參數掃描將產生 {count} 個實驗，請確認工作量。"
            if count > SWEEP_WARNING_THRESHOLD else ""
        )
        self.preview_button.setEnabled(count > 0)

    def _accept_if_valid(self) -> None:
        try:
            self.sweep_config()
        except ValueError as exc:
            QMessageBox.warning(self, "參數掃描設定無效", str(exc))
            return
        self.accept()


class SweepPreviewDialog(QDialog):
    def __init__(
        self, experiments: list[ExperimentConfig], config: ParameterSweepConfig, parent=None
    ) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("參數掃描實驗預覽")
        self.resize(900, 560)
        layout = QVBoxLayout(self)
        mode = "完整因子組合" if config.mode is SweepMode.FULL_FACTORIAL else "單因子逐次變動"
        varied = "、".join(experiments[0].varied_parameters) or "無"
        layout.addWidget(QLabel(
            f"掃描摘要：模式為{mode}；變動參數為{varied}；共 {len(experiments)} 個實驗。"
        ))
        table = QTableWidget(len(experiments), 6)
        table.setHorizontalHeaderLabels(
            ("序號", "名稱", "特徵品質", "每張影像特徵數", "重疊程度", "重投影誤差")
        )
        for row, experiment in enumerate(experiments):
            values = (
                str(row + 1), experiment.name, experiment.feature_detection_quality,
                str(experiment.max_features_per_image), experiment.image_overlap,
                f"{experiment.max_feature_reprojection_error:g}",
            )
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        buttons = QHBoxLayout()
        buttons.addStretch()
        add_button = QPushButton("全部加入效能測試")
        cancel_button = QPushButton("取消")
        add_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(add_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
