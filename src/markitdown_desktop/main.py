"""Punto de entrada de la aplicación."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from . import __version__
from .window import MainWindow


class App(QApplication):
    """Recoge archivos soltados sobre el icono del Dock o abiertos con 'Abrir con'."""

    def __init__(self, argv):
        super().__init__(argv)
        self.window: MainWindow | None = None
        self._pending: list[Path] = []

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            path = Path(event.file())
            if self.window is not None:
                self.window.add_files([path])
            else:
                self._pending.append(path)
            return True
        return super().event(event)


def _selftest(path: str) -> int:
    """Convierte un archivo sin abrir ventana (lo usa la CI para probar la app empaquetada)."""
    from .converter import ConversionError, convert_file

    try:
        sys.stdout.write(convert_file(path))
    except ConversionError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        return _selftest(sys.argv[2])

    app = App(sys.argv)
    app.setApplicationName("MarkItDown")
    app.setOrganizationName("markitdown-desktop")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    app.window = window
    window.show()

    initial = [Path(a) for a in sys.argv[1:] if not a.startswith("-") and Path(a).exists()]
    initial += app._pending
    if initial:
        window.add_files(initial)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
