from __future__ import annotations

from pathlib import Path

import pytest

from rs_benchmark.models import (
    BaselineConfig,
    ExperimentConfig,
    ExperimentResult,
    ExperimentStatus,
    ParameterSweepConfig,
    SweepDefinition,
    SweepMode,
)
from rs_benchmark.reports.charts import generate_parameter_charts
from rs_benchmark.reports.sweep_analysis import relative_to_baseline
from rs_benchmark.services.experiment_generator import ExperimentGenerator, partition_duplicates


def full_config(**updates: object) -> ParameterSweepConfig:
    values = {
        "feature_detection_qualities": ["High", "Normal"],
        "max_features_per_image": [20_000, 40_000, 80_000],
        "image_overlaps": ["Medium", "High"],
        "max_feature_reprojection_errors": [2.0],
    }
    values.update(updates)
    return ParameterSweepConfig(**values)  # type: ignore[arg-type]


def test_config_serialization_validation_and_empty_values() -> None:
    config = full_config()
    assert ParameterSweepConfig.from_dict(config.to_dict()) == config
    assert config.experiment_count == 12
    with pytest.raises(ValueError, match="cannot be empty"):
        full_config(image_overlaps=[])
    with pytest.raises(ValueError, match="positive"):
        full_config(max_features_per_image=[-500])
    with pytest.raises(ValueError, match="one of"):
        full_config(image_overlaps=["Unknown"])


def test_full_factorial_has_every_combination_once() -> None:
    experiments = ExperimentGenerator().generate(full_config())
    signatures = {item.parameter_signature for item in experiments}
    assert len(experiments) == len(signatures) == 12
    assert ("High", 20_000, "Medium", 2.0) in signatures
    assert ("Normal", 80_000, "High", 2.0) in signatures


def test_ofat_changes_only_one_factor_and_includes_baseline_once() -> None:
    baseline = BaselineConfig()
    config = ParameterSweepConfig(
        feature_detection_qualities=["High"],
        max_features_per_image=[20_000, 40_000, 80_000],
        image_overlaps=["Medium"],
        max_feature_reprojection_errors=[2.0],
        mode=SweepMode.ONE_FACTOR_AT_A_TIME,
        baseline=baseline,
    )
    experiments = ExperimentGenerator().generate(config)
    assert len(experiments) == config.experiment_count == 3
    assert [item.experiment_role for item in experiments].count("BASELINE") == 1
    for experiment in experiments:
        changed = sum(
            getattr(experiment, name) != value
            for name, value in baseline.to_dict().items()
        )
        assert changed <= 1


def test_duplicate_detection_naming_and_ids() -> None:
    generated = ExperimentGenerator().generate(full_config())
    unique, duplicates = partition_duplicates(generated, [generated[0]])
    assert len(unique) == 11
    assert duplicates == [generated[0]]
    assert generated[0].machine_name == "QHigh_F20000_OMedium_R2.0"
    assert generated[0].name == "High | 20k | Medium | 2.0px"
    assert len({item.experiment_id for item in generated}) == 12
    assert all(
        "/" not in item.experiment_id and "\\" not in item.experiment_id
        for item in generated
    )


def test_sweep_definition_save_and_load(tmp_path: Path) -> None:
    config = full_config()
    experiments = ExperimentGenerator().generate(config)
    definition = ExperimentGenerator.definition(config, experiments)
    path = definition.save(tmp_path / "sweep.json")
    restored = SweepDefinition.load(path)
    assert restored.to_dict() == definition.to_dict()
    assert "image_folder" not in path.read_text(encoding="utf-8")


def test_relative_metrics_none_zero_and_percentage_points() -> None:
    baseline = ExperimentResult(
        "基準", ExperimentStatus.SUCCESS, 100, 95,
        sparse_point_count=100, mean_reprojection_error=0.7, runtime_seconds=10,
    )
    result = ExperimentResult(
        "變體", ExperimentStatus.SUCCESS, 100, 98,
        sparse_point_count=130, mean_reprojection_error=0.5, runtime_seconds=15,
    )
    relative = relative_to_baseline(result, baseline)
    assert relative.registration_rate_delta_pp == pytest.approx(3.0)
    assert relative.runtime_delta_seconds == 5
    assert relative.runtime_ratio == 1.5
    assert relative.reprojection_error_delta == pytest.approx(-0.2)
    assert relative.sparse_point_delta == 30
    missing = relative_to_baseline(
        ExperimentResult("無資料"), ExperimentResult("零", runtime_seconds=0)
    )
    assert missing.runtime_ratio is None
    assert missing.registration_rate_delta_pp is None


def test_single_variable_parameter_chart(tmp_path: Path) -> None:
    config = full_config(
        feature_detection_qualities=["High"],
        image_overlaps=["Medium"],
    )
    experiments = ExperimentGenerator().generate(config)
    results = [
        ExperimentResult(
            item.name, ExperimentStatus.SUCCESS, 10, 8 + index,
            sparse_point_count=100 + index, mean_reprojection_error=0.5 + index / 10,
            runtime_seconds=2 + index, experiment_id=item.experiment_id,
        )
        for index, item in enumerate(experiments)
    ]
    paths = generate_parameter_charts(tmp_path, results, experiments)
    assert any("max_features_per_image_registration_rate" in path.name for path in paths)
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)


def test_experiment_metadata_round_trip() -> None:
    experiment = ExperimentGenerator().generate(full_config())[0]
    restored = ExperimentConfig.from_dict(experiment.to_dict())
    assert restored == experiment
    assert restored.sweep_id is not None
