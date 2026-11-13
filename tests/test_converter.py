import pytest

from markitdown_desktop.converter import ConversionError, Converter, convert_file, markdown_filename


def test_convert_html(sample_html):
    md = convert_file(sample_html)
    assert "# Hola" in md
    assert "**prueba**" in md


def test_convert_docx(sample_docx):
    md = convert_file(sample_docx)
    assert "# Informe trimestral" in md
    assert "Ventas al alza." in md


def test_missing_file(tmp_path):
    with pytest.raises(ConversionError, match="no existe"):
        convert_file(tmp_path / "nada.pdf")


def test_directory(tmp_path):
    with pytest.raises(ConversionError, match="carpeta"):
        convert_file(tmp_path)


def test_markdown_filename():
    assert markdown_filename("/a/b/informe.final.pdf") == "informe.final.md"


def test_converter_signals(qtbot, sample_html, tmp_path):
    conv = Converter()
    with qtbot.waitSignal(conv.finished, timeout=20000) as ok:
        job = conv.submit(sample_html)
    assert ok.args[0] == job and "# Hola" in ok.args[1]
    with qtbot.waitSignal(conv.failed, timeout=20000) as bad:
        conv.submit(tmp_path / "no.pdf")
    assert "no existe" in bad.args[1]
