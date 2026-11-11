"""Cœur sans interface : manifeste, emplacements, réglages, journal.

Core without interface: manifest, locations, settings, log.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts_windows import core

PROJECT = Path(__file__).resolve().parent.parent


def entry(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"title": "Titre", "filename": "a.bat", "description": "Texte"}
    base.update(overrides)
    return base


# -- manifeste / manifest -------------------------------------------------


def test_real_manifest_is_valid_and_every_script_exists() -> None:
    scripts = core.load_scripts(PROJECT / "scripts.json")
    assert scripts
    for script in scripts:
        assert (core.scripts_dir(PROJECT) / script.filename).is_file(), script.filename
    names = {s.filename for s in scripts}
    assert {core.ARROWS_ON, core.ARROWS_OFF} <= names


def test_parse_minimal_entry_defaults() -> None:
    (script,) = core.parse_scripts({"scripts": [entry()]})
    assert (script.admin, script.registry, script.internet) == (False, False, False)
    assert (script.category, script.icon) == ("autres", "window")
    assert script.badges == []


def test_badges_follow_flags() -> None:
    (script,) = core.parse_scripts({"scripts": [entry(admin=True, internet=True)]})
    assert script.badges == ["Administrateur", "Internet"]


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"scripts": []},
        {"scripts": "a.bat"},
        {"scripts": [entry(filename="..\\evil.bat")]},
        {"scripts": [entry(filename="sub/a.bat")]},
        {"scripts": [entry(filename="C:a.bat")]},
        {"scripts": [entry(filename="a.exe")]},
        {"scripts": [entry(title="")]},
        {"scripts": [entry(admin="yes")]},
        {"scripts": [entry(color="red")]},
        {"scripts": [entry(category="jeux")]},
        {"scripts": [entry(icon="rocket")]},
        {"scripts": [entry(), entry(filename="A.BAT")]},
    ],
)
def test_parse_rejects_bad_manifests(data: object) -> None:
    with pytest.raises(core.ManifestError):
        core.parse_scripts(data)


def test_load_scripts_reports_json_position(tmp_path: Path) -> None:
    bad = tmp_path / "scripts.json"
    bad.write_text('{"scripts": [\n  {"title": }\n]}', encoding="utf-8")
    with pytest.raises(core.ManifestError, match="ligne 2"):
        core.load_scripts(bad)


def test_load_scripts_accepts_bom(tmp_path: Path) -> None:
    path = tmp_path / "scripts.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"scripts": [entry()]}).encode())
    assert len(core.load_scripts(path)) == 1


# -- emplacements / locations ---------------------------------------------


def test_find_app_dir_from_sources() -> None:
    assert core.find_app_dir() == PROJECT


def test_find_app_dir_climbs_from_onedir_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "scripts.json").write_text("{}", encoding="utf-8")
    exe_dir = tmp_path / "dist" / "Script-Manager"
    exe_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "Script-Manager.exe"))
    assert core.find_app_dir() == tmp_path


def test_data_dir_uses_localappdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert core.data_dir() == tmp_path / "Scripts-Windows"


def test_app_icon_is_bundled_resource() -> None:
    assert core.resource_path("assets/app.ico").is_file()


# -- réglages / settings --------------------------------------------------


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "settings.json"
    core.save_settings(path, core.Settings(theme="dark", accent="#8764B8", mica=True))
    assert core.load_settings(path) == core.Settings(theme="dark", accent="#8764B8", mica=True)


@pytest.mark.parametrize(
    "content",
    ["", "not json", "[1, 2]", '{"theme": "rose", "accent": "blue", "mica": "oui"}'],
)
def test_bad_settings_fall_back_to_defaults(tmp_path: Path, content: str) -> None:
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    assert core.load_settings(path) == core.Settings()


def test_old_settings_file_keeps_theme(tmp_path: Path) -> None:
    """settings.json de la v2.1 : seule la clé « theme » existait.

    settings.json from v2.1: only the "theme" key existed.
    """
    path = tmp_path / "settings.json"
    path.write_text('{"theme": "dark"}', encoding="utf-8")
    assert core.load_settings(path).theme == "dark"


# -- journal / log --------------------------------------------------------


def test_read_journal_parses_and_classifies(tmp_path: Path) -> None:
    (tmp_path / "launcher.log").write_text(
        "2026-11-08 10:00:00,123 INFO a.bat : lancé\n"
        "2026-11-08 10:00:05,456 INFO a.bat : terminé (code 0)\n"
        "ligne illisible\n"
        "2026-11-08 10:01:00,000 WARNING b.bat : échec (code 1)\n"
        "2026-11-08 10:02:00,000 INFO c.bat : élévation refusée\n",
        encoding="utf-8",
    )
    entries = core.read_journal(tmp_path)
    assert [e.kind for e in entries] == ["caution", "critical", "success", "info"]
    assert entries[0].text == "c.bat : élévation refusée"


def test_read_journal_without_log(tmp_path: Path) -> None:
    assert core.read_journal(tmp_path) == []


def test_read_journal_reads_only_the_end_of_a_large_log(tmp_path: Path) -> None:
    """Journal plein (256 Ko) : seules les dernières entrées sont lues, même
    si la lecture partielle coupe une ligne ou un caractère accentué.

    Full log (256 KB): only the last entries are read, even
    if the partial read cuts a line or an accented character.
    """
    filler = "2026-11-07 09:00:00,000 INFO vieux.bat : terminé (code 0)\n" * 5000
    noise = "Traceback (most recent call last):\n  ligne de trace\n"
    recent = "".join(
        f"2026-11-08 10:{i // 60:02d}:{i % 60:02d},000 INFO s{i}.bat : lancé\n" for i in range(150)
    )
    (tmp_path / "launcher.log").write_text(filler + noise + recent, encoding="utf-8")
    entries = core.read_journal(tmp_path)
    assert len(entries) == core.JOURNAL_LIMIT
    assert entries[0].text == "s149.bat : lancé"
    assert entries[-1].text == f"s{150 - core.JOURNAL_LIMIT}.bat : lancé"
    assert [e.text for e in core.read_journal(tmp_path, limit=3)] == [
        "s149.bat : lancé",
        "s148.bat : lancé",
        "s147.bat : lancé",
    ]


def test_registry_is_not_read_outside_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "IS_WINDOWS", False)
    assert core.read_registry("HKEY_CURRENT_USER", core.PERSONALIZE_KEY, "AppsUseLightTheme") is None
    assert core.arrows_hidden() is False
    assert core.system_prefers_dark_registry() is False


@pytest.mark.parametrize(
    ("code", "severity"),
    [(0, "success"), (1, "critical"), (core.STATUS_CONTROL_C_EXIT, "caution")],
)
def test_describe_exit(code: int, severity: str) -> None:
    assert core.describe_exit(code)[0] == severity


# -- points de restauration / restore points ----------------------------------


def test_restore_point_command_runs_the_bat_through_cmd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    program, parameters = core.restore_point_command(Path("C:/Mes scripts"), "Script Manager : avant a.bat")
    assert program.replace("\\", "/").endswith("System32/cmd.exe")
    assert parameters.startswith('/d /c ""')
    assert core.RESTORE_SCRIPT in parameters
    assert parameters.endswith('" "Script Manager : avant a.bat""')


def test_restore_point_description_is_cleaned_for_cmd() -> None:
    _, parameters = core.restore_point_command(Path("C:/s"), 'a"b%PATH%^c!d&e')
    assert parameters.endswith('" "abPATHcd&e""'), parameters


@pytest.mark.parametrize(
    ("code", "severity", "launch"),
    [
        (core.RESTORE_CREATED, "success", True),
        (core.RESTORE_RECENT, "caution", True),
        (core.RESTORE_DISABLED, "critical", False),
        (core.RESTORE_FAILED, "critical", False),
        (core.STATUS_CONTROL_C_EXIT, "caution", False),
    ],
)
def test_describe_restore(code: int, severity: str, launch: bool) -> None:
    assert core.describe_restore(code)[0] == severity
    assert core.restore_allows_launch(code) is launch


def test_restore_journal_lines_are_classified() -> None:
    assert core.classify("Point de restauration : créé") == "success"
    assert core.classify("Point de restauration : protection du système désactivée") == "critical"


def test_restore_point_setting_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    core.save_settings(path, core.Settings(restore_point=True))
    assert core.load_settings(path).restore_point is True
    assert core.Settings.from_dict({"restore_point": "oui"}).restore_point is False


def test_restore_script_is_shipped() -> None:
    assert (core.scripts_dir(PROJECT) / core.RESTORE_SCRIPT).is_file()


def test_restore_point_flag_in_manifest() -> None:
    base = {"title": "T", "filename": "a.bat", "description": "D", "admin": True}
    assert core.parse_scripts({"scripts": [base]})[0].restore_point is True
    script = core.parse_scripts({"scripts": [{**base, "restore_point": False}]})[0]
    assert not core.needs_restore_point(script)
    with pytest.raises(core.ManifestError, match="restore_point"):
        core.parse_scripts({"scripts": [{**base, "restore_point": "non"}]})


def test_cleanup_script_is_shipped_and_never_preceded_by_a_point() -> None:
    scripts = {s.filename: s for s in core.load_scripts(PROJECT / "scripts.json")}
    cleanup = scripts[core.RESTORE_CLEANUP]
    assert cleanup.admin and not core.needs_restore_point(cleanup)
    assert (core.scripts_dir(PROJECT) / core.RESTORE_CLEANUP).is_file()


# -- favoris / favorites ----------------------------------------------------------


def test_find_user_scripts_skips_integrated_and_project_tools(tmp_path: Path) -> None:
    names = ("b-perso.bat", "A-perso.CMD", "integre.bat", "build.bat", "notes.txt", "outil.ps1")
    for name in (*names, "Creer-point-restauration.bat", "Animations-Windows.bat"):
        (tmp_path / name).write_text("@echo off\r\n", encoding="ascii")
    (tmp_path / "dossier.bat").mkdir()
    assert core.find_user_scripts(tmp_path, ["Integre.bat"]) == ["A-perso.CMD", "b-perso.bat"]
    assert core.find_user_scripts(tmp_path / "absent") == []


def test_user_script_takes_title_and_first_comment(tmp_path: Path) -> None:
    (tmp_path / "Vider_cache-DNS.bat").write_bytes(
        b"@echo off\r\nsetlocal\r\n"
        b"REM Vide le cache DNS puis affiche la config r\xe9seau.\r\n"
        b"ipconfig /flushdns\r\n"
    )
    (tmp_path / "muet.cmd").write_text(":: \r\necho ok\r\n", encoding="ascii")
    script = core.user_script(tmp_path, "Vider_cache-DNS.bat")
    assert script.title == "Vider cache DNS"
    assert script.description == "Vide le cache DNS puis affiche la config réseau."
    assert (script.category, script.icon, script.admin) == (core.FAVORITES, "star", False)
    assert core.user_script(tmp_path, "muet.cmd").description == core.FAVORITE_DESCRIPTION
    assert core.user_script(tmp_path, "absent.bat").description == core.FAVORITE_DESCRIPTION


def test_favorites_setting_is_validated(tmp_path: Path) -> None:
    settings = core.Settings.from_dict({"favorites": ["a.bat", "A.BAT", "..\\b.bat", "c.ps1", 3, "d.cmd"]})
    assert settings.favorites == ["a.bat", "d.cmd"]
    path = tmp_path / "settings.json"
    core.save_settings(path, settings)
    assert core.load_settings(path).favorites == ["a.bat", "d.cmd"]


def test_scripts_folder_is_under_the_project() -> None:
    assert core.scripts_dir(PROJECT) == PROJECT / "scripts"


@pytest.mark.parametrize(
    ("value", "expected"), [(35, 35), (-5, 0), (500, core.TRANSPARENCY_MAX), (True, 0), ("40", 0)]
)
def test_transparency_setting_is_validated(value: object, expected: int) -> None:
    assert core.Settings.from_dict({"transparency": value}).transparency == expected
    assert core.Settings(transparency=expected).to_dict()["transparency"] == expected


def test_atomic_settings_save_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    core.save_settings(path, core.Settings(theme="dark"))
    core.save_settings(path, core.Settings(theme="light"))
    assert core.load_settings(path).theme == "light"
    assert [p.name for p in tmp_path.iterdir()] == ["settings.json"]


def test_script_command_survives_cmd_special_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    command = core.script_command(Path("C:/A & B (x)/a^b.bat"))
    program, _, rest = command.partition(" ")
    assert program.replace("\\", "/") == '"C:/Windows/System32/cmd.exe"'
    # cmd /c retire le premier et le dernier guillemet : le chemin reste entre guillemets.
    # cmd /c strips the first and last quote: the path stays quoted.
    assert rest.startswith('/d /c ""') and rest.endswith('a^b.bat""')


class FakeKernel32:
    def __init__(self, state: int, code: int) -> None:
        self.state, self.code, self.closed = state, code, 0

    def WaitForSingleObject(self, _handle: int, _ms: int) -> int:  # noqa: N802 - nom de l'API Windows
        return self.state

    def GetExitCodeProcess(self, _handle: int, pointer: Any) -> bool:  # noqa: N802
        pointer._obj.value = self.code
        return True

    def CloseHandle(self, _handle: int) -> bool:  # noqa: N802
        self.closed += 1
        return True


@pytest.mark.parametrize(
    ("state", "expected"),
    [(core.WAIT_TIMEOUT, None), (core.WAIT_OBJECT_0, 5), (0xFFFFFFFF, 1)],
)
def test_elevated_process_poll(monkeypatch: pytest.MonkeyPatch, state: int, expected: int | None) -> None:
    """Un handle inutilisable (WAIT_FAILED) arrête le suivi au lieu de boucler.

    An unusable handle (WAIT_FAILED) stops tracking instead of looping.
    """
    kernel32 = FakeKernel32(state, 5)
    monkeypatch.setattr(core, "_kernel32", lambda: kernel32)
    process = object.__new__(core.ElevatedProcess)
    process._handle, process._code = 42, None
    assert process.poll() == expected
    assert kernel32.closed == (0 if expected is None else 1)
    assert process.poll() == expected
    assert kernel32.closed == (0 if expected is None else 1)


# -- emplacement du dossier des scripts / scripts folder location ------------------


def test_exposed_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    downloads = tmp_path / "Telechargements"
    (downloads / "Script Manager" / "scripts").mkdir(parents=True)
    (tmp_path / "Outils" / "scripts").mkdir(parents=True)
    monkeypatch.setattr(core, "downloads_dir", lambda: downloads)
    monkeypatch.setattr(core, "drive_type", lambda _path: 3)  # DRIVE_FIXED
    assert core.exposed_location(downloads / "Script Manager" / "scripts") == "il est dans Téléchargements"
    assert core.exposed_location(tmp_path / "Outils" / "scripts") is None
    monkeypatch.setattr(core, "drive_type", lambda _path: core.DRIVE_REMOVABLE)
    assert core.exposed_location(tmp_path / "Outils" / "scripts") == "il est sur un lecteur amovible"
    monkeypatch.setattr(core, "drive_type", lambda _path: core.DRIVE_REMOTE)
    assert core.exposed_location(tmp_path / "Outils" / "scripts") == "il est sur un lecteur réseau"


def test_internet_scripts_download_from_github_and_update_safely() -> None:
    """Super God Mode se met à jour par un fichier temporaire ; WinUtil vient de GitHub et est vérifié.

    Super God Mode updates through a temporary file; WinUtil comes from GitHub and is checked.
    """
    sgm = (core.scripts_dir(PROJECT) / "Lancer-Super-God-Mode.bat").read_bytes().decode("utf-8")
    assert "$maxAgeDays = 7" in sgm and "Move-Item -LiteralPath $temporary" in sgm
    text = (core.scripts_dir(PROJECT) / "Lancer-WinUtil.bat").read_bytes().decode("utf-8")
    winutil = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(("#", "REM")))
    assert "github.com/ChrisTitusTech/winutil/releases/latest/download/winutil.ps1" in winutil
    assert "Get-AuthenticodeSignature" in winutil and "christitus.com" not in winutil
    assert "| iex" not in winutil and "Invoke-Expression" not in winutil
