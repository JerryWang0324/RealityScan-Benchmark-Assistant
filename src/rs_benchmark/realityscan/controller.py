from __future__ import annotations

import logging
import subprocess
import time
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
    return_code: int | None
    stdout: str
    stderr: str
    runtime_seconds: float
    timed_out: bool = False


class RealityScanControllerProtocol(Protocol):
    def validate_executable(self) -> None: ...

    def get_version(self) -> str | None: ...

    def run_command(
        self, arguments: Sequence[str], timeout_seconds: float | None = None
    ) -> ProcessResult: ...

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

    def get_version(self) -> str | None:
        """Read Windows file-version metadata; RealityScan has no documented version command."""
        self.validate_executable()
        try:
            import ctypes
            from ctypes import wintypes

            size = ctypes.windll.version.GetFileVersionInfoSizeW(str(self.executable), None)
            if not size:
                return None
            buffer = ctypes.create_string_buffer(size)
            if not ctypes.windll.version.GetFileVersionInfoW(
                str(self.executable), 0, size, buffer
            ):
                return None
            pointer = ctypes.c_void_p()
            length = wintypes.UINT()
            if not ctypes.windll.version.VerQueryValueW(
                buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)
            ):
                return None

            class FixedFileInfo(ctypes.Structure):
                _fields_ = [
                    ("signature", wintypes.DWORD), ("struct_version", wintypes.DWORD),
                    ("file_version_ms", wintypes.DWORD), ("file_version_ls", wintypes.DWORD),
                ]

            info = ctypes.cast(pointer, ctypes.POINTER(FixedFileInfo)).contents
            return ".".join(str(value) for value in (
                info.file_version_ms >> 16, info.file_version_ms & 0xFFFF,
                info.file_version_ls >> 16, info.file_version_ls & 0xFFFF,
            ))
        except (AttributeError, OSError, ValueError):
            LOGGER.debug("RealityScan version metadata is unavailable", exc_info=True)
            return None

    def run_command(
        self, arguments: Sequence[str], timeout_seconds: float | None = None
    ) -> ProcessResult:
        self.validate_executable()
        command = [str(self.executable), *arguments]
        LOGGER.info("Starting RealityScan command with %d arguments", len(arguments))
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False,
                timeout=timeout_seconds, shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            runtime = time.perf_counter() - started
            LOGGER.warning("RealityScan command timed out after %.3f seconds", runtime)
            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout
            )
            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            )
            return ProcessResult(
                command=tuple(command), return_code=None, stdout=stdout or "",
                stderr=stderr or "", runtime_seconds=runtime, timed_out=True,
            )
        except OSError as exc:
            LOGGER.exception("Unable to start RealityScan")
            raise RealityScanError(f"Unable to start RealityScan: {exc}") from exc
        runtime = time.perf_counter() - started
        LOGGER.info("RealityScan exited with code %d", completed.returncode)
        return ProcessResult(
            command=tuple(command), return_code=completed.returncode,
            stdout=completed.stdout or "", stderr=completed.stderr or "",
            runtime_seconds=runtime,
        )

    def execute(
        self, arguments: Sequence[str], timeout_seconds: float | None = None
    ) -> ProcessResult:
        return self.run_command(arguments, timeout_seconds)
