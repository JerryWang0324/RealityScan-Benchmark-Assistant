from __future__ import annotations

import re

from rs_benchmark.models import BenchmarkStatus, ExperimentStatus

QUALITY_OPTIONS = (("高", "High"), ("一般", "Normal"))
OVERLAP_OPTIONS = (("低", "Low"), ("中", "Medium"), ("高", "High"))

STATUS_LABELS = {
    ExperimentStatus.PENDING: "等待中",
    ExperimentStatus.RUNNING: "執行中",
    ExperimentStatus.SUCCESS: "成功",
    ExperimentStatus.FAILED: "失敗",
    ExperimentStatus.TIMEOUT: "逾時",
    ExperimentStatus.DRY_RUN: "試執行完成",
    ExperimentStatus.SKIPPED: "已略過",
    ExperimentStatus.CANCELLED: "已取消",
}

BENCHMARK_STATUS_LABELS = {
    BenchmarkStatus.PENDING: "等待中",
    BenchmarkStatus.RUNNING: "執行中",
    BenchmarkStatus.COMPLETED: "已完成",
    BenchmarkStatus.PARTIAL_SUCCESS: "部分成功",
    BenchmarkStatus.FAILED: "失敗",
    BenchmarkStatus.CANCELLED: "已取消",
}


def status_label(status: ExperimentStatus) -> str:
    """Return a Traditional Chinese label for an internal experiment status."""
    return STATUS_LABELS.get(status, "未知狀態")


def benchmark_status_label(status: BenchmarkStatus) -> str:
    return BENCHMARK_STATUS_LABELS.get(status, "未知狀態")


def localize_error_message(message: str | None) -> str:
    """Translate known service errors without changing their machine-facing values."""
    if not message:
        return "發生未預期錯誤，請查看應用程式記錄檔。"

    prefix_translations = (
        ("Image folder does not exist:", "影像資料夾不存在："),
        ("No supported images found in:", "資料夾內找不到支援的影像："),
        ("RealityScan executable not found:", "找不到 RealityScan 執行檔："),
        ("Benchmark name cannot be empty", "效能測試名稱不可空白"),
        ("At least one enabled experiment is required", "至少需要一組已啟用的實驗"),
        ("Unable to start RealityScan:", "無法啟動 RealityScan："),
        ("Unable to read report:", "無法讀取對齊報告："),
        ("Alignment report is empty:", "對齊報告是空的："),
        ("Unrecognized alignment report format:", "無法辨識對齊報告格式："),
        (
            "Alignment completed, but report export or parsing failed:",
            "RealityScan 對齊已完成，但報告匯出或解析失敗：",
        ),
    )
    for english, chinese in prefix_translations:
        if message.startswith(english):
            return f"{chinese}{message.removeprefix(english).strip()}"

    exact_translations = {
        "Experiment name cannot be empty": "實驗名稱不可空白",
        "Max features per image must be positive": "每張影像最大特徵數必須大於零",
        "Max feature reprojection error must be positive": "最大重投影誤差必須大於零",
        "Executable must be named RealityScan.exe or RealityCapture.exe": (
            "執行檔名稱必須是 RealityScan.exe 或 RealityCapture.exe"
        ),
        "RealityScan process timed out": "RealityScan 處理程序已逾時",
    }
    if message in exact_translations:
        return exact_translations[message]

    exit_match = re.fullmatch(r"RealityScan exited with code (-?\d+)", message)
    if exit_match:
        return f"RealityScan 已結束，結束代碼：{exit_match.group(1)}"

    return "發生未預期錯誤，請查看 logs/app.log 取得詳細資訊。"
