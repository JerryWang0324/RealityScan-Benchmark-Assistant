from __future__ import annotations

import hashlib
import json
import platform
import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from rs_benchmark.realityscan.dataset import SUPPORTED_IMAGE_EXTENSIONS

from .experiment import ExperimentConfig
from .result import ExperimentResult


class BenchmarkStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class BenchmarkProject:
    name: str
    image_folder: Path
    experiments: list[ExperimentConfig] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    realityscan_executable: Path = Path()
    output_directory: Path = Path("benchmark_runs")
    results: list[ExperimentResult] = field(default_factory=list)
    benchmark_id: str = field(default_factory=lambda: uuid4().hex)
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    notes: str = ""
    stop_on_failure: bool = False
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    run_directory: Path | None = None

    def image_files(self) -> list[Path]:
        if not self.image_folder.is_dir():
            raise FileNotFoundError(f"Image folder does not exist: {self.image_folder}")
        return sorted(
            path for path in self.image_folder.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )

    @property
    def enabled_experiments(self) -> list[ExperimentConfig]:
        return [experiment for experiment in self.experiments if experiment.enabled]

    def validate(self, *, require_executable: bool = False) -> list[str]:
        if not self.name.strip():
            raise ValueError("Benchmark name cannot be empty")
        if not self.image_files():
            raise ValueError(f"No supported images found in: {self.image_folder}")
        if not self.experiments:
            raise ValueError("At least one experiment is required")
        if not self.enabled_experiments:
            raise ValueError("At least one enabled experiment is required")
        if require_executable and not self.realityscan_executable.is_file():
            raise FileNotFoundError(
                f"RealityScan executable not found: {self.realityscan_executable}"
            )

        warnings: list[str] = []
        signatures: dict[tuple[object, ...], str] = {}
        for experiment in self.enabled_experiments:
            signature = experiment.parameter_signature
            if signature in signatures:
                warnings.append(
                    f'Experiments "{signatures[signature]}" and "{experiment.name}" '
                    "use identical parameters."
                )
            else:
                signatures[signature] = experiment.name
        return warnings

    def experiment_config(
        self, experiment: ExperimentConfig, output_directory: Path
    ) -> ExperimentConfig:
        """Apply the project-wide dataset/executable without mutating the saved row."""
        return replace(
            experiment,
            image_folder=self.image_folder,
            realityscan_executable=self.realityscan_executable,
            output_directory=output_directory,
            dry_run=self.dry_run,
        )

    def collect_metadata(self, realityscan_version: str | None = None) -> dict[str, Any]:
        images = self.image_files()
        digest = hashlib.sha256()
        for image in images:
            stat = image.stat()
            relative = image.relative_to(self.image_folder).as_posix()
            digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
        self.metadata.update({
            "operating_system": platform.platform(),
            "python_version": platform.python_version(),
            "realityscan_version": realityscan_version,
            "app_version": _app_version(),
            "dataset_image_count": len(images),
            "dataset_fingerprint": f"sha256:{digest.hexdigest()}",
            "cache_policy": "isolated_process_temp_per_experiment",
            "start_time": self.started_at.isoformat() if self.started_at else None,
        })
        return self.metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "image_folder": str(self.image_folder),
            "realityscan_executable": str(self.realityscan_executable),
            "output_directory": str(self.output_directory),
            "experiments": [_project_experiment_dict(item) for item in self.experiments],
            "results": [result.to_dict() for result in self.results],
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "notes": self.notes,
            "stop_on_failure": self.stop_on_failure,
            "dry_run": self.dry_run,
            "metadata": self.metadata,
            "run_directory": str(self.run_directory) if self.run_directory else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkProject:
        def parsed_time(value: str | None) -> datetime | None:
            return datetime.fromisoformat(value) if value else None

        return cls(
            benchmark_id=data.get("benchmark_id", uuid4().hex),
            name=data["name"],
            created_at=parsed_time(data.get("created_at")) or datetime.now().astimezone(),
            image_folder=Path(data["image_folder"]),
            realityscan_executable=Path(data.get("realityscan_executable", "")),
            output_directory=Path(data.get("output_directory", "benchmark_runs")),
            experiments=[ExperimentConfig.from_dict(item) for item in data.get("experiments", [])],
            results=[ExperimentResult.from_dict(item) for item in data.get("results", [])],
            status=BenchmarkStatus(data.get("status", BenchmarkStatus.PENDING)),
            started_at=parsed_time(data.get("started_at")),
            finished_at=parsed_time(data.get("finished_at")),
            notes=data.get("notes", ""),
            stop_on_failure=bool(data.get("stop_on_failure", False)),
            dry_run=bool(data.get("dry_run", False)),
            metadata=dict(data.get("metadata", {})),
            run_directory=Path(data["run_directory"]) if data.get("run_directory") else None,
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> BenchmarkProject:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def create_run_directory(self, runs_root: Path | None = None) -> Path:
        self.validate()
        root = runs_root or self.output_directory
        base = root / f"{self.created_at:%Y-%m-%d_%H%M%S}_{_slug(self.name)}"
        candidate = base
        suffix = 1
        while candidate.exists():
            candidate = Path(f"{base}_{suffix:02d}")
            suffix += 1
        (candidate / "summary" / "charts").mkdir(parents=True)
        experiments_root = candidate / "experiments"
        experiments_root.mkdir()
        for index, experiment in enumerate(self.enabled_experiments, start=1):
            directory = experiments_root / f"{index:03d}_{experiment.experiment_id}"
            (directory / "realityscan_output").mkdir(parents=True)
            (directory / "config.json").write_text(
                json.dumps(experiment.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            # Preserve the Phase 2 public helper's legacy path for compatibility.
            legacy = candidate / f"experiment_{index:03d}_{_slug(experiment.name)}"
            (legacy / "realityscan_output").mkdir(parents=True)
            (legacy / "config.json").write_text(
                json.dumps(experiment.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
        self.run_directory = candidate
        self.save(candidate / "benchmark.json")
        return candidate


def slug(value: str) -> str:
    return _slug(value)


def _slug(value: str) -> str:
    return re.sub(r"[^\w-]+", "_", value.strip().lower()).strip("_") or "benchmark"


def _project_experiment_dict(experiment: ExperimentConfig) -> dict[str, Any]:
    data = experiment.to_dict()
    for shared_field in (
        "image_folder", "realityscan_executable", "output_directory", "dry_run"
    ):
        data.pop(shared_field, None)
    return data


def _app_version() -> str | None:
    try:
        from rs_benchmark import __version__

        return __version__
    except Exception:
        return None
