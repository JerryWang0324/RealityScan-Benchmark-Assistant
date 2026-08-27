from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def config_file() -> Path:
    return project_root() / "config" / "app_settings.json"


def log_directory() -> Path:
    return project_root() / "logs"


def benchmark_runs_directory() -> Path:
    return project_root() / "benchmark_runs"
