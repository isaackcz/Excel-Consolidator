# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\icons\\app.ico', 'assets\\icons'), ('assets\\icons\\logo.png', 'assets\\icons'), ('assets\\icons\\check.svg', 'assets\\icons'), ('assets\\icons\\check_disabled.svg', 'assets\\icons'), ('config\\config.py', 'config')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'openpyxl', 'requests', 'json', 'threading', 'logging', 'tempfile', 'zipfile', 'platform', 'socket', 'urllib.parse', 'urllib.request'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Excel Consolidate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icons\\app.ico'],
)
