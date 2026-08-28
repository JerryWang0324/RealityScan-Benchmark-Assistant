from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rs_benchmark.models import ExperimentResult


def generate_charts(output_directory: Path, results: list[ExperimentResult]) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    specifications: tuple[
        tuple[str, str, str, Callable[[ExperimentResult], float | int | None]], ...
    ] = (
        (
            "registration_rate.png", "實驗與註冊率比較",
            "註冊率（%）",
            lambda item: (
                item.registration_rate * 100 if item.registration_rate is not None else None
            ),
        ),
        (
            "runtime.png", "實驗與執行時間比較", "執行時間（秒）",
            lambda item: item.runtime_seconds,
        ),
        (
            "mean_reprojection_error.png", "實驗與平均重投影誤差比較",
            "平均重投影誤差（像素）", lambda item: item.mean_reprojection_error,
        ),
        (
            "sparse_point_count.png", "實驗與稀疏點數比較",
            "稀疏點數", lambda item: item.sparse_point_count,
        ),
    )
    generated: list[Path] = []
    for filename, title, ylabel, extractor in specifications:
        values = [(item.experiment_name, extractor(item)) for item in results]
        valid = [(name, value) for name, value in values if value is not None]
        minimum = 2 if filename == "mean_reprojection_error.png" else 1
        if len(valid) < minimum:
            continue
        generated.append(_bar_chart(output_directory / filename, title, ylabel, valid))
    return generated


def _bar_chart(
    path: Path, title: str, ylabel: str, values: list[tuple[str, float | int]]
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    plt.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "Noto Sans CJK TC", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False

    width = max(7.0, min(14.0, len(values) * 1.35))
    figure, axis = plt.subplots(figsize=(width, 5.2))
    names = [name for name, _ in values]
    metrics = [value for _, value in values]
    axis.bar(names, metrics, color="#2878B5")
    axis.set_title(title)
    axis.set_xlabel("實驗")
    axis.set_ylabel(ylabel)
    axis.tick_params(axis="x", labelrotation=25)
    for label in axis.get_xticklabels():
        label.set_horizontalalignment("right")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return path


class ChartGenerator:
    generate = staticmethod(generate_charts)
