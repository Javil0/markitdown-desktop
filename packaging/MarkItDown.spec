# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller:  pyinstaller packaging/MarkItDown.spec --noconfirm
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

sys.path.insert(0, str(Path(SPECPATH).parent / "src"))
from markitdown_desktop import __version__  # noqa: E402

datas, binaries, hiddenimports = [], [], []
for package in ("markitdown", "magika", "pdfminer", "mammoth", "pptx", "openpyxl", "xlrd",
                "pandas", "markdownify", "speech_recognition", "pydub", "olefile",
                "azure.ai.documentintelligence", "youtube_transcript_api"):
    try:
        d, b, h = collect_all(package)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

icon = Path(SPECPATH) / "MarkItDown.icns"
icon = str(icon) if icon.exists() else None

a = Analysis(
    [str(Path(SPECPATH) / "run.py")],
    pathex=[str(Path(SPECPATH).parent / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarkItDown",
    console=False,
    argv_emulation=False,
    icon=icon,
)

coll = COLLECT(exe, a.binaries, a.datas, name="MarkItDown")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MarkItDown.app",
        icon=icon,
        bundle_identifier="io.github.javil0.markitdown-desktop",
        version=__version__,
        info_plist={
            "CFBundleName": "MarkItDown",
            "CFBundleDisplayName": "MarkItDown",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            # Permite soltar cualquier archivo sobre el icono del Dock y usar "Abrir con"
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Documento",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "LSItemContentTypes": ["public.data", "public.content"],
                }
            ],
        },
    )
