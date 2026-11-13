"""Panel derecho: vista del Markdown y formas de sacarlo de la app."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDrag, QFontDatabase, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

_drag_dir: Path | None = None


def drag_temp_dir() -> Path:
    """Carpeta temporal donde se escriben los .md antes de arrastrarlos."""
    global _drag_dir
    if _drag_dir is None:
        _drag_dir = Path(tempfile.mkdtemp(prefix="markitdown-desktop-"))
    return _drag_dir


def write_temp_markdown(filename: str, text: str) -> Path:
    """Escribe el .md en una subcarpeta propia para no pisar otros con el mismo nombre."""
    folder = Path(tempfile.mkdtemp(dir=drag_temp_dir()))
    target = folder / filename
    target.write_text(text, encoding="utf-8")
    return target


class DragHandle(QLabel):
    """Icono que se arrastra al Finder para soltar el .md en una carpeta."""

    def __init__(self, provider, parent: QWidget | None = None):
        super().__init__(parent)
        self._provider = provider  # callable -> (filename, text) | None
        self._press_pos: QPoint | None = None
        self.setObjectName("DragHandle")
        self.setText("📄  Arrastra el .md a una carpeta")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Arrastra este icono al Finder, al escritorio o a otra app")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        distance = (event.position().toPoint() - self._press_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            return
        self._press_pos = None
        self.start_drag()

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def build_mime(self) -> QMimeData | None:
        data = self._provider()
        if data is None:
            return None
        filename, text = data
        path = write_temp_markdown(filename, text)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path))])
        mime.setText(text)  # para soltar en editores de texto
        return mime

    def start_drag(self):
        mime = self.build_mime()
        if mime is None:
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.CopyAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class PreviewPanel(QWidget):
    copy_requested = Signal()
    save_requested = Signal()
    text_edited = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._filename = ""
        self._loading = False

        self.title = QLabel("")
        self.title.setObjectName("PreviewTitle")
        self.copy_button = QPushButton("Copiar")
        self.save_button = QPushButton("Guardar como…")
        self.save_button.setDefault(True)
        self.copy_button.clicked.connect(self.copy_requested)
        self.save_button.clicked.connect(self.save_requested)

        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.copy_button)
        header.addWidget(self.save_button)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.textChanged.connect(self._on_text_changed)
        self.rendered = QTextBrowser()
        self.rendered.setOpenExternalLinks(True)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.editor, "Markdown")
        self.tabs.addTab(self.rendered, "Vista renderizada")
        self.tabs.currentChanged.connect(self._refresh_render)

        self.drag_handle = DragHandle(self.current_document)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addLayout(header)
        content_layout.addWidget(self.tabs, 1)
        content_layout.addWidget(self.drag_handle)

        self.message = QLabel()
        self.message.setObjectName("PreviewMessage")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.message)
        self.stack.addWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.show_message("El Markdown aparecerá aquí")

    # --- estado -------------------------------------------------------
    def show_message(self, text: str):
        self._filename = ""
        self.message.setText(text)
        self.stack.setCurrentIndex(0)

    def show_markdown(self, filename: str, text: str):
        self._filename = filename
        self.title.setText(filename)
        self._loading = True
        self.editor.setPlainText(text)
        self._loading = False
        self._refresh_render()
        self.stack.setCurrentIndex(1)

    def has_document(self) -> bool:
        return bool(self._filename)

    def filename(self) -> str:
        return self._filename

    def text(self) -> str:
        return self.editor.toPlainText()

    def current_document(self) -> tuple[str, str] | None:
        if not self.has_document():
            return None
        return self._filename, self.text()

    # --- internos -----------------------------------------------------
    def _on_text_changed(self):
        if not self._loading:
            self.text_edited.emit(self.text())
            if self.tabs.currentIndex() == 1:
                self._refresh_render()

    def _refresh_render(self, *_):
        if self.tabs.currentIndex() == 1:
            self.rendered.setMarkdown(self.text())

    def copy_to_clipboard(self):
        QGuiApplication.clipboard().setText(self.text())
