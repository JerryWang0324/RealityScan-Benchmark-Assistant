import ast
import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from rs_benchmark.gui.localization import localize_error_message, status_label
from rs_benchmark.gui.main_window import MainWindow
from rs_benchmark.gui.sweep_dialog import ParameterSweepDialog
from rs_benchmark.models import BenchmarkProject, ExperimentResult, ExperimentStatus
from rs_benchmark.services.benchmark_runner import BenchmarkProgress

_CHINESE_CHARACTER = re.compile(r"[\u3400-\u9fff]")
_FIRST_ARGUMENT_UI_CALLS = {
    "QCheckBox",
    "QGroupBox",
    "QLabel",
    "QLineEdit",
    "QPushButton",
    "addItem",
    "addRow",
    "setPlaceholderText",
    "setText",
    "setToolTip",
    "setWindowTitle",
}


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _literal_text(node: ast.AST) -> str:
    return "".join(
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    )


def test_internal_values_use_chinese_display_labels() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.quality_combo.currentText() == "高"
    assert window.quality_combo.currentData() == "High"
    assert window.overlap_combo.currentText() == "中"
    assert window.overlap_combo.currentData() == "Medium"
    assert window._config().feature_detection_quality == "High"
    assert window._config().image_overlap == "Medium"
    assert window.timeout_spin.value() == 60
    assert window._config().timeout_seconds == 3_600
    assert window.quality_combo.isHidden()
    assert window.features_spin.isHidden()
    assert window.overlap_combo.isHidden()
    assert window.reprojection_spin.isHidden()
    assert window.timeout_spin.isHidden()
    assert window.experiment_table.rowCount() == 3
    assert window.repeat_count_spin.value() == 1
    assert window.repeat_summary_label.text() == "總執行次數：3 套參數 × 1 次 = 3 次"
    assert window.estimated_time_label.text() == "預估剩餘時間：尚無足夠資料"
    window.repeat_count_spin.setValue(4)
    assert window._project().repeat_count == 4
    assert window.repeat_summary_label.text() == "總執行次數：3 套參數 × 4 次 = 12 次"
    assert window.experiment_table.item(0, 1).text() == "預設"
    window.experiment_table.selectRow(0)
    window._duplicate_experiment()
    assert window.experiment_table.item(3, 1).text() == "預設 副本"
    window.close()
    assert app is not None


def test_remaining_time_label_is_traditional_chinese_and_updates_with_progress() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.thread = QThread(window)
    window._time_estimator.reset(3)
    window._time_estimator.observe(BenchmarkProgress(1, 3, "預設", "RUNNING"), 0)
    window._update_estimated_time(5_000)
    assert window.estimated_time_label.text() == "預估剩餘時間：尚無足夠資料"

    window._time_estimator.observe(BenchmarkProgress(1, 3, "預設", "FINISHED"), 20_000)
    window._update_estimated_time(20_000)
    assert window.estimated_time_label.text() == (
        "預估剩餘時間：約 00:00:40（依已完成實驗估算）"
    )
    window._time_estimator.observe(BenchmarkProgress(2, 3, "預設", "RUNNING"), 20_000)
    window._update_estimated_time(40_000)
    assert window.estimated_time_label.text() == "預估剩餘時間：無法準確預估"

    window.thread = None
    window.close()
    assert app is not None


def test_parameter_sweep_dialog_uses_chinese_labels_and_live_count() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = ParameterSweepDialog()

    assert dialog.mode_combo.currentText() == "完整因子組合"
    assert dialog.quality_checks[0].text() == "高"
    assert dialog.count_label.text() == "將產生實驗：12"
    assert dialog.sweep_config().experiment_count == 12
    dialog.mode_combo.setCurrentIndex(1)
    assert dialog.baseline_group.isEnabled()
    assert dialog.sweep_config().experiment_count == 5
    dialog.close()
    assert app is not None


