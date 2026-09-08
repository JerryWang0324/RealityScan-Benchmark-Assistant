from __future__ import annotations

from rs_benchmark.analysis.metrics import BenchmarkAnalysisResult, MetricLeader


def build_observations(analysis: BenchmarkAnalysisResult) -> list[str]:
    if analysis.successful_count == 0:
        return ["沒有可用於指標比較的成功實驗結果。"]
    labels = {
        "highest_registration_rate": ("最高註冊率", "%"),
        "fastest_runtime": ("最短執行時間", " 秒"),
        "lowest_reported_reprojection_error": ("最低報告重投影誤差", " px"),
        "highest_sparse_point_count": ("最高稀疏點數", " 點"),
    }
    rows: list[str] = []
    for key, (label, suffix) in labels.items():
        leader = analysis.metric_leaders.get(key)
        if leader:
            rows.append(_leader_sentence(label, suffix, leader))
    for sweep in analysis.sweep_analysis:
        rows.extend(sweep.observations)
    return rows


def scientific_warnings(analysis: BenchmarkAnalysisResult) -> list[str]:
    warnings = [
        "本效能測試未使用獨立的真值幾何資料。",
        "結果只適用於本次資料集、RealityScan 版本、硬體與執行條件。",
    ]
    if "lowest_reported_reprojection_error" in analysis.metric_leaders:
        warnings.append("較低的報告重投影誤差本身不足以證明絕對三維精度較高。")
    if "highest_sparse_point_count" in analysis.metric_leaders:
        warnings.append("較大的稀疏點數不必然代表重建更準確或品質更高。")
    return warnings


def _leader_sentence(label: str, suffix: str, leader: MetricLeader) -> str:
    names = "、".join(leader.experiment_names)
    tie = "（平手）" if len(leader.experiment_names) > 1 else ""
    value = leader.value * 100 if leader.metric == "highest_registration_rate" else leader.value
    precision = 2 if isinstance(value, float) else 0
    return f"{label}：{names}{tie}，{value:.{precision}f}{suffix}。"

