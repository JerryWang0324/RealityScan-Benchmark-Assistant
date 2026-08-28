from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rs_benchmark.models import ExperimentConfig, ExperimentResult
from rs_benchmark.reports.sweep_analysis import varied_parameters


def generate_charts(
    output_directory: Path,
    results: list[ExperimentResult],
    experiments: list[ExperimentConfig] | None = None,
) -> list[Path]:
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
    if experiments:
        generated.extend(generate_parameter_charts(output_directory, results, experiments))
    return generated


def generate_parameter_charts(
    output_directory: Path,
    results: list[ExperimentResult],
    experiments: list[ExperimentConfig],
) -> list[Path]:
    """Create parameter-effect charts only for unambiguous single-variable sweeps."""
    output_directory.mkdir(parents=True, exist_ok=True)
    result_by_id = {item.experiment_id: item for item in results if item.experiment_id}
    result_by_name = {item.experiment_name: item for item in results}
    groups: dict[str, list[ExperimentConfig]] = {}
    for experiment in experiments:
        if experiment.sweep_id:
            groups.setdefault(experiment.sweep_id, []).append(experiment)

    labels = {
        "feature_detection_quality": "特徵偵測品質",
        "max_features_per_image": "每張影像特徵數",
        "image_overlap": "影像重疊程度",
        "max_feature_reprojection_error": "最大特徵重投影誤差",
    }
    metrics: tuple[
        tuple[str, str, Callable[[ExperimentResult], float | int | None]], ...
    ] = (
        (
            "registration_rate",
            "註冊率（%）",
            lambda r: (
                r.registration_rate * 100 if r.registration_rate is not None else None
            ),
        ),
        ("runtime", "執行時間（秒）", lambda r: r.runtime_seconds),
        ("mean_reprojection_error", "平均重投影誤差（像素）", lambda r: r.mean_reprojection_error),
        ("sparse_point_count", "稀疏點數", lambda r: r.sparse_point_count),
    )
    generated: list[Path] = []
    for sweep_id, configs in groups.items():
        varied = varied_parameters(configs)
        if len(varied) != 1:
            continue
        parameter = varied[0]
        pairs = []
        for config in configs:
            result = result_by_id.get(config.experiment_id) or result_by_name.get(config.name)
            if result:
                pairs.append((getattr(config, parameter), result))
        pairs.sort(key=lambda pair: str(pair[0]) if isinstance(pair[0], str) else pair[0])
        for metric_name, ylabel, extractor in metrics:
            values = [(x, extractor(result)) for x, result in pairs]
            valid = [(x, y) for x, y in values if y is not None]
            if len(valid) < 2:
                continue
            path = output_directory / f"{sweep_id}_{parameter}_{metric_name}.png"
            generated.append(_line_chart(path, labels[parameter], ylabel, valid))
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


def _line_chart(
    path: Path, xlabel: str, ylabel: str, values: list[tuple[object, float | int]]
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    plt.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "Noto Sans CJK TC", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axis = plt.subplots(figsize=(7.5, 5.2))
    x_values = [item[0] for item in values]
    y_values = [item[1] for item in values]
    axis.plot(x_values, y_values, marker="o", linewidth=2, color="#2878B5")
    axis.set_title(f"{xlabel}與{ylabel}的關係")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return path


class ChartGenerator:
    generate = staticmethod(generate_charts)
