from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    folder: Path
    image_files: tuple[Path, ...]

    @property
    def total_images(self) -> int:
        return len(self.image_files)


def validate_dataset(folder: Path) -> DatasetInfo:
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Image folder does not exist: {folder}")
    images = tuple(
        sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )
    )
    if not images:
        raise ValueError(f"No supported images found in: {folder}")
    return DatasetInfo(folder=folder, image_files=images)
