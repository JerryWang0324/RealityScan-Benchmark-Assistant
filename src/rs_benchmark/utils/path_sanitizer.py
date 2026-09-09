from __future__ import annotations

import re
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any


class PathDisplaySanitizer:
    """Remove private parent directories from public artifacts."""

    _windows_absolute = re.compile(r"^[A-Za-z]:[\\/]")
    _windows_user_prefix = re.compile(
        r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/]Users[\\/][^\\/\r\n]+"
    )
    _posix_user_prefix = re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\r\n]+")

    @classmethod
    def sanitize(cls, value: str | Path | None, *, label: str = "dataset") -> str | None:
        if value is None:
            return None
        text = str(value)
        if not text:
            return text
        if cls._windows_absolute.match(text):
            name = PureWindowsPath(text).name
            return f"<{label}>/{name}" if name else f"<{label}>"
        path = PurePath(text)
        if path.is_absolute():
            return f"<{label}>/{path.name}" if path.name else f"<{label}>"
        return text.replace("\\", "/")

    @classmethod
    def sanitize_structure(cls, value: Any, *, key: str = "") -> Any:
        if isinstance(value, dict):
            return {
                item_key: cls.sanitize_structure(item, key=str(item_key))
                for item_key, item in value.items()
            }
        if isinstance(value, list):
            return [cls.sanitize_structure(item, key=key) for item in value]
        if isinstance(value, str):
            label = (
                "executable" if "executable" in key
                else "dataset" if "image" in key
                else "path"
            )
            if cls._windows_absolute.match(value) or value.startswith("/"):
                return cls.sanitize(value, label=label)
            # Error messages and free-form metadata may contain a path without being
            # path fields themselves. Redact the private account prefix while keeping
            # the surrounding diagnostic text useful.
            value = cls._windows_user_prefix.sub("<user>", value)
            return cls._posix_user_prefix.sub("<user>", value)
        return value
