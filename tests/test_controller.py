import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from rs_benchmark.realityscan.controller import InvalidExecutableError, RealityScanController


def _controller(tmp_path: Path) -> RealityScanController:
    executable = tmp_path / "RealityScan.exe"
    executable.touch()
    return RealityScanController(executable)


def test_invalid_executable_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidExecutableError, match="not found"):
        RealityScanController(tmp_path / "RealityScan.exe").validate_executable()


def test_success_and_nonzero_exit_are_results(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    with patch("subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "out", "")
        success = controller.run_command(["-quit"])
        run.return_value = subprocess.CompletedProcess([], 7, "", "problem")
        failure = controller.run_command(["-quit"])

    assert success.return_code == 0
    assert success.stdout == "out"
    assert failure.return_code == 7
    assert failure.stderr == "problem"
    assert run.call_args.kwargs["shell"] is False
    assert run.call_args.kwargs["encoding"] == "utf-8"
    assert run.call_args.kwargs["errors"] == "replace"


def test_timeout_is_captured_not_raised(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rs", 1)):
        result = controller.run_command(["-align"], timeout_seconds=1)

    assert result.timed_out is True
    assert result.return_code is None
