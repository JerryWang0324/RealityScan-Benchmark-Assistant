from __future__ import annotations

import json
import zipfile
from pathlib import Path

from rs_benchmark import __version__
from rs_benchmark.models import BenchmarkProject
from rs_benchmark.utils.path_sanitizer import PathDisplaySanitizer


def export_reproducibility_package(
    destination: Path, project: BenchmarkProject, root: Path
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    benchmark = PathDisplaySanitizer.sanitize_structure(project.to_dict())
    metadata = PathDisplaySanitizer.sanitize_structure({
        **project.metadata,
        "benchmark_id": project.benchmark_id,
        "app_version": __version__,
    })
    allowed_files = [
        (root / "summary" / "benchmark_summary.json", "benchmark_summary.json"),
        (root / "summary" / "results.csv", "results.csv"),
        (root / "summary" / "analysis.json", "analysis.json"),
        (root / "summary" / "report.html", "report.html"),
    ]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("benchmark.json", json.dumps(benchmark, indent=2, ensure_ascii=False))
        archive.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
        for source, target in allowed_files:
            if source.is_file():
                archive.write(source, target)
        for folder_name in ("charts", "sweeps"):
            folder = (
                root / "summary" / folder_name
                if folder_name == "charts" else root / folder_name
            )
            if folder.is_dir():
                for source in folder.rglob("*"):
                    if source.is_file():
                        target = f"{folder_name}/{source.relative_to(folder).as_posix()}"
                        archive.write(source, target)
        for config in sorted((root / "experiments").glob("*/config.json")):
            try:
                payload = json.loads(config.read_text(encoding="utf-8"))
                payload = PathDisplaySanitizer.sanitize_structure(payload)
                archive.writestr(
                    f"experiment_configs/{config.parent.name}.json",
                    json.dumps(payload, indent=2, ensure_ascii=False),
                )
            except (OSError, ValueError, TypeError):
                continue
    return destination
