"""Panel izquierdo: zona para soltar archivos y lista de archivos convertidos."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_ERROR = "error"

_STATUS_PREFIX = {
    STATUS_PENDING: "⏳",
    STATUS_DONE: "✅",
    STATUS_ERROR: "⚠️",
}

ROLE_JOB_ID = Qt.ItemDataRole.UserRole


def paths_from_mime(mime) -> list[Path]:
    """Extrae rutas locales de un drop; las carpetas se expanden (sin ocultos)."""
    paths: list[Path] = []
    for url in mime.urls():
        if not url.isLocalFile():
            continue
        p = Path(url.toLocalFile())
        if p.is_dir():
            paths.extend(
                sorted(
                    f
                    for f in p.rglob("*")
                    if f.is_file() and not any(part.startswith(".") for part in f.relative_to(p).parts)
                )
            )
        elif p.is_file():
            paths.append(p)
    return paths


class DropArea(QFrame):
    """Recuadro donde se sueltan archivos; también se puede hacer clic."""

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        icon = QLabel("⬇︎")
        icon.setObjectName("DropIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel(
            "<b>Arrastra aquí tus archivos</b><br>"
            "PDF, Word, PowerPoint, Excel, HTML, imágenes, audio…<br>"
            "<span style='color:gray'>o haz clic para elegirlos</span>"
        )
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        layout.addStretch(1)
        layout.addWidget(icon)
        layout.addWidget(text)
        layout.addStretch(1)
        self._set_hover(False)

    def _set_hover(self, hover: bool):
        self.setProperty("hover", hover)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_hover(False)

    def dropEvent(self, event):
        self._set_hover(False)
        paths = paths_from_mime(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.files_dropped.emit(paths)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(self, "Elige archivos para convertir")
            if files:
                self.files_dropped.emit([Path(f) for f in files])
        super().mouseReleaseEvent(event)


class DropPanel(QWidget):
    """Zona de soltar + lista de archivos con su estado."""

    files_dropped = Signal(list)
    job_selected = Signal(int)  # job_id (0 = ninguno)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.drop_area = DropArea(self)
        self.list = QListWidget(self)
        self.list.setObjectName("FileList")
        self.list.setAlternatingRowColors(False)
        hint = QLabel("Archivos")
        hint.setObjectName("SectionTitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.drop_area, 3)
        layout.addWidget(hint)
        layout.addWidget(self.list, 2)

        self.drop_area.files_dropped.connect(self.files_dropped)
        self.list.currentItemChanged.connect(self._on_current_changed)

        # Soltar también encima de la lista
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.drop_area.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        self.drop_area.dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self.drop_area.dragLeaveEvent(event)

    def dropEvent(self, event):
        self.drop_area.dropEvent(event)

    def _on_current_changed(self, current: QListWidgetItem | None, _previous):
        self.job_selected.emit(current.data(ROLE_JOB_ID) if current else 0)

    def _find(self, job_id: int) -> QListWidgetItem | None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(ROLE_JOB_ID) == job_id:
                return item
        return None

    def add_job(self, job_id: int, path: Path):
        item = QListWidgetItem()
        item.setData(ROLE_JOB_ID, job_id)
        item.setData(Qt.ItemDataRole.UserRole + 1, path.name)
        item.setToolTip(str(path))
        self.list.addItem(item)
        self.set_status(job_id, STATUS_PENDING)
        if self.list.currentItem() is None:
            self.list.setCurrentItem(item)

    def set_status(self, job_id: int, status: str, detail: str = ""):
        item = self._find(job_id)
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole + 1)
        item.setText(f"{_STATUS_PREFIX[status]}  {name}")
        if detail:
            item.setToolTip(f"{item.toolTip().splitlines()[0]}\n{detail}")

    def select(self, job_id: int):
        item = self._find(job_id)
        if item is not None:
            self.list.setCurrentItem(item)
