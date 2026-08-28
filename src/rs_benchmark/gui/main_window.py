from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, Qt, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rs_benchmark.gui.experiment_dialog import ExperimentDialog
from rs_benchmark.gui.localization import (
    OVERLAP_OPTIONS,
    QUALITY_OPTIONS,
    benchmark_status_label,
    localize_error_message,
    status_label,
)
from rs_benchmark.gui.workers import BenchmarkWorker
from rs_benchmark.models import BenchmarkProject, ExperimentConfig, ExperimentResult
from rs_benchmark.realityscan.dataset import validate_dataset
from rs_benchmark.services.benchmark_runner import BenchmarkProgress
from rs_benchmark.services.settings_service import AppSettings, SettingsService
from rs_benchmark.services.single_experiment_runner import SingleExperimentRunner
from rs_benchmark.utils.paths import benchmark_runs_directory


def built_in_presets() -> list[ExperimentConfig]:
    return [
        ExperimentConfig(name="預設"),
        ExperimentConfig(name="高特徵數", max_features_per_image=80_000),
        ExperimentConfig(
            name="嚴格幾何", image_overlap="High", max_feature_reprojection_error=1.0
        ),
    ]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RealityScan 效能測試助手 — 多實驗對齊效能測試")
        self.resize(1120, 780)
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self.thread: QThread | None = None
        self.worker: BenchmarkWorker | None = None
        self.current_project: BenchmarkProject | None = None
        self._close_when_finished = False
        self._elapsed = QElapsedTimer()
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._build_ui()
        self._build_compatibility_controls()
        for preset in built_in_presets():
            self._append_experiment(preset)
        self._update_image_count()

    def _build_ui(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)
        tabs = QTabWidget()
        self.setup_tab = QWidget()
        setup_layout = QVBoxLayout(self.setup_tab)
        setup_layout.addWidget(self._dataset_group())
        setup_layout.addWidget(self._experiments_group(), stretch=1)
        setup_layout.addWidget(self._run_controls())
        tabs.addTab(self.setup_tab, "效能測試設定")
        tabs.addTab(self._results_tab(), "結果")
        outer.addWidget(tabs)
        self.tabs = tabs
        self.setCentralWidget(central)

    def _dataset_group(self) -> QGroupBox:
        group = QGroupBox("效能測試資料集")
        layout = QVBoxLayout(group)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("效能測試名稱"))
        self.benchmark_name_edit = QLineEdit("建築效能測試")
        name_row.addWidget(self.benchmark_name_edit)
        layout.addLayout(name_row)

        image_row = QHBoxLayout()
        image_row.addWidget(QLabel("影像資料夾"))
        self.image_folder_edit = QLineEdit(self.settings.last_image_folder)
        self.image_folder_edit.editingFinished.connect(self._update_image_count)
        image_row.addWidget(self.image_folder_edit, stretch=1)
        image_button = QPushButton("瀏覽…")
        image_button.clicked.connect(self._browse_image_folder)
        image_row.addWidget(image_button)
        self.image_count_label = QLabel("影像數量：0")
        image_row.addWidget(self.image_count_label)
        layout.addLayout(image_row)

        executable_row = QHBoxLayout()
        executable_row.addWidget(QLabel("RealityScan 執行檔"))
        self.executable_edit = QLineEdit(self.settings.realityscan_executable)
        executable_row.addWidget(self.executable_edit, stretch=1)
        executable_button = QPushButton("瀏覽…")
        executable_button.clicked.connect(self._browse_executable)
        executable_row.addWidget(executable_button)
        layout.addLayout(executable_row)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("輸出資料夾"))
        self.output_directory_edit = QLineEdit(str(benchmark_runs_directory()))
        output_row.addWidget(self.output_directory_edit, stretch=1)
        output_button = QPushButton("瀏覽…")
        output_button.clicked.connect(self._browse_output_directory)
        output_row.addWidget(output_button)
        layout.addLayout(output_row)
        return group

    def _experiments_group(self) -> QGroupBox:
        group = QGroupBox("對齊實驗佇列")
        layout = QVBoxLayout(group)
        self.experiment_table = QTableWidget(0, 7)
        self.experiment_table.setHorizontalHeaderLabels(
            ("啟用", "名稱", "特徵品質", "每張影像特徵數", "重疊程度", "重投影誤差", "狀態")
        )
        self.experiment_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.experiment_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.experiment_table.verticalHeader().setVisible(False)
        header = self.experiment_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (0, 2, 3, 4, 5, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.experiment_table.doubleClicked.connect(self._edit_experiment)
        layout.addWidget(self.experiment_table)

        buttons = QHBoxLayout()
        actions = (
            ("新增實驗", self._add_experiment),
            ("編輯", self._edit_experiment),
            ("複製", self._duplicate_experiment),
            ("刪除", self._delete_experiment),
            ("上移", self._move_up),
            ("下移", self._move_down),
        )
        for text, callback in actions:
            button = QPushButton(text)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        return group

    def _run_controls(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        options = QHBoxLayout()
        self.dry_run_check = QCheckBox("效能測試試執行（建立所有指令，但不啟動 RealityScan）")
        self.stop_failure_check = QCheckBox("實驗失敗時停止後續佇列")
        options.addWidget(self.dry_run_check)
        options.addWidget(self.stop_failure_check)
        options.addStretch()
        layout.addLayout(options)
        actions = QHBoxLayout()
        self.preview_button = QPushButton("預覽 CLI 指令")
        self.preview_button.clicked.connect(self._preview_commands)
        self.run_button = QPushButton("執行效能測試")
        self.run_button.clicked.connect(self._run_benchmark)
        self.cancel_button = QPushButton("取消效能測試")
        self.cancel_button.clicked.connect(self._cancel_benchmark)
        self.cancel_button.setEnabled(False)
        actions.addStretch()
        actions.addWidget(self.preview_button)
        actions.addWidget(self.run_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)

        self.progress_label = QLabel("準備就緒")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.elapsed_label = QLabel("經過時間：00:00:00")
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.elapsed_label)
        return widget

    def _results_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.result_table = QTableWidget(0, 9)
        self.result_table.setHorizontalHeaderLabels(
            (
                "實驗", "狀態", "已註冊", "註冊率", "元件數", "最大元件",
                "稀疏點數", "重投影誤差", "執行時間",
            )
        )
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.result_table, stretch=1)
        self.comparison_label = QLabel("描述性比較會在效能測試完成後顯示。")
        self.comparison_label.setWordWrap(True)
        layout.addWidget(self.comparison_label)
        actions = QHBoxLayout()
        self.open_output_button = QPushButton("開啟輸出資料夾")
        self.open_output_button.clicked.connect(self._open_output_folder)
        self.export_button = QPushButton("匯出 CSV")
        self.export_button.clicked.connect(self._export_csv)
        self.charts_button = QPushButton("檢視圖表")
        self.charts_button.clicked.connect(self._view_charts)
        for button in (self.open_output_button, self.export_button, self.charts_button):
            button.setEnabled(False)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        return widget

    def _build_compatibility_controls(self) -> None:
        """Retain the Phase 2 configuration API while the UI uses the experiment table."""
        self.name_edit = self.benchmark_name_edit
        self.quality_combo = QComboBox(self)
        for label, value in QUALITY_OPTIONS:
            self.quality_combo.addItem(label, value)
        self.features_spin = QSpinBox(self)
        self.features_spin.setRange(1, 10_000_000)
        self.features_spin.setValue(40_000)
        self.overlap_combo = QComboBox(self)
        for label, value in OVERLAP_OPTIONS:
            self.overlap_combo.addItem(label, value)
        self.overlap_combo.setCurrentIndex(self.overlap_combo.findData("Medium"))
        self.reprojection_spin = QDoubleSpinBox(self)
        self.reprojection_spin.setValue(2.0)
        self.timeout_spin = QSpinBox(self)
        self.timeout_spin.setRange(0, 1_440)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSpecialValueText("不限時間")
        # These widgets only preserve the Phase 2 programmatic configuration API.
        # Without an explicit hidden state, parented widgets that are not in a
        # layout are painted at the main window's top-left corner over the tabs.
        for control in (
            self.quality_combo,
            self.features_spin,
            self.overlap_combo,
            self.reprojection_spin,
            self.timeout_spin,
        ):
            control.hide()

    def _config(self) -> ExperimentConfig:
        return ExperimentConfig(
            name=self.name_edit.text().strip() or "預設",
            image_folder=Path(self.image_folder_edit.text()),
            realityscan_executable=Path(self.executable_edit.text()),
            feature_detection_quality=self.quality_combo.currentData(),
            max_features_per_image=self.features_spin.value(),
            image_overlap=self.overlap_combo.currentData(),
            max_feature_reprojection_error=self.reprojection_spin.value(),
            output_directory=Path(self.output_directory_edit.text()),
            timeout_seconds=(self.timeout_spin.value() * 60 or None),
            dry_run=self.dry_run_check.isChecked(),
        )

    def _append_experiment(self, config: ExperimentConfig) -> None:
        row = self.experiment_table.rowCount()
        self.experiment_table.insertRow(row)
        enabled = QTableWidgetItem()
        enabled.setFlags(enabled.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        enabled.setCheckState(
            Qt.CheckState.Checked if config.enabled else Qt.CheckState.Unchecked
        )
        enabled.setData(Qt.ItemDataRole.UserRole, config)
        self.experiment_table.setItem(row, 0, enabled)
        self._populate_row(row, config)

    def _populate_row(self, row: int, config: ExperimentConfig) -> None:
        quality = dict((value, label) for label, value in QUALITY_OPTIONS)[
            config.feature_detection_quality
        ]
        overlap = dict((value, label) for label, value in OVERLAP_OPTIONS)[config.image_overlap]
        values = (
            config.name,
            quality,
            str(config.max_features_per_image),
            overlap,
            f"{config.max_feature_reprojection_error:.2f}",
            "準備就緒",
        )
        for column, value in enumerate(values, start=1):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.experiment_table.setItem(row, column, item)

    def _experiments(self) -> list[ExperimentConfig]:
        experiments = []
        for row in range(self.experiment_table.rowCount()):
            item = self.experiment_table.item(row, 0)
            config = item.data(Qt.ItemDataRole.UserRole)
            experiments.append(replace(config, enabled=item.checkState() == Qt.CheckState.Checked))
        return experiments

    def _selected_row(self) -> int:
        return self.experiment_table.currentRow()

    def _add_experiment(self) -> None:
        dialog = ExperimentDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self._append_experiment(dialog.config())
            except ValueError as exc:
                QMessageBox.warning(self, "實驗設定無效", localize_error_message(str(exc)))

    def _edit_experiment(self, *_: object) -> None:
        row = self._selected_row()
        if row < 0:
            return
        source = self._experiments()[row]
        dialog = ExperimentDialog(source, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                config = dialog.config()
            except ValueError as exc:
                QMessageBox.warning(self, "實驗設定無效", localize_error_message(str(exc)))
                return
            item = self.experiment_table.item(row, 0)
            item.setData(Qt.ItemDataRole.UserRole, config)
            item.setCheckState(
                Qt.CheckState.Checked if config.enabled else Qt.CheckState.Unchecked
            )
            self._populate_row(row, config)

    def _duplicate_experiment(self) -> None:
        row = self._selected_row()
        if row < 0:
            return
        source = self._experiments()[row]
        self._append_experiment(replace(source, name=f"{source.name} 副本"))
        self.experiment_table.selectRow(self.experiment_table.rowCount() - 1)

    def _delete_experiment(self) -> None:
        row = self._selected_row()
        if row >= 0:
            self.experiment_table.removeRow(row)

    def _move_up(self) -> None:
        self._move_selected(-1)

    def _move_down(self) -> None:
        self._move_selected(1)

    def _move_selected(self, offset: int) -> None:
        row = self._selected_row()
        target = row + offset
        if row < 0 or target < 0 or target >= self.experiment_table.rowCount():
            return
        configs = self._experiments()
        configs[row], configs[target] = configs[target], configs[row]
        self.experiment_table.setRowCount(0)
        for config in configs:
            self._append_experiment(config)
        self.experiment_table.selectRow(target)

    def _project(self) -> BenchmarkProject:
        return BenchmarkProject(
            name=self.benchmark_name_edit.text().strip(),
            image_folder=Path(self.image_folder_edit.text()),
            realityscan_executable=Path(self.executable_edit.text()),
            output_directory=Path(self.output_directory_edit.text()),
            experiments=self._experiments(),
            stop_on_failure=self.stop_failure_check.isChecked(),
            dry_run=self.dry_run_check.isChecked(),
        )

    def _run_benchmark(self) -> None:
        if self.thread is not None:
            return
        project = self._project()
        try:
            warnings = project.validate(require_executable=True)
        except (ValueError, FileNotFoundError, OSError) as exc:
            QMessageBox.warning(self, "無法執行效能測試", localize_error_message(str(exc)))
            return
        if warnings:
            duplicate_message = "\n".join(warnings).replace(
                "Experiments ", "實驗 "
            ).replace(" and ", " 與 ").replace(
                " use identical parameters.", " 使用完全相同的參數。"
            )
            QMessageBox.warning(self, "實驗參數重複", duplicate_message)
        self._save_settings()
        self.current_project = project
        self.result_table.setRowCount(0)
        self.run_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在準備效能測試…")
        self._elapsed.start()
        self._elapsed_timer.start(1_000)
        self.thread = QThread(self)
        self.worker = BenchmarkWorker(project)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._benchmark_progress)
        self.worker.completed.connect(self._benchmark_completed)
        self.worker.failed.connect(self._benchmark_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _cancel_benchmark(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.progress_label.setText("已要求取消；目前實驗結束後將停止後續佇列。")

    def _benchmark_progress(self, progress: BenchmarkProgress) -> None:
        phase = "執行中" if progress.phase == "RUNNING" else "已完成"
        self.progress_label.setText(
            f"實驗 {progress.current} / {progress.total}：{progress.experiment_name} — {phase}"
        )
        self.progress_bar.setValue(progress.percent)
        for row in range(self.experiment_table.rowCount()):
            if self.experiment_table.item(row, 1).text() == progress.experiment_name:
                self.experiment_table.item(row, 6).setText(phase)
                break

    def _benchmark_completed(self, project: BenchmarkProject) -> None:
        self.current_project = project
        if project.status.value != "CANCELLED":
            self.progress_bar.setValue(100)
        self.progress_label.setText(f"效能測試狀態：{benchmark_status_label(project.status)}")
        self._show_results(project)
        self.tabs.setCurrentIndex(1)

    def _benchmark_failed(self, message: str) -> None:
        self.progress_label.setText("效能測試無法啟動")
        QMessageBox.warning(self, "效能測試失敗", localize_error_message(message))

    def _thread_finished(self) -> None:
        self._elapsed_timer.stop()
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None
        self.run_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self._close_when_finished:
            QTimer.singleShot(0, self.close)

    def _show_results(self, project: BenchmarkProject) -> None:
        self.result_table.setRowCount(0)
        for result in project.results:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            rate = result.registration_rate
            values = (
                result.experiment_name,
                status_label(result.status),
                self._display(result.registered_images),
                self._display(rate * 100 if rate is not None else None, "%", 1),
                self._display(result.component_count),
                self._display(result.largest_component_camera_count),
                self._display(result.sparse_point_count),
                self._display(result.mean_reprojection_error, " px", 3),
                self._display(result.runtime_seconds, " 秒", 1),
            )
            for column, value in enumerate(values):
                self.result_table.setItem(row, column, QTableWidgetItem(value))
            for experiment_row in range(self.experiment_table.rowCount()):
                if self.experiment_table.item(experiment_row, 1).text() == result.experiment_name:
                    self.experiment_table.item(experiment_row, 6).setText(
                        status_label(result.status)
                    )
                    break
        self._set_comparison(project.results)
        for button in (self.open_output_button, self.export_button, self.charts_button):
            button.setEnabled(project.run_directory is not None)

    def _set_comparison(self, results: list[ExperimentResult]) -> None:
        from rs_benchmark.reports.comparison import compare_results

        comparison = compare_results(results)
        labels = {
            "highest_registration_rate": "較高註冊率",
            "lowest_runtime": "較短執行時間",
            "lowest_reprojection_error": "較低報告重投影誤差",
            "highest_sparse_point_count": "較高稀疏點數",
        }
        lines = [
            f"{labels[key]}：{result.experiment_name}"
            for key, result in comparison.items() if result is not None
        ]
        self.comparison_label.setText("；".join(lines) if lines else "沒有可比較的有效數值。")

    @staticmethod
    def _display(value: object, suffix: str = "", decimals: int | None = None) -> str:
        if value is None:
            return "N/A"
        if decimals is not None and isinstance(value, (float, int)):
            return f"{value:.{decimals}f}{suffix}"
        return f"{value}{suffix}"

    def _preview_commands(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("RealityScan CLI 指令預覽")
        dialog.resize(820, 500)
        layout = QVBoxLayout(dialog)
        text = []
        project = self._project()
        for index, experiment in enumerate(project.enabled_experiments, start=1):
            config = project.experiment_config(experiment, project.output_directory)
            text.extend(
                (
                    f"實驗 {index}：{experiment.name}",
                    SingleExperimentRunner.preview_command(config),
                    "",
                )
            )
        view = QPlainTextEdit("\n".join(text))
        view.setReadOnly(True)
        layout.addWidget(view)
        close_button = QPushButton("關閉")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _browse_image_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "選擇影像資料夾")
        if selected:
            self.image_folder_edit.setText(selected)
            self._save_settings()
            self._update_image_count()

    def _browse_executable(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "選擇 RealityScan 執行檔", filter="RealityScan 執行檔 (*.exe)"
        )
        if selected:
            self.executable_edit.setText(selected)
            self._save_settings()

    def _browse_output_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if selected:
            self.output_directory_edit.setText(selected)

    def _update_image_count(self) -> None:
        try:
            count = validate_dataset(Path(self.image_folder_edit.text())).total_images
        except (FileNotFoundError, ValueError, OSError):
            count = 0
        self.image_count_label.setText(f"影像數量：{count}")

    def _update_elapsed(self) -> None:
        elapsed = max(0, self._elapsed.elapsed() // 1_000)
        hours, remainder = divmod(elapsed, 3_600)
        minutes, seconds = divmod(remainder, 60)
        self.elapsed_label.setText(f"經過時間：{hours:02d}:{minutes:02d}:{seconds:02d}")

    def _open_output_folder(self) -> None:
        if self.current_project and self.current_project.run_directory:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_project.run_directory)))

    def _export_csv(self) -> None:
        if not self.current_project or not self.current_project.run_directory:
            return
        source = self.current_project.run_directory / "summary" / "results.csv"
        selected, _ = QFileDialog.getSaveFileName(
            self, "匯出結果 CSV", "results.csv", "CSV 檔案 (*.csv)"
        )
        if selected:
            shutil.copy2(source, selected)

    def _view_charts(self) -> None:
        if not self.current_project or not self.current_project.run_directory:
            return
        charts = sorted((self.current_project.run_directory / "summary" / "charts").glob("*.png"))
        if charts:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(charts[0])))
        else:
            QMessageBox.information(self, "沒有可用圖表", "目前結果沒有足夠的有效數值可產生圖表。")

    @staticmethod
    def _format_result(result: ExperimentResult, directory: Path | None) -> str:
        def value(item: object, suffix: str = "") -> str:
            return "無資料" if item is None else f"{item}{suffix}"

        rate = result.registration_rate
        runtime = f"{result.runtime_seconds:.1f}" if result.runtime_seconds is not None else None
        lines = [
            f"狀態：{status_label(result.status)}", "",
            f"影像總數：{value(result.total_images)}",
            f"已註冊影像數：{value(result.registered_images)}",
            f"註冊率：{value(f'{rate * 100:.1f}' if rate is not None else None, '%')}",
            f"元件數量：{value(result.component_count)}",
            f"最大元件相機數：{value(result.largest_component_camera_count)}",
            f"稀疏點數（最大元件）：{value(result.sparse_point_count)}",
            f"重投影誤差（最大元件）：{value(result.mean_reprojection_error, ' 像素')}",
            f"執行時間：{value(runtime, ' 秒')}",
        ]
        if result.error_message:
            lines.extend(("", f"錯誤：{localize_error_message(result.error_message)}"))
        if directory:
            lines.extend(("", f"實驗輸出位置：{directory}"))
        return "\n".join(lines)

    def _save_settings(self) -> None:
        self.settings_service.save(
            AppSettings(
                realityscan_executable=self.executable_edit.text(),
                last_image_folder=self.image_folder_edit.text(),
            )
        )

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._save_settings()
        if self.thread is not None:
            self._close_when_finished = True
            if self.worker:
                self.worker.cancel()
            self.progress_label.setText("正在取消效能測試；目前實驗結束後將關閉視窗。")
            event.ignore()
            return
        super().closeEvent(event)
