from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from statistics import mean

from matplotlib import rcParams
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rs_benchmark.gui.localization import OVERLAP_OPTIONS, QUALITY_OPTIONS
from rs_benchmark.models import BenchmarkProject, ExperimentResult, ExperimentStatus

METRICS = (
    ("registered_images", "已註冊影像數", "張"),
    ("registration_rate", "註冊率", "%"),
    ("component_count", "元件數", "個"),
    ("largest_component_camera_count", "最大元件影像數", "張"),
    ("sparse_point_count", "稀疏點數", "點"),
    ("mean_reprojection_error", "平均重投影誤差", "像素"),
    ("runtime_seconds", "執行時間", "秒"),
    ("runtime_per_registered_image", "每張已註冊影像執行時間", "秒／張"),
)


@dataclass(frozen=True)
class ParameterCombination:
    label: str
    values: dict[str, float | None]


def parameter_combinations(project: BenchmarkProject) -> list[ParameterCombination]:
    """Keep every enabled parameter signature, including combinations without valid results."""
    quality_labels = {value: label for label, value in QUALITY_OPTIONS}
    overlap_labels = {value: label for label, value in OVERLAP_OPTIONS}
    groups: dict[tuple[object, ...], list[ExperimentResult]] = defaultdict(list)
    signatures_by_id = {
        config.experiment_id: config.parameter_signature
        for config in project.enabled_experiments
    }
    names_by_signature: dict[tuple[object, ...], set[str]] = defaultdict(set)
    for config in project.enabled_experiments:
        names_by_signature[config.parameter_signature].add(config.name)
    for result in project.results:
        signature = signatures_by_id.get(result.experiment_id)
        if signature is None and not result.experiment_id:
            matches = [
                candidate for candidate, names in names_by_signature.items()
                if result.experiment_name in names
            ]
            if len(matches) == 1:
                signature = matches[0]
        if signature is not None and result.status == ExperimentStatus.SUCCESS:
            groups[signature].append(result)

    combinations: list[ParameterCombination] = []
    signatures = dict.fromkeys(
        config.parameter_signature for config in project.enabled_experiments
    )
    for signature in signatures:
        quality, features, overlap, reprojection = signature
        label = (
            f"品質：{quality_labels.get(quality, quality)}\n"
            f"特徵：{features:,}\n"
            f"重疊：{overlap_labels.get(overlap, overlap)}\n"
            f"誤差上限：{reprojection:g}"
        )
        values: dict[str, float | None] = {}
        for key, _, _ in METRICS:
            valid: list[float] = []
            for result in groups[signature]:
                value = getattr(result, key)
                if value is not None and isfinite(value):
                    valid.append(value * 100 if key == "registration_rate" else value)
            values[key] = mean(valid) if valid else None
        combinations.append(ParameterCombination(label, values))
    return combinations


class ChartDialog(QDialog):
    def __init__(self, project: BenchmarkProject, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("參數組合結果圖表")
        self.resize(1100, 740)
        self.combinations = parameter_combinations(project)
        self.metric_checks: dict[str, QCheckBox] = {}
        self.chart_tabs = QTabWidget()

        layout = QVBoxLayout(self)
        intro = QLabel("選擇要繪製的結果作為縱軸；橫軸列出所有已啟用的參數組合。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        note = QLabel("同一參數組合的成功執行結果取平均值；缺少數值的組合會標示「無資料」。")
        note.setWordWrap(True)
        layout.addWidget(note)
        has_values = any(
            value is not None
            for item in self.combinations
            for value in item.values.values()
        )
        if not has_values:
            empty = QLabel("目前結果沒有可繪製的有效數值。")
            layout.addWidget(empty)
        selector = QHBoxLayout()
        for index, (key, label, _) in enumerate(METRICS):
            check = QCheckBox(label)
            available = any(item.values[key] is not None for item in self.combinations)
            check.setChecked(available and key in {"registration_rate", "runtime_seconds"})
            check.setEnabled(available)
            self.metric_checks[key] = check
            selector.addWidget(check)
            if index == 3:
                layout.addLayout(selector)
                selector = QHBoxLayout()
        layout.addLayout(selector)

        controls = QHBoxLayout()
        self.draw_button = QPushButton("繪製圖表")
        self.draw_button.clicked.connect(self.draw_charts)
        self.draw_button.setEnabled(any(check.isEnabled() for check in self.metric_checks.values()))
        controls.addWidget(self.draw_button)
        controls.addStretch()
        close_button = QPushButton("關閉")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)
        layout.addWidget(self.chart_tabs, stretch=1)
        if self.draw_button.isEnabled():
            self.draw_charts()

    def draw_charts(self) -> None:
        selected = [metric for metric in METRICS if self.metric_checks[metric[0]].isChecked()]
        if not selected:
            QMessageBox.information(self, "尚未選擇結果", "請至少選擇一項要繪製的結果。")
            return
        rcParams["font.sans-serif"] = [
            "Microsoft JhengHei", "Microsoft YaHei", "Noto Sans CJK TC", "DejaVu Sans"
        ]
        rcParams["axes.unicode_minus"] = False
        while self.chart_tabs.count():
            widget = self.chart_tabs.widget(0)
            self.chart_tabs.removeTab(0)
            widget.deleteLater()
        for key, label, unit in selected:
            figure = Figure(figsize=(max(8, len(self.combinations) * 1.9), 5.7))
            axis = figure.subplots()
            positions = list(range(len(self.combinations)))
            values = [item.values[key] for item in self.combinations]
            axis.bar(
                [
                    position for position, value in zip(positions, values, strict=True)
                    if value is not None
                ],
                [value for value in values if value is not None],
                color="#2878B5",
                width=0.65,
            )
            axis.set_xticks(positions, [item.label for item in self.combinations])
            axis.set_xlabel("參數組合")
            axis.set_ylabel(f"{label}（{unit}）")
            axis.set_title(f"各參數組合的{label}")
            axis.grid(axis="y", alpha=0.25)
            axis.set_axisbelow(True)
            for position, value in zip(positions, values, strict=True):
                if value is None:
                    axis.text(position, 0, "無資料", ha="center", va="bottom")
            figure.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.32)
            canvas = FigureCanvasQTAgg(figure)
            canvas.setMinimumSize(max(800, len(self.combinations) * 180), 500)
            scroll = QScrollArea()
            scroll.setWidget(canvas)
            scroll.setWidgetResizable(False)
            scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.chart_tabs.addTab(scroll, label)