def test_result_summary_is_traditional_chinese() -> None:
    result = ExperimentResult(
        experiment_name="預設",
        status=ExperimentStatus.SUCCESS,
        total_images=10,
        registered_images=9,
        component_count=1,
        runtime_seconds=2.5,
    )

    summary = MainWindow._format_result(result, Path("輸出"))

    assert "狀態：成功" in summary
    assert "影像總數：10" in summary
    assert "已註冊影像數：9" in summary
    assert "註冊率：90.0%" in summary
    assert "執行時間：2.5 秒" in summary
    assert "Status:" not in summary
    assert "Images:" not in summary


def test_pareto_filter_shows_component_runtime_tradeoff_and_names_criteria(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    project = BenchmarkProject(name="測試", image_folder=tmp_path)
    project.results = [
        ExperimentResult(
            experiment_name="快速設定", experiment_id="same",
            status=ExperimentStatus.SUCCESS, total_images=68, registered_images=68,
            component_count=2, runtime_seconds=17.0, repeat_index=1,
        ),
        ExperimentResult(
            experiment_name="快速設定", experiment_id="same",
            status=ExperimentStatus.SUCCESS, total_images=68, registered_images=68,
            component_count=2, runtime_seconds=16.4, repeat_index=2,
        ),
        ExperimentResult(
            experiment_name="單一元件", experiment_id="other",
            status=ExperimentStatus.SUCCESS, total_images=68, registered_images=68,
            component_count=1, runtime_seconds=16.8,
        ),
    ]
    window.result_filter_combo.setCurrentIndex(
        window.result_filter_combo.findData("pareto")
    )
    window._show_results(project)

    assert window.result_filter_combo.currentText() == "僅 Pareto 前緣（註冊率／時間／元件數）"
    assert window.result_table.rowCount() == 2
    assert window.result_table.item(0, 7).text() == "1"
    assert {window.result_table.item(row, 7).text() for row in range(2)} == {"1", "2"}
    assert {window.result_table.item(row, 11).text() for row in range(2)} == {
        "16.4 秒", "16.8 秒",
    }
    window.close()
    assert app is not None


def test_repeated_results_show_stability_summary() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    results = [
        ExperimentResult(
            experiment_name="預設", experiment_id="exp_repeat",
            status=ExperimentStatus.SUCCESS, total_images=10, registered_images=9,
            runtime_seconds=10.0, repeat_index=1, repeat_count=2,
        ),
        ExperimentResult(
            experiment_name="預設", experiment_id="exp_repeat",
            status=ExperimentStatus.SUCCESS, total_images=10, registered_images=8,
            runtime_seconds=12.0, repeat_index=2, repeat_count=2,
        ),
    ]

    window._set_comparison(results)

    assert "穩定性｜預設（2 次）：有效結果 2 / 2" in window.comparison_label.text()
    assert "平均註冊率 85.0%（標準差 5.0%）" in window.comparison_label.text()
    assert "平均執行時間 11.0 秒（標準差 1.0 秒）" in window.comparison_label.text()
    window.close()
    assert app is not None


def test_statuses_and_known_errors_are_localized() -> None:
    assert status_label(ExperimentStatus.TIMEOUT) == "逾時"
    assert localize_error_message("RealityScan process timed out") == "RealityScan 處理程序已逾時"
    assert localize_error_message("Image folder does not exist: C:/missing") == (
        "影像資料夾不存在：C:/missing"
    )
    assert localize_error_message(
        "Alignment completed, but report export or parsing failed: empty report"
    ) == "RealityScan 對齊已完成，但報告匯出或解析失敗：empty report"


def test_static_gui_text_uses_chinese_as_primary_language() -> None:
    gui_directory = Path(__file__).parents[1] / "src" / "rs_benchmark" / "gui"
    violations: list[str] = []

    for source_path in gui_directory.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            call_name = _call_name(call)
            argument_index = 1 if call_name in {"getExistingDirectory", "getOpenFileName"} else 0
            if call_name not in _FIRST_ARGUMENT_UI_CALLS | {
                "getExistingDirectory",
                "getOpenFileName",
            }:
                continue
            if len(call.args) <= argument_index:
                continue
            text = _literal_text(call.args[argument_index])
            if text and not _CHINESE_CHARACTER.search(text):
                violations.append(f"{source_path.name}:{call.lineno}：{text}")

    assert not violations, "UI 靜態文字必須以中文為主：\n" + "\n".join(violations)
