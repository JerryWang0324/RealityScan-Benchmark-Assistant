import pytest

from rs_benchmark.models import ExperimentConfig


def test_experiment_config_round_trip() -> None:
    config = ExperimentConfig(
        name="High Features",
        feature_detection_quality="Normal",
        max_features_per_image=80_000,
        image_overlap="High",
        max_feature_reprojection_error=1.5,
    )

    assert ExperimentConfig.from_dict(config.to_dict()) == config


def test_experiment_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="positive"):
        ExperimentConfig(name="Invalid", max_features_per_image=0)
