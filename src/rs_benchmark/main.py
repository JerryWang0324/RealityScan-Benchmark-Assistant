from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from rs_benchmark.gui.main_window import MainWindow
from rs_benchmark.utils.logging_config import configure_logging


def main() -> int:
    configure_logging()
    logging.getLogger(__name__).info("Starting RealityScan Benchmark Assistant")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

