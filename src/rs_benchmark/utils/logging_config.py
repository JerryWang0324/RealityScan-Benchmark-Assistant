from __future__ import annotations

import logging
from pathlib import Path

from .paths import log_directory


def configure_logging(directory: Path | None = None) -> Path:
    target_directory = directory or log_directory()
    target_directory.mkdir(parents=True, exist_ok=True)
    log_file = target_directory / "app.log"
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    return log_file
