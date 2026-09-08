from __future__ import annotations

from html import escape
from pathlib import Path

from rs_benchmark import __version__
from rs_benchmark.analysis.metrics import BenchmarkAnalysisResult
from rs_benchmark.models import BenchmarkProject, ExperimentConfig, ExperimentResult
from rs_benchmark.utils.path_sanitizer import PathDisplaySanitizer

LIMITATIONS = (
    "結果只適用於本次資料集與執行環境。",
    "RealityScan 內部指標屬於間接品質指標。",
    "重投影誤差本身不足以證明絕對三維精度。",
    "稀疏點數本身不足以證明重建品質。",
    "獨立精度評估需要控制點、測量尺度或真值幾何資料。",
)


def generate_html_report(
    path: Path,
    project: BenchmarkProject,
    analysis: BenchmarkAnalysisResult,
    chart_paths: list[Path],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    config_by_id = {row.experiment_id: row for row in project.enabled_experiments}
    charts = [p for p in chart_paths if p.exists()]
    overview = {
        "效能測試名稱": project.name,
        "日期": (project.finished_at or project.created_at).isoformat(),
        "資料集": PathDisplaySanitizer.sanitize(project.image_folder),
        "影像數量": project.metadata.get("dataset_image_count", "無資料"),
        "RealityScan 版本": project.metadata.get("realityscan_version") or "無資料",
        "工具版本": f"RealityScan Benchmark Assistant v{__version__}",
        "實驗數": analysis.experiment_count,
        "成功執行": analysis.successful_count,
        "失敗執行": analysis.failed_count,
        "總執行時間": f"{analysis.total_runtime_seconds:.1f} 秒",
    }
    design = _design(project.enabled_experiments)
    warning_section = (
        '<section class="warning"><h2>資料完整性與科學提醒</h2>'
        + _items(analysis.warnings)
        + "</section>"
        if analysis.warnings else ""
    )
    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(project.name)} — RealityScan 效能測試報告</title>
