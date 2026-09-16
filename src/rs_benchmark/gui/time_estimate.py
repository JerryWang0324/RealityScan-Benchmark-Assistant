from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from rs_benchmark.services.benchmark_runner import BenchmarkProgress


def format_duration(seconds: float) -> str:
    """Format an estimate as hours, minutes, and seconds without rounding down."""
    hours, remainder = divmod(ceil(max(0, seconds)), 3_600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@dataclass(slots=True)
class ProcessingTimeEstimator:
    """Estimate queue time from completed experiments' observed wall time."""

    total: int = 0
    completed: int = 0
    completed_seconds: float = 0.0
    current_started_ms: int | None = None

    def reset(self, total: int) -> None:
        self.total = total
        self.completed = 0
        self.completed_seconds = 0.0
        self.current_started_ms = None

    def observe(self, progress: BenchmarkProgress, now_ms: int) -> None:
        if progress.phase == "RUNNING":
            if progress.current > self.completed and self.current_started_ms is None:
                self.current_started_ms = now_ms
        elif progress.phase == "FINISHED" and progress.current > self.completed:
            if self.current_started_ms is not None:
                self.completed_seconds += max(0, now_ms - self.current_started_ms) / 1_000
            self.completed = progress.current
            self.current_started_ms = None

    def remaining_seconds(self, now_ms: int) -> float | None:
        if self.completed == 0 or self.completed_seconds <= 0 or self.completed >= self.total:
            return None
        average = self.completed_seconds / self.completed
        if self.current_started_ms is not None:
            current_elapsed = max(0, now_ms - self.current_started_ms) / 1_000
            if current_elapsed >= average:
                return None
            return average * (self.total - self.completed) - current_elapsed
        return average * (self.total - self.completed)
