from __future__ import annotations

from rs_benchmark.analysis.comparison import metric_leaders, successful_results
from rs_benchmark.analysis.interpretation import build_observations, scientific_warnings
from rs_benchmark.analysis.metrics import BenchmarkAnalysisResult, MarginalGain, MetricLeader
from rs_benchmark.analysis.pareto import (
    registration_reprojection_frontier,
    registration_runtime_frontier,
)
from rs_benchmark.analysis.sweep_analysis import analyze_sweeps
from rs_benchmark.models import BenchmarkProject, ExperimentStatus


def analyze_benchmark(project: BenchmarkProject) -> BenchmarkAnalysisResult:
    successful = successful_results(project.results)
    failed = [
        row for row in project.results
        if row.status in {ExperimentStatus.FAILED, ExperimentStatus.TIMEOUT}
    ]
    sweeps, relative = analyze_sweeps(project.enabled_experiments, project.results)
    warnings = _integrity_warnings(project)
    analysis = BenchmarkAnalysisResult(
        experiment_count=len(project.enabled_experiments),
        result_count=len(project.results),
        successful_count=len(successful),
        failed_count=len(failed),
        total_runtime_seconds=sum(row.runtime_seconds or 0 for row in project.results),
        metric_leaders=metric_leaders(project.results),
        pareto_experiment_ids=registration_runtime_frontier(project.results),
        pareto_reprojection_experiment_ids=(
            registration_reprojection_frontier(project.results)
            if sum(row.mean_reprojection_error is not None for row in successful) >= 2 else []
        ),
        relative_metrics=relative,
        sweep_analysis=sweeps,
        warnings=warnings,
    )
    analysis.observations = build_observations(analysis)
    analysis.warnings.extend(scientific_warnings(analysis))
    return analysis


def _integrity_warnings(project: BenchmarkProject) -> list[str]:
    warnings: list[str] = []
    expected = len(project.enabled_experiments) * project.repeat_count
    if len(project.results) != expected:
        warnings.append(
            f"結果完整性警告：預期 {expected} 筆結果，實際為 {len(project.results)} 筆。"
        )
    expected_ids = {row.experiment_id for row in project.enabled_experiments}
    actual_ids = {row.experiment_id for row in project.results if row.experiment_id}
    missing = sorted(expected_ids - actual_ids)
    unknown = sorted(actual_ids - expected_ids)
    if missing:
        warnings.append("結果完整性警告：缺少實驗 ID：" + "、".join(missing))
    if unknown:
        warnings.append("結果完整性警告：出現未知實驗 ID：" + "、".join(unknown))
    return warnings


__all__ = [
    "BenchmarkAnalysisResult", "MarginalGain", "MetricLeader", "analyze_benchmark",
    "analyze_sweeps", "metric_leaders", "registration_runtime_frontier",
]
