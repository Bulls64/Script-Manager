"""Interface PySide6, rendue hors écran.

PySide6 interface, rendered offscreen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QWidget  # noqa: E402

from scripts_windows import core  # noqa: E402
from scripts_windows.cards import ArrowsCard, ResponsiveGrid, ScriptCard  # noqa: E402
from scripts_windows.pages import JournalDay  # noqa: E402
from scripts_windows.theme import make_tokens, tok  # noqa: E402
from scripts_windows.window import MainWindow  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


class FakeProcess:
    def __init__(self, code: int | None) -> None:
        self.code = code

    def poll(self) -> int | None:
        return self.code


def build(qapp: Any, tmp_path: Path, settings: core.Settings | None = None) -> MainWindow:
    scripts = core.load_scripts(PROJECT / "scripts.json")
    window = MainWindow(
        scripts, settings or core.Settings(theme="light"), tmp_path / "s.json", PROJECT, tmp_path
    )
    window.resize(1240, 820)
    return window


def test_tokens_share_the_same_keys() -> None:
    light = make_tokens(False, core.ACCENTS[0], False)
    dark = make_tokens(True, core.ACCENTS[0], False)
    assert light.keys() == dark.keys()


def test_one_card_per_script_and_one_switch_for_the_arrows(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    scripts = core.load_scripts(PROJECT / "scripts.json")
    page = window.scripts_page
    assert set(page.script_cards) == {s.filename for s in scripts} - {core.ARROWS_ON, core.ARROWS_OFF}
    assert isinstance(page.arrows_card, ArrowsCard)


def test_search_filters_cards(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    page = window.scripts_page
    page.search.setText("god mode")
    shown = [c for c in page.cards if not c.property("filtered")]
    assert shown and all("god" in getattr(c, "search_text", "") for c in shown)
    page.search.setText("zzz introuvable")
    assert page.empty.isVisibleTo(page)


def test_theme_and_accent_are_saved(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    window.quick_toggle_theme()
    window.set_accent("#107C10")
    assert core.load_settings(tmp_path / "s.json") == core.Settings(theme="dark", accent="#107C10")
    assert window.settings_page.combo.currentData() == "dark"


def test_launch_watch_and_journal(qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lancement réel simulé : le processus se termine en échec, puis en succès.

    Simulated real launch: the process ends in failure, then in success.
    """
    window = build(qapp, tmp_path)
    card = next(iter(window.scripts_page.script_cards.values()))
    assert isinstance(card, ScriptCard)
    process = FakeProcess(None)
    calls: list[tuple[Path, bool]] = []

    def fake_start(path: Path, elevate: bool) -> FakeProcess:
        calls.append((path, elevate))
        return process

    monkeypatch.setattr(core, "start_script", fake_start)
    window.launch_card(card)
    assert calls == [(PROJECT / "scripts" / card.script.filename, card.script.admin)]
    assert not card.button.isEnabled()
    window.launch_card(card)  # déjà en cours : ignoré / already running: ignored
    assert len(calls) == 1
    process.code = 1
    window._watch()
    assert card.button.isEnabled()
    assert window.info.severity == "critical"
    assert window.journal_page.entries[0].text.endswith("échec (code 1)")


def test_cancelled_elevation_reverts_arrows_switch(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path)
    card = window.scripts_page.arrows_card
    assert card is not None

    def refuse(path: Path, elevate: bool) -> FakeProcess:
        error = OSError("annulé")
        error.winerror = core.ERROR_CANCELLED  # type: ignore[attr-defined]
        raise error

    monkeypatch.setattr(core, "start_script", refuse)
    card.switch.setChecked(True)
    assert not card.switch.isChecked()
    assert window.info.severity == "caution"