<style>{_css()}</style></head><body><main>
<header><p class="eyebrow">RealityScan Benchmark Assistant v{__version__}</p>
<h1>RealityScan 效能測試報告</h1><p>研究級描述性分析與可重現實驗紀錄</p></header>
<section><h2>1. 效能測試概覽</h2>{_key_value_table(overview)}</section>
<section><h2>2. 實驗設計</h2>{_key_value_table(design)}</section>
<section><h2>3. 實驗設定</h2>{_configuration_table(project.enabled_experiments)}</section>
<section><h2>4. 結果</h2>{_results_table(project.results, config_by_id)}</section>
<section><h2>5. 關鍵比較</h2>{_leaders(analysis)}</section>
<section><h2>6. 參數效果</h2>{_sweep_section(analysis)}</section>
<section><h2>7. Pareto 分析</h2>{_pareto_section(analysis, charts, config_by_id)}</section>
<section><h2>8. 科學詮釋</h2>{_items(analysis.observations, "沒有可用觀察結果。")}</section>
<section><h2>9. 限制</h2>{_items(list(LIMITATIONS))}</section>
<section><h2>10. 可重現性</h2>{_key_value_table(_reproducibility(project))}</section>
{warning_section}
</main></body></html>"""
    path.write_text(html, encoding="utf-8")
    return path


def _design(experiments: list[ExperimentConfig]) -> dict[str, object]:
    modes = {row.sweep_mode for row in experiments if row.sweep_mode}
    mode = "手動"
    if modes == {"full_factorial"}:
        mode = "全因子"
    elif modes == {"one_factor_at_a_time"}:
        mode = "單因子法（OFAT）"
    varied = sorted({p for row in experiments for p in row.varied_parameters})
    values = {
        parameter: list(dict.fromkeys(getattr(row, parameter) for row in experiments))
        for parameter in varied
    }
    return {
        "設計類型": mode,
        "變動參數": "、".join(varied) if varied else "無（手動設計）",
        "參數值": json_display(values) if values else "無",
        "基準設定": "有" if any(row.experiment_role == "BASELINE" for row in experiments) else "無",
        "實驗數": len(experiments),
    }


def _configuration_table(experiments: list[ExperimentConfig]) -> str:
    rows = [[
        row.experiment_id, row.name,
        {"High": "高", "Normal": "一般"}.get(
            row.feature_detection_quality, row.feature_detection_quality
        ),
        row.max_features_per_image,
        {"Low": "低", "Medium": "中", "High": "高"}.get(
            row.image_overlap, row.image_overlap
        ),
        row.max_feature_reprojection_error,
    ] for row in experiments]
    return _table(["實驗 ID", "實驗", "品質", "特徵數", "重疊", "重投影上限"], rows)


def _results_table(
    results: list[ExperimentResult], configs: dict[str, ExperimentConfig]
) -> str:
    rows = []
    for row in results:
        rate = row.registration_rate
        rows.append([
            row.experiment_name, _status(row.status.value), row.registered_images,
            f"{rate * 100:.2f}%" if rate is not None else None,
            row.component_count, row.sparse_point_count, row.mean_reprojection_error,
            f"{row.runtime_seconds:.2f} s" if row.runtime_seconds is not None else None,
        ])
    return _table(
        ["實驗", "狀態", "已註冊", "註冊率", "元件", "稀疏點", "報告重投影誤差", "執行時間"], rows
    )


def _leaders(analysis: BenchmarkAnalysisResult) -> str:
    if not analysis.metric_leaders:
        return "<p class='muted'>沒有可用於指標比較的成功實驗結果。</p>"
    labels = {
        "highest_registration_rate": "最高註冊率",
        "fastest_runtime": "最短執行時間",
        "lowest_reported_reprojection_error": "最低報告重投影誤差",
        "highest_sparse_point_count": "最高稀疏點數",
    }
    rows = []
    for key, leader in analysis.metric_leaders.items():
        value = leader.value * 100 if key == "highest_registration_rate" else leader.value
        unit = "%" if key == "highest_registration_rate" else leader.unit
        names = "、".join(leader.experiment_names)
        if len(leader.experiment_names) > 1:
            names += "（平手）"
        rows.append([labels[key], names, f"{value:.3g} {unit}"])
    return _table(["比較", "實驗", "數值"], rows)


def _sweep_section(analysis: BenchmarkAnalysisResult) -> str:
    if not analysis.sweep_analysis:
        return "<p class='muted'>本次結果沒有可作單參數敏感度分析的 sweep。</p>"
    blocks = []
    for sweep in analysis.sweep_analysis:
        rows = [[
            gain.from_value, gain.to_value, _fmt(gain.delta_registration_pp, " pp"),
            _fmt(gain.delta_runtime_seconds, " s"),
            _fmt(gain.registration_gain_per_extra_minute, " pp/min"),
        ] for gain in sweep.marginal_gains]
        blocks.append(
            f"<h3>{escape(sweep.parameter)}</h3>" +
            _table(["起始值", "終止值", "註冊率差", "執行時間差", "每額外分鐘註冊率增益"], rows) +
            _items(sweep.observations, "未偵測到符合規則的報酬遞減跡象。")
        )
    return "".join(blocks)


def _pareto_section(
    analysis: BenchmarkAnalysisResult,
    charts: list[Path],
    configs: dict[str, ExperimentConfig],
) -> str:
    chart = next((p for p in charts if p.name == "pareto_registration_runtime.png"), None)
    image = (
        f'<img src="charts/{escape(chart.name)}" alt="註冊率與執行時間 Pareto 圖">'
        if chart else ""
    )
    if not analysis.pareto_experiment_ids:
        return image + "<p class='muted'>至少需要兩筆具有註冊率與執行時間的成功結果。</p>"
    rows = [
        f"Pareto-efficient：{configs[item].name}（{item}）" if item in configs
        else f"Pareto-efficient：{item}"
        for item in analysis.pareto_experiment_ids
    ]
    return image + _items(rows)


def _reproducibility(project: BenchmarkProject) -> dict[str, object]:
    return {
        "資料集指紋": project.metadata.get("dataset_fingerprint") or "無資料",
        "RealityScan 版本": project.metadata.get("realityscan_version") or "無資料",
        "工具版本": __version__,
        "實驗設定檔": "benchmark.json",
        "Sweep 定義": "sweeps/（如有）",
        "效能測試 ID": project.benchmark_id,
        "作業系統": project.metadata.get("operating_system") or "無資料",
        "Python 版本": project.metadata.get("python_version") or "無資料",
    }


def _key_value_table(values: dict[str, object]) -> str:
    return _table(["欄位", "內容"], [[key, value] for key, value in values.items()])


def _table(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(_display(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (
        f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def _items(values: list[str], empty: str = "") -> str:
    if not values:
        return f"<p class='muted'>{escape(empty)}</p>" if empty else ""
    return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"


def _display(value: object) -> str:
    return "無資料" if value is None else str(value)


def json_display(value: dict[str, list[object]]) -> str:
    return "；".join(f"{key}={', '.join(map(str, values))}" for key, values in value.items())


def _status(value: str) -> str:
    return {
        "PENDING": "等待中",
        "RUNNING": "執行中",
        "SUCCESS": "成功",
        "FAILED": "失敗",
        "TIMEOUT": "逾時",
        "DRY_RUN": "模擬執行",
        "SKIPPED": "已略過",
        "CANCELLED": "已取消",
    }.get(value, value)


def _fmt(value: float | None, suffix: str) -> str:
    return "無資料" if value is None else f"{value:.2f}{suffix}"


def _css() -> str:
    return """
:root{color-scheme:light;--ink:#17212b;--muted:#65717d;--line:#d9e0e6;
--accent:#245b85;--paper:#fff;--bg:#f3f5f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 "Microsoft JhengHei",Arial,sans-serif}
main{max-width:1120px;margin:32px auto;padding:0 28px 64px}
header,section{background:var(--paper);border:1px solid var(--line);
padding:24px 28px;margin:0 0 18px}
header{border-top:5px solid var(--accent)}
h1{font-size:30px;margin:.15em 0}
h2{font-size:20px;border-bottom:1px solid var(--line);padding-bottom:10px}
h3{font-size:16px}
.eyebrow{color:var(--accent);font-weight:700;letter-spacing:.04em}
.muted{color:var(--muted)}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#eef3f7;color:#29475f}
img{display:block;max-width:820px;width:100%;margin:18px auto}
.warning{border-left:5px solid #a66b17}
li{margin:.35em 0}
@media print{body{background:#fff}main{margin:0;max-width:none}
section,header{break-inside:avoid;border-left:0;border-right:0}}
"""
