from __future__ import annotations

import csv
from pathlib import Path

from rs_benchmark.models import ExperimentConfig, ExperimentResult, ExperimentStatus
from rs_benchmark.reports.charts import generate_charts
from rs_benchmark.reports.comparison import compare_results
from rs_benchmark.reports.csv_exporter import CSV_FIELDS, export_results_csv


def test_csv_fields_none_failed_and_utf8(tmp_path: Path) -> None:
    path = export_results_csv(
        tmp_path / "results.csv",
        [
            ExperimentResult("預設", ExperimentStatus.SUCCESS, 10, 9, runtime_seconds=4.5),
            ExperimentResult("失敗", ExperimentStatus.FAILED),
        ],
        [ExperimentConfig(name="預設"), ExperimentConfig(name="失敗")],
    )

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert tuple(rows[0]) == CSV_FIELDS
    assert rows[0]["registration_rate"] == "90.0"
    assert rows[1]["registered_images"] == "N/A"
    assert rows[1]["status"] == "FAILED"


def test_charts_generate_only_for_valid_metrics(tmp_path: Path) -> None:
    results = [
        ExperimentResult(
            "A", ExperimentStatus.SUCCESS, 10, 9, sparse_point_count=100,
            mean_reprojection_error=0.5, runtime_seconds=2,
        ),
        ExperimentResult(
            "B", ExperimentStatus.SUCCESS, 10, 8, sparse_point_count=80,
            mean_reprojection_error=0.7, runtime_seconds=3,
        ),
    ]

    paths = generate_charts(tmp_path, results)

    assert {path.name for path in paths} == {
        "registration_rate.png", "runtime.png", "mean_reprojection_error.png",
        "sparse_point_count.png",
    }
    assert all(path.stat().st_size > 0 for path in paths)


def test_all_missing_metrics_create_no_charts(tmp_path: Path) -> None:
    assert generate_charts(
        tmp_path, [ExperimentResult("失敗", ExperimentStatus.FAILED)]
    ) == []


def test_descriptive_comparison_and_all_none() -> None:
    a = ExperimentResult(
        "A", ExperimentStatus.SUCCESS, 10, 9, sparse_point_count=100,
        mean_reprojection_error=0.7, runtime_seconds=5,
    )
    b = ExperimentResult(
        "B", ExperimentStatus.SUCCESS, 10, 8, sparse_point_count=120,
        mean_reprojection_error=0.5, runtime_seconds=3,
    )
    comparison = compare_results([a, b])

    assert comparison["highest_registration_rate"] is a
    assert comparison["lowest_runtime"] is b
    assert comparison["lowest_reprojection_error"] is b
    assert comparison["highest_sparse_point_count"] is b
    assert all(value is None for value in compare_results([ExperimentResult("N/A")]).values())
