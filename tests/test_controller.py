from pathlib import Path

import pytest

from rs_benchmark.realityscan.controller import InvalidExecutableError, RealityScanController


def test_invalid_executable_is_rejected(tmp_path: Path) -> None:
    controller = RealityScanController(tmp_path / "RealityScan.exe")

    with pytest.raises(InvalidExecutableError, match="not found"):
        controller.validate_executable()


def test_wrong_executable_name_is_rejected(tmp_path: Path) -> None:
    executable = tmp_path / "other.exe"
    executable.touch()

    with pytest.raises(InvalidExecutableError, match="must be named"):
        RealityScanController(executable).validate_executable()
