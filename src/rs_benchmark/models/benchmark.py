from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .experiment import ExperimentConfig

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})


@dataclass(slots=True)
class BenchmarkProject:
    name: str
    image_folder: Path
    experiments: list[ExperimentConfig] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def image_files(self) -> list[Path]:
        if not self.image_folder.is_dir():
            raise FileNotFoundError(f"Image folder does not exist: {self.image_folder}")
        return sorted(
            path
            for path in self.image_folder.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Benchmark name cannot be empty")
        if not self.image_files():
            raise ValueError(f"No supported images found in: {self.image_folder}")
        if not self.experiments:
            raise ValueError("At least one experiment is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "image_folder": str(self.image_folder),
            "image_count": len(self.image_files()),
            "created_at": self.created_at.isoformat(),
            "experiments": [experiment.to_dict() for experiment in self.experiments],
        }

    def create_run_directory(self, runs_root: Path) -> Path:
        """Create the reproducibility folder skeleton for a benchmark run."""
        self.validate()
        safe_name = "_".join(self.name.lower().split())
        run_directory = runs_root / f"{self.created_at:%Y-%m-%d_%H%M%S}_{safe_name}"
        run_directory.mkdir(parents=True, exist_ok=False)
        for index, experiment in enumerate(self.experiments, start=1):
            experiment_name = "_".join(experiment.name.lower().split())
            experiment_directory = run_directory / f"experiment_{index:03d}_{experiment_name}"
            (experiment_directory / "realityscan_output").mkdir(parents=True)
            (experiment_directory / "config.json").write_text(
                json.dumps(experiment.to_dict(), indent=2), encoding="utf-8"
            )
        (run_directory / "summary" / "charts").mkdir(parents=True)
        (run_directory / "benchmark.json").write_text(
            json.dumps(self.to_dict(), indent=2), encoding="utf-8"
        )
        return run_directory
