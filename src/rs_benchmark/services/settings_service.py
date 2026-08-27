from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from rs_benchmark.utils.paths import config_file

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AppSettings:
    realityscan_executable: str = ""
    last_image_folder: str = ""


class SettingsService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_file()

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AppSettings(**data)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            LOGGER.warning("Unable to load settings from %s: %s", self.path, exc)
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")