def test_journal_is_built_lazily_capped_and_painted(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    window.show()
    journal = window.journal_page
    for i in range(core.JOURNAL_LIMIT + 5):
        window.record(f"s{i}.bat", "terminé (code 0)")
    # Page cachée : rien n'est construit, mais la liste reste bornée.
    # Hidden page: nothing is built, but the list stays bounded.
    assert len(journal.entries) == core.JOURNAL_LIMIT
    assert journal.entries[0].text == f"s{core.JOURNAL_LIMIT + 4}.bat : terminé (code 0)"
    assert not journal.findChildren(JournalDay)
    window.stack.setCurrentWidget(journal)
    qapp.processEvents()
    days = journal.findChildren(JournalDay)
    assert len(days) == 1 and len(days[0].entries) == core.JOURNAL_LIMIT
    # Une carte par jour : quelques widgets, pas un par ligne.
    # One card per day: a few widgets, not one per line.
    assert len(journal.findChildren(QWidget)) < 30
    assert not days[0].grab().isNull()
    window.record("dernier.bat", "échec (code 2)")
    qapp.processEvents()
    assert journal.findChildren(JournalDay)[-1].entries[0].kind == "critical"
    window.close()


def test_theme_colors_follow_the_theme(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    light = tok("bg").name()
    window.quick_toggle_theme()
    assert tok("bg").name() != light
    assert tok("bg").name() == make_tokens(True, core.ACCENTS[0], False)["bg"]


def test_grid_lays_out_once_on_demand(qapp: Any) -> None:
    grid = ResponsiveGrid(min_column=100, spacing=0)
    grid.resize(300, 200)
    widgets = [QWidget() for _ in range(5)]
    for widget in widgets:
        grid.add(widget)
    assert grid.grid.count() == 0
    grid.relayout()
    assert grid.columns == 3 and grid.grid.count() == 5
    widgets[0].setProperty("filtered", True)
    grid.relayout(force=True)
    assert grid.grid.count() == 4 and grid.visible_count() == 4


# -- points de restauration / restore points ---------------------------------


class Launcher:
    """Faux lancements : un processus par appel, gardés pour être terminés à la main.

    Fake launches: one process per call, kept so they can be finished by hand.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.scripts: list[tuple[Path, FakeProcess]] = []
        self.restores: list[tuple[str, FakeProcess]] = []

        def start_script(path: Path, elevate: bool) -> FakeProcess:
            process = FakeProcess(None)
            self.scripts.append((path, process))
            return process

        def start_restore(app_dir: Path, description: str) -> FakeProcess:
            process = FakeProcess(None)
            self.restores.append((description, process))
            return process

        monkeypatch.setattr(core, "start_script", start_script)
        monkeypatch.setattr(core, "start_restore_point", start_restore)


def card_named(window: MainWindow, filename: str) -> ScriptCard:
    return window.scripts_page.script_cards[filename]


def test_restore_point_then_launch(qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = build(qapp, tmp_path)
    fake = Launcher(monkeypatch)
    card = card_named(window, "Creer-dossier-GodMode.bat")
    window.launch_card(card, restore=True)
    assert fake.restores and not fake.scripts  # le script attend le point / the script waits for the point
    assert "Creer-dossier-GodMode.bat" in fake.restores[0][0]
    assert card.button.text() == "Point de restauration…"
    assert window.settings_page.restore_now.text() == "Création…"
    fake.restores[0][1].code = core.RESTORE_CREATED
    window._watch()
    assert [p.name for p, _ in fake.scripts] == ["Creer-dossier-GodMode.bat"]
    assert card.button.text() == "En cours…"
    assert window.settings_page.restore_now.text() == "Créer"
    texts = [e.text for e in window.journal_page.entries]
    assert "Point de restauration : créé" in texts
    fake.scripts[0][1].code = 0
    window._watch()
    assert card.button.isEnabled() and window.info.severity == "success"


def test_failed_restore_point_blocks_the_script(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path)
    fake = Launcher(monkeypatch)
    card = card_named(window, "Creer-dossier-GodMode.bat")
    window.launch_card(card, restore=True)
    fake.restores[0][1].code = core.RESTORE_DISABLED
    window._watch()
    assert not fake.scripts
    assert card.button.isEnabled() and card.button.text() == "Lancer"
    assert window.info.severity == "critical"
    assert window.journal_page.entries[0].kind == "critical"


def test_recent_restore_point_still_launches(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path)
    fake = Launcher(monkeypatch)
    window.launch_card(card_named(window, "Creer-raccourci-Bureau.bat"), restore=True)
    fake.restores[0][1].code = core.RESTORE_RECENT
    window._watch()
    assert len(fake.scripts) == 1 and window.info.severity == "caution"


def test_automatic_restore_point_only_for_system_scripts(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path)
    fake = Launcher(monkeypatch)
    window.settings_page.restore_auto.setChecked(True)
    assert core.load_settings(tmp_path / "s.json").restore_point is True
    window.launch_card(card_named(window, "Creer-raccourci-Bureau.bat"))
    assert len(fake.scripts) == 1 and not fake.restores
    window.launch_card(card_named(window, "Lancer-WinUtil.bat"))
    assert len(fake.restores) == 1 and len(fake.scripts) == 1
    # Un seul point de restauration à la fois.
    # Only one restore point at a time.
    arrows = window.scripts_page.arrows_card
    assert arrows is not None
    arrows.switch.setChecked(True)
    assert not arrows.switch.isChecked() and len(fake.restores) == 1


def test_refused_restore_point_reverts_arrows_switch(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path, core.Settings(theme="light", restore_point=True))
    started: list[Path] = []
    monkeypatch.setattr(core, "start_script", lambda path, elevate: started.append(path))

    def refuse(app_dir: Path, description: str) -> FakeProcess:
        error = OSError("annulé")
        error.winerror = core.ERROR_CANCELLED  # type: ignore[attr-defined]
        raise error

    monkeypatch.setattr(core, "start_restore_point", refuse)
    arrows = window.scripts_page.arrows_card
    assert arrows is not None
    arrows.switch.setChecked(True)
    assert not arrows.switch.isChecked() and not started
    assert window.info.severity == "caution"


def test_manual_restore_point(qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = build(qapp, tmp_path)
    fake = Launcher(monkeypatch)
    window.settings_page.restore_now_requested.emit()
    assert len(fake.restores) == 1 and "point manuel" in fake.restores[0][0]
    fake.restores[0][1].code = core.RESTORE_CREATED
    window._watch()
    assert not fake.scripts and window.info.severity == "success"
    assert not window.running


def test_cleanup_button_launches_without_automatic_restore_point(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = build(qapp, tmp_path, core.Settings(theme="light", restore_point=True))
    fake = Launcher(monkeypatch)
    card = window.scripts_page.script_cards[core.RESTORE_CLEANUP]
    assert card.script.category == "systeme" and card.script.admin
    window.settings_page.restore_cleanup_requested.emit()
    assert [p.name for p, _ in fake.scripts] == [core.RESTORE_CLEANUP]
    assert not fake.restores
    assert card.button.text() == "En cours…"


# -- favoris / favorites ------------------------------------------------------------


def favorites_window(qapp: Any, tmp_path: Path, favorites: list[str] | None = None) -> MainWindow:
    """Fenêtre sur un dossier de scripts temporaire, avec deux scripts personnels.

    Window on a temporary scripts folder, with two personal scripts.
    """
    app_dir = tmp_path / "projet"
    folder = app_dir / "scripts"
    folder.mkdir(parents=True)
    (app_dir / "scripts.json").write_bytes((PROJECT / "scripts.json").read_bytes())
    # hors du dossier des scripts
    # outside the scripts folder
    (app_dir / "build.bat").write_text("@echo off\r\n", encoding="ascii")
    (folder / "Mon-script.bat").write_text("@echo off\r\nrem Fait une chose utile.\r\n", encoding="ascii")
    (folder / "Autre.cmd").write_text("@echo off\r\n", encoding="ascii")
    scripts = core.load_scripts(app_dir / "scripts.json")
    settings = core.Settings(theme="light", favorites=favorites or [])
    window = MainWindow(scripts, settings, tmp_path / "s.json", app_dir, tmp_path)
    window.resize(1240, 820)
    return window


def test_favorites_section_starts_empty_with_an_add_button(qapp: Any, tmp_path: Path) -> None:
    window = favorites_window(qapp, tmp_path)
    page = window.scripts_page
    assert page.favorites_box.isVisibleTo(page) and page.favorites_empty.isVisibleTo(page)
    assert page.available_favorites() == ["Autre.cmd", "Mon-script.bat"]
    assert "Favoris" in [item.text() for item in window.nav]


def test_add_launch_and_remove_a_favorite(qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    window = favorites_window(qapp, tmp_path)
    page = window.scripts_page
    page.favorite_added.emit("Mon-script.bat")
    card = page.favorite_cards["Mon-script.bat"]
    assert card.script.title == "Mon script" and card.script.description == "Fait une chose utile."
    assert not page.favorites_empty.isVisibleTo(page)
    assert page.available_favorites() == ["Autre.cmd"]
    assert core.load_settings(tmp_path / "s.json").favorites == ["Mon-script.bat"]

    fake = Launcher(monkeypatch)
    calls: list[bool] = []

    def start(path: Path, elevate: bool) -> FakeProcess:
        calls.append(elevate)
        return FakeProcess(0)

    monkeypatch.setattr(core, "start_script", start)
    window.launch_card(card)
    window._watch()
    card.launch_elevated.emit(card)
    window._watch()
    assert calls == [False, True] and not fake.restores
    assert "Mon-script.bat : lancé en administrateur" in [e.text for e in window.journal_page.entries]

    card.unfavorite.emit(card)
    assert "Mon-script.bat" not in page.favorite_cards
    assert core.load_settings(tmp_path / "s.json").favorites == []
    assert page.favorites_empty.isVisibleTo(page)


def test_favorites_are_restored_filtered_and_searchable(qapp: Any, tmp_path: Path) -> None:
    window = favorites_window(qapp, tmp_path, ["Autre.cmd", "Creer-raccourci-Bureau.bat", "Disparu.bat"])
    page = window.scripts_page
    # Un script intégré n'est jamais doublé en favori ; un favori disparu garde sa carte.
    # A built-in script is never duplicated as a favorite; a missing favorite keeps its card.
    assert list(page.favorite_cards) == ["Autre.cmd", "Disparu.bat"]
    assert page.favorite_cards["Disparu.bat"].missing
    page.search.setText("autre")
    assert page.favorites_box.isVisibleTo(page) and not page.empty.isVisibleTo(page)
    page.search.setText("introuvable")
    assert not page.favorites_box.isVisibleTo(page)
    page.search.clear()
    page.set_category(core.FAVORITES)
    assert page.title.text() == "Favoris" and page.favorites_box.isVisibleTo(page)
    assert not page.sections["bureau"][0].isVisibleTo(page)


def test_missing_scripts_folder_is_reported(qapp: Any, tmp_path: Path) -> None:
    (tmp_path / "scripts.json").write_bytes((PROJECT / "scripts.json").read_bytes())
    scripts = core.load_scripts(tmp_path / "scripts.json")
    window = MainWindow(scripts, core.Settings(theme="light"), None, tmp_path, tmp_path)
    shown: list[str] = []
    window.notify = lambda severity, title, message: shown.append(title)  # type: ignore[method-assign]
    qapp.processEvents()
    assert "Dossier des scripts introuvable" in shown
    assert all(card.missing for card in window.scripts_page.script_cards.values())


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("mica", [False, True])
def test_transparency_fades_surfaces_only(dark: bool, mica: bool) -> None:
    opaque = make_tokens(dark, core.ACCENTS[0], mica)
    faded = make_tokens(dark, core.ACCENTS[0], mica, 50)
    for name in ("layer", "card"):
        assert QColor(faded[name]).alpha() == round(QColor(opaque[name]).alpha() / 2)
    for name in ("text", "control", "accent", "flyout"):
        assert faded[name] == opaque[name]
    assert make_tokens(dark, core.ACCENTS[0], mica, 0) == opaque


def test_transparency_slider_applies_and_saves(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path, core.Settings(theme="dark", transparency=20))
    slider = window.settings_page.transparency
    assert slider.value() == 20 and window.settings_page.transparency_value.text() == "20 %"
    slider.setValue(40)
    assert window.settings.transparency == 40
    window._theme_timer.timeout.emit()
    # Sans fond flouté (hors Windows 11), c'est toute la fenêtre qui devient transparente.
    # Without a blurred background (outside Windows 11), the whole window becomes transparent.
    assert abs(window.windowOpacity() - 0.6) < 0.01
    window.close()
    assert core.load_settings(tmp_path / "s.json").transparency == 40
    slider.setValue(slider.maximum() + 10)
    assert window.settings.transparency == core.TRANSPARENCY_MAX


def test_window_in_english(qapp: Any, tmp_path: Path) -> None:
    from scripts_windows import i18n

    i18n.set_language("en")
    window = build(qapp, tmp_path)
    assert [item.text() for item in window.nav][:2] == ["Home", "Desktop"]
    assert window.scripts_page.title.text() == "Home"
    assert window.settings_page.restore_now.text() == "Create"
    window.nav[-1].click()
    assert window.stack.currentWidget() is window.settings_page


def test_language_choice_is_saved_and_announced(qapp: Any, tmp_path: Path) -> None:
    window = build(qapp, tmp_path)
    combo = window.settings_page.language
    assert combo.currentData() == "system"
    combo.setCurrentIndex(combo.findData("en"))
    assert core.load_settings(tmp_path / "s.json").language == "en"
    # Le message est écrit dans la langue choisie, l'interface ne change qu'au redémarrage.
    # The message is written in the chosen language; the interface only changes on restart.
    assert window.info._title.text() == "Language" and "English" in window.info._message.text()
    assert window.scripts_page.title.text() == "Accueil"


def test_running_text_follows_the_language(qapp: Any, tmp_path: Path) -> None:
    """Le texte « En cours… » est traduit à l'appel, pas figé au chargement du module.

    The "En cours…" text is translated at call time, not frozen when the module loads.
    """
    from scripts_windows import i18n

    i18n.set_language("en")
    script = core.Script("Titre", "a.bat", "Texte")
    card = ScriptCard(script, tmp_path)
    card.set_running(True)
    assert card.button.text() == i18n.tr("En cours…") != "En cours…"


def test_grid_stretches_every_column_beyond_six(qapp: Any) -> None:
    grid = ResponsiveGrid(min_column=100, spacing=0)
    grid.resize(800, 200)
    for _ in range(8):
        grid.add(QWidget())
    grid.relayout()
    assert grid.columns == 8
    assert all(grid.grid.columnStretch(i) == 1 for i in range(8))
    grid.resize(300, 200)
    grid.relayout()
    assert [grid.grid.columnStretch(i) for i in range(8)] == [1, 1, 1, 0, 0, 0, 0, 0]


def test_helper_scripts_and_case_duplicates_are_not_favorites(qapp: Any, tmp_path: Path) -> None:
    window = favorites_window(qapp, tmp_path, ["autre.CMD", "Autre.cmd", "Creer-point-restauration.bat"])
    assert list(window.scripts_page.favorite_cards) == ["autre.CMD"]
    assert window.scripts_page.add_favorite("CREER-RACCOURCI-BUREAU.BAT") is None


def test_exposed_scripts_folder_is_reported(
    qapp: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(core, "exposed_location", lambda _folder: "il est sur un lecteur amovible")
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        MainWindow, "notify", lambda _self, severity, _title, message: shown.append((severity, message))
    )
    favorites_window(qapp, tmp_path)
    qapp.processEvents()
    assert any(severity == "caution" and "lecteur amovible" in text for severity, text in shown)
