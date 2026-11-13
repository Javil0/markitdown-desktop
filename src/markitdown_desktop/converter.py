"""Conversión de archivos a Markdown con MarkItDown, en segundo plano."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_local = threading.local()


def _markitdown():
    """Una instancia de MarkItDown por hilo (se reutiliza entre conversiones)."""
    md = getattr(_local, "md", None)
    if md is None:
        from markitdown import MarkItDown

        md = MarkItDown(enable_plugins=False)
        _local.md = md
    return md


class ConversionError(Exception):
    """Error legible para mostrar al usuario."""


def convert_file(path: str | Path) -> str:
    """Convierte un archivo a Markdown y devuelve el texto."""
    path = Path(path)
    if not path.exists():
        raise ConversionError(f"El archivo no existe: {path}")
    if path.is_dir():
        raise ConversionError("Es una carpeta, no un archivo")
    try:
        result = _markitdown().convert(str(path))
    except Exception as exc:  # MarkItDown lanza varios tipos distintos
        name = type(exc).__name__
        if name == "UnsupportedFormatException":
            raise ConversionError("Formato no soportado") from exc
        raise ConversionError(f"{name}: {exc}") from exc
    return result.text_content or ""


def markdown_filename(source: str | Path) -> str:
    """'informe.pdf' -> 'informe.md'."""
    return Path(source).stem + ".md"


@dataclass
class Job:
    job_id: int
    path: Path


class _Signals(QObject):
    finished = Signal(int, str)  # job_id, markdown
    failed = Signal(int, str)  # job_id, mensaje de error


class _Task(QRunnable):
    def __init__(self, job: Job, signals: _Signals):
        super().__init__()
        self.job = job
        self.signals = signals

    def run(self):
        try:
            text = convert_file(self.job.path)
        except ConversionError as exc:
            self.signals.failed.emit(self.job.job_id, str(exc))
        except Exception as exc:  # pragma: no cover - red de seguridad
            self.signals.failed.emit(self.job.job_id, f"Error inesperado: {exc}")
        else:
            self.signals.finished.emit(self.job.job_id, text)


class Converter(QObject):
    """Encola conversiones y emite señales en el hilo de la interfaz."""

    finished = Signal(int, str)
    failed = Signal(int, str)

    def __init__(self, parent: QObject | None = None, max_threads: int = 2):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_threads)
        self._signals = _Signals()
        self._signals.finished.connect(self.finished)
        self._signals.failed.connect(self.failed)
        self._next_id = 1

    def submit(self, path: str | Path) -> int:
        job = Job(self._next_id, Path(path))
        self._next_id += 1
        self._pool.start(_Task(job, self._signals))
        return job.job_id

    def wait(self, msecs: int = -1) -> bool:
        return self._pool.waitForDone(msecs)
