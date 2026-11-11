"""Rend le paquet scripts_windows importable et fournit une application Qt hors écran.

Makes the scripts_windows package importable and provides an offscreen Qt application.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp() -> Iterator[Any]:
    pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtWidgets import QApplication

    from scripts_windows.window import make_app

    app = QApplication.instance() or make_app([])
    yield app
    # Fenêtres détruites avant l'arrêt de Python : sinon Qt peut détruire des objets déjà libérés
    # (« pure virtual method called ») pendant la fermeture de l'interpréteur.
    # Windows destroyed before Python shuts down: otherwise Qt may destroy already freed objects
    # ("pure virtual method called") while the interpreter exits.
    import gc

    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    app.processEvents()
    gc.collect()


@pytest.fixture(autouse=True)
def french_interface() -> Iterator[None]:
    """Les tests vérifient les textes français ; chaque test repart du français.

    The tests check the French texts; each test starts again from French.
    """
    from scripts_windows import i18n

    i18n.set_language("fr")
    yield
    i18n.set_language("fr")
