from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from rs_benchmark.analysis import analyze_benchmark
from rs_benchmark.analysis.pareto import (
    registration_runtime_frontier,
    registration_runtime_frontier_rows,
)
from rs_benchmark.analysis.sweep_analysis import analyze_sweeps
from rs_benchmark.models import (
    BenchmarkProject,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
)
from rs_benchmark.reports.html_report import generate_html_report
from rs_benchmark.reports.reproducibility import export_reproducibility_package
from rs_benchmark.services.benchmark_runner import BenchmarkRunner
from rs_benchmark.utils.path_sanitizer import PathDisplaySanitizer


def result(
    name: str,
    identifier: str,
    registered: int | None,
    runtime: float | None,
    *,
    total: int | None = 100,
    reprojection: float | None = None,
    sparse: int | None = None,
    status: ExperimentStatus = ExperimentStatus.SUCCESS,
) -> ExperimentResult:
    return ExperimentResult(
        experiment_name=name,
        experiment_id=identifier,
        status=status,
        total_images=total,
        registered_images=registered,
        runtime_seconds=runtime,
        mean_reprojection_error=reprojection,
        sparse_point_count=sparse,
    )


def test_pareto_dominated_multiple_frontier_and_exact_tie() -> None:
    rows = [
        result("A", "a", 98, 300),
        result("B", "b", 96, 170),
        result("B tie", "b2", 96, 170),
        result("C", "c", 94, 280),
    ]
    assert registration_runtime_frontier(rows) == ["a", "b", "b2"]


def test_pareto_missing_single_and_empty() -> None:
    assert registration_runtime_frontier([]) == []
    assert registration_runtime_frontier([result("A", "a", 98, 300)]) == []
    assert registration_runtime_frontier([
        result("A", "a", 98, None), result("B", "b", None, 20)
    ]) == []


def test_pareto_frontier_tracks_repeated_runs_individually() -> None:
    slower = result("A", "same", 100, 20)
    faster = result("A", "same", 100, 10)
    assert registration_runtime_frontier([slower, faster]) == ["same"]
    assert registration_runtime_frontier_rows([slower, faster]) == [faster]


def test_pareto_keeps_one_component_and_faster_two_component_tradeoff() -> None:
    two_components = result("最快但分裂", "split", 100, 10)
    two_components.component_count = 2
    one_component_fast = result("單一元件快", "one_fast", 100, 17)
    one_component_fast.component_count = 1
    one_component_slow = result("單一元件慢", "one_slow", 100, 20)
    one_component_slow.component_count = 1

    rows = [two_components, one_component_slow, one_component_fast]
    assert registration_runtime_frontier_rows(rows) == [one_component_fast, two_components]
    assert registration_runtime_frontier(rows) == ["one_fast", "split"]


def test_pareto_prefers_reported_fewer_components_when_primary_metrics_tie() -> None:
    missing = result("未知", "missing", 100, 9)
    three = result("三元件", "three", 100, 9)
    three.component_count = 3
    two = result("兩元件", "two", 100, 9)
    two.component_count = 2

    assert registration_runtime_frontier([missing, three, two]) == ["two"]


