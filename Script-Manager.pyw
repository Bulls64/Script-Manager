"""Script Manager : lanceur des scripts de personnalisation de Windows.

Interface PySide6 au style WinUI 3. Le code est dans le dossier scripts_windows.
Dépendance : pip install -r requirements.txt

Script Manager: launcher for the Windows customization scripts.

PySide6 interface in the WinUI 3 style. The code is in the scripts_windows folder.
Dependency: pip install -r requirements.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from scripts_windows.window import main
except ImportError as exc:  # PySide6 absent / PySide6 missing
    if "PySide6" not in str(exc):
        raise
    import ctypes

    message = "PySide6 est requis.\n\nInstalle-le avec :\npy -3 -m pip install -r requirements.txt"
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, "Script Manager", 0x10)
    else:
        print(message, file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
