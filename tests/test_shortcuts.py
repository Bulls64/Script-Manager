"""Raccourcis sur le Bureau : noms, création sans écraser, fenêtre de choix, interface.

Desktop shortcuts: names, creation without overwriting, picker window, interface.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from scripts_windows import core

PROJECT = Path(__file__).resolve().parent.parent


def script(title: str, filename: str, category: str = "bureau") -> core.Script:
    return core.Script(title, filename, f"Description de {title}", category=category)


def fake_runner(calls: list[list[dict[str, str]]], fail: str = "") -> Any:
    """Écrit un faux .lnk par élément, sauf ceux dont le nom contient ``fail``.

    Writes a fake .lnk per item, except those whose name contains ``fail``.
    """

    def run(items: list[dict[str, str]]) -> str:
        calls.append(items)
        for item in items:
            if not fail or fail not in item["path"]:
                Path(item["path"]).write_text(json.dumps(item), encoding="utf-8")
        return "refusé" if fail else ""

    return run


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Raccourci Bureau", "Raccourci Bureau.lnk"),
        ('Créer: a/b\\c?*"<>|', "Créer a b c.lnk"),
        ("  Fin avec un point.  ", "Fin avec un point.lnk"),
        ("...", "Script.lnk"),
        ("CON", "Script CON.lnk"),
        ("x" * 300, "x" * core.SHORTCUT_NAME_MAX + ".lnk"),
    ],
)
def test_shortcut_name(title: str, expected: str) -> None:
    assert core.shortcut_name(title) == expected


def test_desktop_dir_follows_redirection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "read_registry", lambda *_args: r"D:\OneDrive\Bureau")
    assert core.desktop_dir() == Path(r"D:\OneDrive\Bureau")
    monkeypatch.setattr(core, "read_registry", lambda *_args: None)
    assert core.desktop_dir() == Path.home() / "Desktop"


def test_create_shortcuts(tmp_path: Path) -> None:
    scripts_dir, desktop = tmp_path / "scripts", tmp_path / "Bureau"
    scripts_dir.mkdir()
    desktop.mkdir()
    for name in ("a.bat", "b.bat", "c.bat"):
        (scripts_dir / name).write_text("@echo off\r\n", encoding="ascii")
    (desktop / "Déjà là.lnk").write_text("à l'utilisateur", encoding="utf-8")
    calls: list[list[dict[str, str]]] = []
    result = core.create_shortcuts(
        [
            script("Script A", "a.bat"),
            script("Déjà là", "b.bat"),
            script("Script A", "c.bat"),  # même nom / same name
            script("Absent", "absent.bat"),
        ],
        scripts_dir,
        desktop,
        fake_runner(calls),
    )
    assert result.created == ["Script A.lnk"]
    assert result.existing == ["Déjà là.lnk", "Script A.lnk"]
    assert result.failed == ["Absent.lnk"]
    assert (desktop / "Déjà là.lnk").read_text(encoding="utf-8") == "à l'utilisateur"
    (item,) = calls[0]
    assert item == {
        "path": str(desktop / "Script A.lnk"),
        "target": str(scripts_dir / "a.bat"),
        "folder": str(scripts_dir),
        "description": "Description de Script A",
    }


def test_create_shortcuts_reports_failures(tmp_path: Path) -> None:
    (tmp_path / "a.bat").write_text("@echo off\r\n", encoding="ascii")
    (tmp_path / "b.bat").write_text("@echo off\r\n", encoding="ascii")
    calls: list[list[dict[str, str]]] = []
    result = core.create_shortcuts(
        [script("Un", "a.bat"), script("Deux", "b.bat")], tmp_path, tmp_path, fake_runner(calls, "Deux")
    )
    assert (result.created, result.failed, result.error) == (["Un.lnk"], ["Deux.lnk"], "refusé")


def test_create_shortcuts_without_powershell(tmp_path: Path) -> None:
    (tmp_path / "a.bat").write_text("@echo off\r\n", encoding="ascii")

    def missing(_items: list[dict[str, str]]) -> str:
        raise FileNotFoundError("powershell.exe")

    result = core.create_shortcuts([script("Un", "a.bat")], tmp_path, tmp_path, missing)
    assert result.failed == ["Un.lnk"] and "powershell" in result.error
    assert core.create_shortcuts([], tmp_path, tmp_path, missing) == core.ShortcutResult()


def test_shortcut_script_takes_data_from_the_environment() -> None:
    """Aucune donnée n'est collée dans le code PowerShell. / No data is pasted into the PowerShell code."""
    assert "$env:SM_SHORTCUTS | ConvertFrom-Json" in core.SHORTCUT_SCRIPT
    assert "{" not in core.SHORTCUT_SCRIPT.replace("{\n", "").replace("{ ", "")


