from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QFileDialog

from markitdown_desktop.drop_zone import paths_from_mime
from markitdown_desktop.window import MainWindow, unique_path


def make_window(qtbot, settings):
    w = MainWindow(settings)
    qtbot.addWidget(w)
    return w


def wait_done(qtbot, w):
    qtbot.waitUntil(lambda: all(j.markdown is not None or j.error for j in w.jobs.values()), timeout=20000)


def test_drop_shows_markdown(qtbot, settings, sample_html):
    w = make_window(qtbot, settings)
    w.drop_panel.files_dropped.emit([sample_html])
    wait_done(qtbot, w)
    assert w.preview.has_document()
    assert w.preview.filename() == "informe.md"
    assert "# Hola" in w.preview.text()
    assert w.drop_panel.list.item(0).text().startswith("✅")


def test_error_is_shown(qtbot, settings, tmp_path):
    w = make_window(qtbot, settings)
    w.add_files([tmp_path / "fantasma.pdf"])
    wait_done(qtbot, w)
    assert not w.preview.has_document()
    assert "No se pudo convertir" in w.preview.message.text()


def test_drag_out_writes_temp_file(qtbot, settings, sample_html):
    w = make_window(qtbot, settings)
    w.add_files([sample_html])
    wait_done(qtbot, w)
    w.preview.editor.setPlainText("# Editado")
    mime = w.preview.drag_handle.build_mime()
    path = Path(mime.urls()[0].toLocalFile())
    assert path.name == "informe.md"
    assert path.read_text(encoding="utf-8") == "# Editado"
    assert w.jobs[w.current_job].markdown == "# Editado"


def test_save_as(qtbot, settings, sample_html, tmp_path, monkeypatch):
    w = make_window(qtbot, settings)
    w.add_files([sample_html])
    wait_done(qtbot, w)
    target = tmp_path / "salida" / "resultado"
    target.parent.mkdir()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    w.save_current()
    saved = target.with_suffix(".md")
    assert "# Hola" in saved.read_text(encoding="utf-8")
    assert settings.value("last_save_dir") == str(saved.parent)


def test_auto_save_next_to_original(qtbot, settings, sample_html):
    (sample_html.parent / "informe.md").write_text("ya existía")
    w = make_window(qtbot, settings)
    w.auto_save.setChecked(True)
    w.add_files([sample_html])
    wait_done(qtbot, w)
    qtbot.waitUntil(lambda: (sample_html.parent / "informe (1).md").exists(), timeout=5000)
    assert (sample_html.parent / "informe.md").read_text() == "ya existía"


def test_copy(qtbot, settings, sample_html):
    w = make_window(qtbot, settings)
    w.add_files([sample_html])
    wait_done(qtbot, w)
    w.copy_current()
    from PySide6.QtGui import QGuiApplication
    assert "# Hola" in QGuiApplication.clipboard().text()


def test_paths_from_mime_expands_folders(tmp_path):
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.docx").write_text("x")
    (tmp_path / ".oculto").write_text("x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(tmp_path))])
    names = [p.name for p in paths_from_mime(mime)]
    assert names == ["a.pdf", "b.docx"]


def test_unique_path(tmp_path):
    p = tmp_path / "x.md"
    assert unique_path(p) == p
    p.write_text("")
    assert unique_path(p).name == "x (1).md"
