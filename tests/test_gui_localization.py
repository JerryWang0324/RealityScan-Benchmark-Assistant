import ast
import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rs_benchmark.gui.localization import localize_error_message, status_label
from rs_benchmark.gui.main_window import MainWindow
from rs_benchmark.models import ExperimentResult, ExperimentStatus

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
    window.close()
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
