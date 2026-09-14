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
    [],
    exclude_binaries=True,
    name="ocr-keju",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ocr-keju",
)
