from pathlib import Path

import pytest

from rs_benchmark.realityscan.dataset import validate_dataset


def test_valid_dataset_counts_supported_extensions_case_insensitively(tmp_path: Path) -> None:
    for name in ("a.jpg", "b.JPEG", "c.png", "d.tif", "e.TIFF"):
        (tmp_path / name).touch()
    (tmp_path / "notes.txt").touch()

    assert validate_dataset(tmp_path).total_images == 5


def test_missing_dataset_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        validate_dataset(tmp_path / "missing")


def test_empty_or_unsupported_dataset_fails(tmp_path: Path) -> None:
    (tmp_path / "video.mp4").touch()
    with pytest.raises(ValueError, match="No supported images"):
        validate_dataset(tmp_path)
