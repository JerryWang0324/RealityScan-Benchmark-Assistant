from __future__ import annotations

from rs_benchmark.analysis.metric_champions import parameter_champions
from rs_benchmark.models import ExperimentResult, ExperimentStatus


def row(
    name: str,
    identifier: str,
    registered: int,
    total: int,
    runtime: float,
    components: int,
    *,
    largest: int | None = None,
    sparse: int | None = None,
    reprojection: float | None = None,
    status: ExperimentStatus = ExperimentStatus.SUCCESS,
) -> ExperimentResult:
    return ExperimentResult(
        experiment_name=name, experiment_id=identifier, status=status,
        registered_images=registered, total_images=total,
        runtime_seconds=runtime, component_count=components,
        largest_component_camera_count=largest,
        sparse_point_count=sparse,
        mean_reprojection_error=reprojection,
    )


def test_champions_use_group_means_and_merge_multiple_wins() -> None:
    rows = [
        row("不穩定", "a", 100, 100, 5, 1),
        row("不穩定", "a", 0, 100, 5, 1),
        row("穩定", "b", 80, 100, 10, 2),
        row("穩定", "b", 80, 100, 10, 2),
        row("失敗", "failed", 100, 100, 1, 1, status=ExperimentStatus.FAILED),
    ]

    champions = {item.experiment_id: item for item in parameter_champions(rows)}
    assert set(champions) == {"a", "b"}
    assert champions["a"].values["registration_rate"] == 0.5
    assert champions["b"].values["registered_images"] == 80
    assert {"registered_images", "registration_rate"} <= set(champions["b"].winning_metrics)
    assert {"runtime_seconds", "component_count"} <= set(champions["a"].winning_metrics)


def test_champion_ties_use_registration_then_time_then_components() -> None:
    rows = [
        row("註冊率高", "rate", 80, 80, 20, 2, sparse=1000),
        row("註冊率低", "low", 80, 100, 1, 1, sparse=1000),
    ]
    champions = {item.experiment_id: item for item in parameter_champions(rows)}
    assert "sparse_point_count" in champions["rate"].winning_metrics

    rows = [
        row("較快", "fast", 80, 80, 10, 2, sparse=1000),
        row("較慢", "slow", 80, 80, 20, 1, sparse=1000),
    ]
    champions = {item.experiment_id: item for item in parameter_champions(rows)}
    assert "sparse_point_count" in champions["fast"].winning_metrics

    rows = [
        row("單一元件", "one", 80, 80, 10, 1, sparse=1000),
        row("兩個元件", "two", 80, 80, 10, 2, sparse=1000),
    ]
    champions = {item.experiment_id: item for item in parameter_champions(rows)}
    assert set(champions) == {"one"}
    assert "sparse_point_count" in champions["one"].winning_metrics


def test_champion_view_never_exceeds_seven_groups() -> None:
    rows = [
        row(f"設定 {index}", f"id{index}", 50 + index, 100, 30 - index, 1 + index)
        for index in range(10)
    ]
    assert len(parameter_champions(rows)) <= 7


def test_all_seven_result_metrics_can_mark_a_winner() -> None:
    rows = [
        row("甲", "a", 80, 100, 10, 1, largest=70, sparse=1000, reprojection=.5),
        row("乙", "b", 75, 75, 12, 2, largest=75, sparse=2000, reprojection=.4),
    ]
    winners = parameter_champions(rows)
    assert {metric for item in winners for metric in item.winning_metrics} == {
        "registered_images", "registration_rate", "component_count",
        "largest_component_camera_count", "sparse_point_count",
        "mean_reprojection_error", "runtime_seconds",
    }
