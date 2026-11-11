# -*- mode: python ; coding: utf-8 -*-
# Build « onedir » : démarrage immédiat (rien à décompresser dans %TEMP%) et
# moins de faux positifs antivirus qu'un EXE « onefile ».
# Lancé par build.bat ; le résultat va dans dist\Script-Manager\.
# "onedir" build: instant startup (nothing to unpack into %TEMP%) and
# fewer antivirus false positives than a "onefile" EXE.
# Run by build.bat; the result goes to dist\Script-Manager\.
from pathlib import Path

ROOT = Path(SPECPATH)
NAME = "Script-Manager"

a = Analysis(
    [str(ROOT / f"{NAME}.pyw")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "assets" / "app.ico"), "assets")],
    # Interface PySide6 : Tkinter et les modules Qt inutilisés restent dehors.
    # PySide6 interface: Tkinter and the unused Qt modules are left out.
    excludes=["tkinter", "unittest", "pydoc", "test", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=str(ROOT / "assets" / "app.ico"),
    version=str(ROOT / "assets" / "version_info.txt"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)
