# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

rapidocr_datas = collect_data_files("rapidocr")

analysis = Analysis(
    ["src/ocr_keju/ui/app.py"],
    pathex=["src"],
    binaries=[],
    datas=rapidocr_datas,
    hiddenimports=["rapidocr"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="ocr-keju",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