def test_pareto_report_identifies_selected_repeat(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    split = result("分裂", "a", 100, 10)
    split.component_count = 2
    connected = result("完整", "b", 100, 17)
    connected.component_count = 1
    connected.repeat_index = 3
    connected.repeat_count = 3
    project.results = [split, connected]

    path = generate_html_report(
        tmp_path / "report.html", project, analyze_benchmark(project), []
    )
    report = path.read_text(encoding="utf-8")
    assert "Pareto 前緣：完整（第 3 / 3 次；元件數 1；註冊率 100.0%；執行時間 17.000 秒）" in report
    assert "Pareto 前緣：分裂" in report


def test_analysis_tie_warnings_and_no_unsupported_best_claim(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    project.results = [
        result("A", "a", 98, 120, reprojection=.7, sparse=1000),
        result("B", "b", 98, 160, reprojection=.6, sparse=1500),
    ]
    analysis = analyze_benchmark(project)
    leader = analysis.metric_leaders["highest_registration_rate"]
    assert leader.experiment_ids == ["a", "b"]
    assert any("平手" in line for line in analysis.observations)
    assert any("絕對三維精度" in line for line in analysis.warnings)
    assert any("稀疏點數" in line for line in analysis.warnings)
    assert "最佳整體" not in json.dumps(analysis.to_dict(), ensure_ascii=False)


def test_all_failed_analysis_is_still_serializable(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    project.results = [
        result("A", "a", None, None, status=ExperimentStatus.FAILED),
        result("B", "b", None, None, status=ExperimentStatus.TIMEOUT),
    ]
    analysis = analyze_benchmark(project)
    assert analysis.successful_count == 0
    assert analysis.metric_leaders == {}
    assert analysis.pareto_experiment_ids == []
    assert "沒有可用" in analysis.observations[0]


def test_sweep_sorted_delta_none_handling_and_diminishing_returns() -> None:
    configs = [
        ExperimentConfig(
            name=name, experiment_id=identifier, max_features_per_image=value,
            sweep_id="s1", sweep_mode="one_factor_at_a_time",
            experiment_role="BASELINE" if value == 20_000 else "SWEEP",
            varied_parameters=("max_features_per_image",),
        )
        for name, identifier, value in (
            ("80k", "e80", 80_000),
            ("20k", "e20", 20_000),
            ("40k", "e40", 40_000),
        )
    ]
    rows = [
        result("80k", "e80", 98, 390),
        result("20k", "e20", 92, 140),
        result("40k", "e40", 97, 220),
    ]
    sweeps, relative = analyze_sweeps(configs, rows)
    assert [p["parameter_value"] for p in sweeps[0].points] == [20_000, 40_000, 80_000]
    assert sweeps[0].marginal_gains[0].delta_registration_pp == 5
    assert sweeps[0].marginal_gains[0].delta_runtime_seconds == 80
    assert sweeps[0].marginal_gains[1].registration_gain_per_extra_minute is not None
    assert sweeps[0].observations
    assert relative

    rows[1].runtime_seconds = 0
    sweeps, _ = analyze_sweeps(configs, rows)
    assert sweeps[0].marginal_gains[0].runtime_change_percent is None


def test_html_report_package_and_path_privacy(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    project.image_folder = Path(r"C:\Users\User Name\Desktop\Test")
    project.results = [
        result("A", "a", None, None, status=ExperimentStatus.FAILED),
        result("B", "b", 97, 190, reprojection=.65),
    ]
    project.metadata = {"dataset_image_count": 100, "dataset_fingerprint": "sha256:test"}
    project.run_directory = tmp_path
    summary = tmp_path / "summary"
    (summary / "charts").mkdir(parents=True)
    (tmp_path / "experiments" / "001_a").mkdir(parents=True)
    (tmp_path / "experiments" / "001_a" / "config.json").write_text(
        json.dumps({"image_folder": r"C:\Users\User Name\Desktop\Test"})
    )
    for name, text in (
        ("results.csv", "experiment,status\nA,FAILED\n"),
        ("analysis.json", "{}"),
        ("benchmark_summary.json", "{}"),
    ):
        (summary / name).write_text(text, encoding="utf-8")
    analysis = analyze_benchmark(project)
    report = generate_html_report(summary / "report.html", project, analysis, [])
    report_text = report.read_text(encoding="utf-8")
    assert "RealityScan 效能測試報告" in report_text
    assert "失敗" in report_text
    assert r"C:\Users\User Name" not in report_text
    package = export_reproducibility_package(summary / "package.zip", project, tmp_path)
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        assert {"benchmark.json", "results.csv", "analysis.json", "report.html"} <= names
        assert not any("image" in name.lower() or "cache" in name.lower() for name in names)
        benchmark = archive.read("benchmark.json").decode("utf-8")
        assert r"C:\\Users\\User Name" not in benchmark
        config = archive.read("experiment_configs/001_a.json").decode("utf-8")
        assert "User Name" not in config


def test_runner_report_level_integration(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    project.results = [
        result("A", "a", 92, 120, reprojection=.72),
        result("B", "b", 97, 190, reprojection=.65),
    ]
    project.run_directory = tmp_path
    (tmp_path / "summary" / "charts").mkdir(parents=True)
    (tmp_path / "experiments").mkdir()
    BenchmarkRunner._write_reports(project, tmp_path)
    assert (tmp_path / "summary" / "analysis.json").is_file()
    assert (tmp_path / "summary" / "report.html").is_file()
    assert (tmp_path / "summary" / "charts" / "pareto_registration_runtime.png").is_file()
    report = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert 'src="charts/pareto_registration_runtime.png"' in report
    assert list((tmp_path / "summary").glob("*_reproducibility.zip"))


def test_path_sanitizer_windows_path() -> None:
    sanitized = PathDisplaySanitizer.sanitize(r"C:\Users\User Name\Desktop\Test")
    assert sanitized == "<dataset>/Test"
    assert "User Name" not in sanitized


def test_path_sanitizer_redacts_paths_embedded_in_diagnostics() -> None:
    payload = {
        "error_message": r"Unable to read C:\Users\User Name\Desktop\Test\image.jpg",
        "note": "Unable to read /home/private-user/datasets/test/image.jpg",
    }
    sanitized = PathDisplaySanitizer.sanitize_structure(payload)
    assert sanitized["error_message"] == r"Unable to read <user>\Desktop\Test\image.jpg"
    assert sanitized["note"] == "Unable to read <user>/datasets/test/image.jpg"
    assert "User Name" not in json.dumps(sanitized)
    assert "private-user" not in json.dumps(sanitized)


def test_html_report_embeds_single_parameter_sweep_charts(tmp_path: Path) -> None:
    project = project_fixture(tmp_path)
    project.experiments = [
        ExperimentConfig(
            name=name,
            experiment_id=identifier,
            max_features_per_image=value,
            sweep_id="sweep_features",
            sweep_mode="one_factor_at_a_time",
            experiment_role="BASELINE" if value == 20_000 else "SWEEP",
            varied_parameters=("max_features_per_image",),
        )
        for name, identifier, value in (
            ("20k", "e20", 20_000),
            ("40k", "e40", 40_000),
        )
    ]
    project.results = [result("20k", "e20", 92, 140), result("40k", "e40", 97, 220)]
    charts = tmp_path / "summary" / "charts"
    charts.mkdir(parents=True)
    registration_chart = charts / (
        "sweep_features_max_features_per_image_registration_rate.png"
    )
    runtime_chart = charts / "sweep_features_max_features_per_image_runtime.png"
    registration_chart.touch()
    runtime_chart.touch()

    report = generate_html_report(
        tmp_path / "summary" / "report.html",
        project,
        analyze_benchmark(project),
        [registration_chart, runtime_chart],
    )
    report_text = report.read_text(encoding="utf-8")
    assert f'src="charts/{registration_chart.name}"' in report_text
    assert f'src="charts/{runtime_chart.name}"' in report_text


def project_fixture(tmp_path: Path) -> BenchmarkProject:
    project = BenchmarkProject(
        name="Phase 5 測試",
        image_folder=tmp_path,
        output_directory=tmp_path,
        experiments=[
            ExperimentConfig(name="A", experiment_id="a"),
            ExperimentConfig(name="B", experiment_id="b"),
        ],
        created_at=datetime.now().astimezone(),
    )
    return project
