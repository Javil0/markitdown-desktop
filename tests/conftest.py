import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def sample_html(tmp_path):
    p = tmp_path / "informe.html"
    p.write_text("<html><body><h1>Hola</h1><p>Texto de <b>prueba</b>.</p></body></html>", encoding="utf-8")
    return p


@pytest.fixture
def sample_docx(tmp_path):
    from docx import Document

    doc = Document()
    doc.add_heading("Informe trimestral", level=1)
    doc.add_paragraph("Ventas al alza.")
    p = tmp_path / "trimestre.docx"
    doc.save(p)
    return p


@pytest.fixture(autouse=True)
def answer_dialogs(monkeypatch):
    """Simula la respuesta al diálogo de 'sin guardar' para que nunca bloquee.

    Los tests cambian `answer_dialogs.discard` y leen `answer_dialogs.shown`.
    """
    from PySide6.QtWidgets import QMessageBox

    class Answer:
        discard = True
        shown = 0

    state = Answer()

    def fake_exec(box):
        state.shown += 1
        wanted = QMessageBox.ButtonRole.DestructiveRole if state.discard else QMessageBox.ButtonRole.RejectRole
        button = next(b for b in box.buttons() if box.buttonRole(b) == wanted)
        monkeypatch.setattr(box, "clickedButton", lambda: button)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    return state
