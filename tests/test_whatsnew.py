"""Fenêtre « Nouveautés » : liste par version, affichage au premier lancement, réglage.

"What's new" window: list per version, display on first run, setting.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6.QtWidgets")

from scripts_windows import __version__, core, i18n, whatsnew  # noqa: E402
from scripts_windows.window import MainWindow  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def build(tmp_path: Path, settings: core.Settings) -> MainWindow:
    scripts = core.load_scripts(PROJECT / "scripts.json")
    return MainWindow(scripts, settings, tmp_path / "s.json", PROJECT, tmp_path)


def test_current_version_has_notes() -> None:
    assert whatsnew.NOTES.get(__version__), "ajouter les nouveautés de la version dans whatsnew.NOTES"


def test_current_version_is_in_the_changelog() -> None:
    changelog = (PROJECT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(__version__)}\b", changelog, re.M)


def test_notes_are_translated() -> None:
    i18n.set_language("en")
    try:
        english = whatsnew.notes()
    finally:
        i18n.set_language("fr")
    assert english and english != whatsnew.notes()


@pytest.mark.parametrize(
    ("enabled", "seen", "expected"),
    [(True, "", True), (True, "2.0.0", True), (True, __version__, False), (False, "", False)],
)
def test_should_show(enabled: bool, seen: str, expected: bool) -> None:
    settings = core.Settings(whats_new=enabled, seen_version=seen)
    assert whatsnew.should_show(settings) is expected
    assert whatsnew.should_show(core.Settings(), "0.0.1") is False  # pas de liste / no list


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    core.save_settings(path, core.Settings(whats_new=False, seen_version="2.18.0"))
    loaded = core.load_settings(path)
    assert (loaded.whats_new, loaded.seen_version) == (False, "2.18.0")
    bad = core.Settings.from_dict({"whats_new": "non", "seen_version": "../x"})
    assert (bad.whats_new, bad.seen_version) == (True, "")


def test_first_run_of_a_version_marks_it_seen(qapp: Any, tmp_path: Path) -> None:
    window = build(tmp_path, core.Settings(theme="light", seen_version="2.18.0"))
    assert core.load_settings(tmp_path / "s.json").seen_version == __version__
    window.close()


def test_dialog_lists_the_notes(qapp: Any, tmp_path: Path) -> None:
    window = build(tmp_path, core.Settings(theme="light", seen_version=__version__))
    window.settings_page.whats_new_requested.emit()
    dialog = window.whats_new_dialog
    assert dialog is not None and dialog.isVisible()
    assert __version__ in dialog.windowTitle()
    assert dialog.items == list(whatsnew.notes())
    # Un second clic ne crée pas une autre fenêtre. / A second click does not open another window.
    window.show_whats_new()
    assert window.whats_new_dialog is dialog
    dialog.accept()
    assert window.whats_new_dialog is None
    window.close()


def test_unknown_version_dialog_is_not_empty(qapp: Any) -> None:
    dialog = whatsnew.WhatsNewDialog(None, "0.0.1")
    assert dialog.items == []
    dialog.deleteLater()


def test_toggle_is_saved(qapp: Any, tmp_path: Path) -> None:
    window = build(tmp_path, core.Settings(theme="light", seen_version=__version__))
    window.settings_page.whats_new_auto.click()
    assert core.load_settings(tmp_path / "s.json").whats_new is False
    window.close()
