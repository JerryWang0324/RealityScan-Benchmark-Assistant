from rs_benchmark.gui.time_estimate import ProcessingTimeEstimator, format_duration
from rs_benchmark.services.benchmark_runner import BenchmarkProgress


def progress(current: int, phase: str, total: int = 3) -> BenchmarkProgress:
    return BenchmarkProgress(current, total, "預設", phase)


def test_estimate_uses_finished_wall_time_and_current_elapsed_time() -> None:
    estimator = ProcessingTimeEstimator()
    estimator.reset(3)
    estimator.observe(progress(1, "RUNNING"), 0)
    assert estimator.remaining_seconds(5_000) is None

    estimator.observe(progress(1, "FINISHED"), 20_000)
    assert estimator.remaining_seconds(20_000) == 40

    estimator.observe(progress(2, "RUNNING"), 20_000)
    assert estimator.remaining_seconds(25_000) == 35
    assert estimator.remaining_seconds(40_000) is None

    estimator.observe(progress(2, "FINISHED"), 50_000)
    assert estimator.remaining_seconds(50_000) == 25
    estimator.observe(progress(3, "RUNNING"), 50_000)
    estimator.observe(progress(3, "FINISHED"), 75_000)
    assert estimator.remaining_seconds(75_000) is None


def test_estimate_reset_and_duplicate_finish_do_not_keep_stale_samples() -> None:
    estimator = ProcessingTimeEstimator()
    estimator.reset(3)
    estimator.observe(progress(1, "RUNNING"), 0)
    estimator.observe(progress(1, "FINISHED"), 10_000)
    estimator.observe(progress(1, "FINISHED"), 20_000)
    assert estimator.remaining_seconds(20_000) == 20

    estimator.reset(2)
    assert estimator.remaining_seconds(30_000) is None


def test_estimate_display_rounds_up_and_supports_long_runs() -> None:
    assert format_duration(0.1) == "00:00:01"
    assert format_duration(3_661) == "01:01:01"
