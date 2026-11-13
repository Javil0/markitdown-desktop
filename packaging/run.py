"""Punto de entrada para PyInstaller."""

import multiprocessing
import sys

from markitdown_desktop.main import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