# -- interface ------------------------------------------------------------------------

pytest.importorskip("PySide6.QtWidgets")


def build(tmp_path: Path) -> Any:
    from scripts_windows import __version__
    from scripts_windows.window import MainWindow

    settings = core.Settings(theme="light", seen_version=__version__)
    scripts = core.load_scripts(PROJECT / "scripts.json")
    return MainWindow(scripts, settings, tmp_path / "s.json", PROJECT, tmp_path)


def test_dialog_lists_scripts_and_skips_those_on_the_desktop(qapp: Any, tmp_path: Path) -> None:
    from scripts_windows.shortcuts import ShortcutsDialog

    scripts = [
        script("Un", "un.bat"),
        script("Deux", "deux.bat", "registre"),
        script("Perso", "perso.bat", core.FAVORITES),
    ]
    (tmp_path / "Deux.lnk").write_text("", encoding="utf-8")
    dialog = ShortcutsDialog(scripts, tmp_path, checked=["UN.bat"])
    assert [s.filename for _box, s in dialog.boxes] == ["un.bat", "perso.bat"]
    assert dialog.on_desktop == ["deux.bat"]
    assert [s.filename for s in dialog.selected()] == ["un.bat"]
    assert dialog.create_button.isEnabled()
    dialog._toggle_all()
    assert len(dialog.selected()) == 2 and "2" in dialog.create_button.text()
    dialog._toggle_all()
    assert dialog.selected() == [] and not dialog.create_button.isEnabled()
    dialog.deleteLater()


def test_window_opens_the_dialog_and_creates_shortcuts(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts_windows import window as window_module

    monkeypatch.setattr(core, "desktop_dir", lambda: tmp_path)
    window = build(tmp_path)
    window.scripts_page.shortcuts_button.click()
    dialog = window.shortcuts_dialog
    assert dialog is not None and dialog.isVisible()
    assert len(dialog.boxes) == len(window.all_scripts())
    window.choose_shortcuts()
    assert window.shortcuts_dialog is dialog  # une seule fenêtre / only one window
    dialog.reject()
    assert window.shortcuts_dialog is None

    calls: list[Any] = []

    def fake_create(scripts: list[core.Script], _folder: Path) -> core.ShortcutResult:
        calls.append(scripts)
        return core.ShortcutResult(created=["X.lnk"])

    monkeypatch.setattr(window_module, "IS_WINDOWS", True)
    monkeypatch.setattr(core, "create_shortcuts", fake_create)
    shown: list[tuple[str, str, str]] = []
    monkeypatch.setattr(window, "notify", lambda *args: shown.append(args))
    card = next(iter(window.scripts_page.script_cards.values()))
    card.shortcut.emit(card)
    deadline = time.monotonic() + 5
    while window._tasks and time.monotonic() < deadline:
        qapp.processEvents()
    assert calls == [[card.script]]
    assert shown[-1][0] == "success" and "X.lnk" in shown[-1][2]
    window.close()


def test_shortcuts_need_windows(qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts_windows import window as window_module

    monkeypatch.setattr(window_module, "IS_WINDOWS", False)
    window = build(tmp_path)
    shown: list[tuple[str, str, str]] = []
    monkeypatch.setattr(window, "notify", lambda *args: shown.append(args))
    window.create_shortcuts(window.scripts[:1])
    assert shown and shown[-1][0] == "caution" and not window._tasks
    window.close()


def test_undo_scripts_exist() -> None:
    from scripts_windows.pages import UNDO_SCRIPTS

    names = {s.filename for s in core.load_scripts(PROJECT / "scripts.json")}
    assert set(UNDO_SCRIPTS) <= names
    assert {name for name in names if name.startswith("Restaurer-")} <= set(UNDO_SCRIPTS)
