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
