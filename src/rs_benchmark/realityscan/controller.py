from __future__ import annotations

import logging
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

LOGGER = logging.getLogger(__name__)
_SUPPORTED_EXECUTABLE_NAMES = {"realityscan.exe", "realitycapture.exe"}


class RealityScanError(RuntimeError):
    """Base exception for RealityScan process control."""


class InvalidExecutableError(RealityScanError):
    """Raised when the configured RealityScan executable is invalid."""


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str


class RealityScanControllerProtocol(Protocol):
    def validate_executable(self) -> None: ...

    def execute(
        self, arguments: Sequence[str], timeout_seconds: float | None = None
    ) -> ProcessResult: ...


class RealityScanController:
    """The only layer allowed to invoke RealityScan subprocesses."""

    def __init__(self, executable: Path) -> None:
        self.executable = Path(executable)

    def validate_executable(self) -> None:
        if not self.executable.is_file():
            raise InvalidExecutableError(f"RealityScan executable not found: {self.executable}")
        if self.executable.name.lower() not in _SUPPORTED_EXECUTABLE_NAMES:
            raise InvalidExecutableError(
                "Executable must be named RealityScan.exe or RealityCapture.exe"
            )

    def execute(
        self, arguments: Sequence[str], timeout_seconds: float | None = None
    ) -> ProcessResult:
        self.validate_executable()
        command = [str(self.executable), *arguments]
        LOGGER.info("Starting RealityScan command with %d arguments", len(arguments))
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            LOGGER.exception("RealityScan command timed out")
            raise RealityScanError("RealityScan command timed out") from exc
        except OSError as exc:
            LOGGER.exception("Unable to start RealityScan")
            raise RealityScanError(f"Unable to start RealityScan: {exc}") from exc
        LOGGER.info("RealityScan exited with code %d", completed.returncode)
        return ProcessResult(
            command=tuple(command),
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
