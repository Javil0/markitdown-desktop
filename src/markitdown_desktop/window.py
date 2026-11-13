"""Ventana principal: panel de archivos a la izquierda, Markdown a la derecha."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .converter import Converter, markdown_filename
from .drop_zone import STATUS_DONE, STATUS_ERROR, DropPanel
from .preview import PreviewPanel

STYLE = """
#DropArea {
    border: 2px dashed palette(mid);
    border-radius: 14px;
    background: palette(base);
}
#DropArea[hover="true"] {
    border-color: palette(highlight);
    background: palette(alternate-base);
}
#DropIcon { font-size: 40px; color: palette(mid); }
#SectionTitle { font-weight: 600; color: palette(placeholder-text); margin-top: 6px; }
#FileList { border-radius: 8px; }
#PreviewTitle { font-size: 15px; font-weight: 600; }
#PreviewMessage { color: palette(placeholder-text); font-size: 15px; }
#DragHandle {
    border: 1px solid palette(mid);
    border-radius: 8px;
    padding: 10px;
    background: palette(alternate-base);
}
#DragHandle:hover { border-color: palette(highlight); }
"""


@dataclass
class JobState:
    path: Path
    markdown: str | None = None
    error: str | None = None


def unique_path(path: Path) -> Path:
    """Si 'x.md' existe, devuelve 'x (1).md', 'x (2).md'…"""
    if not path.exists():
        return path
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings or QSettings()
        self.jobs: dict[int, JobState] = {}
        self.current_job = 0

        self.setWindowTitle("MarkItDown")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE)

        self.converter = Converter(self)
        self.converter.finished.connect(self._on_finished)
        self.converter.failed.connect(self._on_failed)

        self.drop_panel = DropPanel()
        self.preview = PreviewPanel()

        self.auto_save = QCheckBox("Guardar también el .md junto al archivo original")
        self.auto_save.setChecked(self.settings.value("auto_save", False, type=bool))
        self.auto_save.toggled.connect(lambda v: self.settings.setValue("auto_save", v))

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 6, 12)
        left_layout.addWidget(self.drop_panel, 1)
        left_layout.addWidget(self.auto_save)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 12, 12, 12)
        right_layout.addWidget(self.preview)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([420, 680])
        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

        self.drop_panel.files_dropped.connect(self.add_files)
        self.drop_panel.job_selected.connect(self.show_job)
        self.preview.copy_requested.connect(self.copy_current)
        self.preview.save_requested.connect(self.save_current)
        self.preview.text_edited.connect(self._on_text_edited)

        self._build_menu()

    # --- menú -----------------------------------------------------------
    def _build_menu(self):
        menu = self.menuBar().addMenu("Archivo")
        open_action = QAction("Abrir…", self, shortcut=QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_dialog)
        save_action = QAction("Guardar Markdown como…", self, shortcut=QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_current)
        copy_action = QAction("Copiar Markdown", self, shortcut=QKeySequence("Ctrl+Shift+C"))
        copy_action.triggered.connect(self.copy_current)
        clear_action = QAction("Vaciar lista", self)
        clear_action.triggered.connect(self.clear)
        for action in (open_action, save_action, copy_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(clear_action)

    def open_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Elige archivos para convertir")
        if files:
            self.add_files([Path(f) for f in files])

    # --- conversión -----------------------------------------------------
    def add_files(self, paths: list[Path]):
        last_id = 0
        for path in paths:
            job_id = self.converter.submit(path)
            self.jobs[job_id] = JobState(path=Path(path))
            self.drop_panel.add_job(job_id, Path(path))
            last_id = job_id
        if last_id:
            self.drop_panel.select(last_id)
            n = len(paths)
            self.statusBar().showMessage(f"Convirtiendo {n} archivo{'s' if n != 1 else ''}…")

    def _on_finished(self, job_id: int, markdown: str):
        job = self.jobs.get(job_id)
        if job is None:
            return
        job.markdown = markdown
        self.drop_panel.set_status(job_id, STATUS_DONE)
        message = f"Convertido: {job.path.name}"
        if self.auto_save.isChecked():
            try:
                target = unique_path(job.path.with_name(markdown_filename(job.path)))
                target.write_text(markdown, encoding="utf-8")
                message += f" → guardado en {target}"
            except OSError as exc:
                message += f" (no se pudo guardar junto al original: {exc})"
        self.statusBar().showMessage(message, 6000)
        if job_id == self.current_job:
            self.show_job(job_id)

    def _on_failed(self, job_id: int, error: str):
        job = self.jobs.get(job_id)
        if job is None:
            return
        job.error = error
        self.drop_panel.set_status(job_id, STATUS_ERROR, error)
        self.statusBar().showMessage(f"No se pudo convertir {job.path.name}", 6000)
        if job_id == self.current_job:
            self.show_job(job_id)

    def _on_text_edited(self, text: str):
        job = self.jobs.get(self.current_job)
        if job is not None and job.markdown is not None:
            job.markdown = text

    # --- vista ----------------------------------------------------------
    def show_job(self, job_id: int):
        self.current_job = job_id
        job = self.jobs.get(job_id)
        if job is None:
            self.preview.show_message("El Markdown aparecerá aquí")
        elif job.error:
            self.preview.show_message(f"⚠️ No se pudo convertir “{job.path.name}”\n\n{job.error}")
        elif job.markdown is None:
            self.preview.show_message(f"Convirtiendo “{job.path.name}”…")
        else:
            self.preview.show_markdown(markdown_filename(job.path), job.markdown)

    def copy_current(self):
        if self.preview.has_document():
            self.preview.copy_to_clipboard()
            self.statusBar().showMessage("Markdown copiado al portapapeles", 3000)

    def save_current(self):
        job = self.jobs.get(self.current_job)
        if job is None or job.markdown is None:
            return
        start_dir = self.settings.value("last_save_dir", str(job.path.parent))
        default = str(Path(start_dir) / markdown_filename(job.path))
        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar Markdown", default, "Markdown (*.md);;Todos los archivos (*)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix == "":
            target = target.with_suffix(".md")
        try:
            target.write_text(self.preview.text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))
            return
        self.settings.setValue("last_save_dir", str(target.parent))
        self.statusBar().showMessage(f"Guardado en {target}", 5000)

    def clear(self):
        self.jobs.clear()
        self.drop_panel.list.clear()
        self.show_job(0)
