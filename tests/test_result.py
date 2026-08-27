import pytest

from rs_benchmark.models import ExperimentResult, ExperimentStatus


def test_experiment_result_round_trip_and_registration_rate() -> None:
    result = ExperimentResult(
        experiment_name="Default",
        status=ExperimentStatus.SUCCEEDED,
        total_images=100,
        registered_images=92,
        alignment_runtime_seconds=12.5,
    )

    restored = ExperimentResult.from_dict(result.to_dict())

    assert restored == result
    assert restored.registration_rate == pytest.approx(0.92)


def test_registration_rate_is_none_without_total_images() -> None:
    assert ExperimentResult(experiment_name="Empty").registration_rate is None

