"""Cœur de l'application, sans interface : manifeste, réglages, journal, lancement.

Ce module n'importe pas Qt : il est testable partout, Windows ou non.

Application core, without interface: manifest, settings, log, launching.

This module does not import Qt: it can be tested anywhere, Windows or not.
"""

from __future__ import annotations

import ctypes
import functools
import json
import logging
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Protocol

from .i18n import LANGUAGES, N_, language, tr

APP_NAME = "Script Manager"
MANIFEST_NAME = "scripts.json"
# sous-dossier des scripts, à côté de scripts.json
# scripts subfolder, next to scripts.json
SCRIPTS_FOLDER = "scripts"
SCRIPT_SUFFIXES = (".bat", ".cmd")
IS_WINDOWS = sys.platform == "win32"

CATEGORIES = ("bureau", "registre", "systeme", "en_ligne", "autres")
ICONS = (
    "power",
    "desktop",
    "sparkle",
    "undo",
    "key",
    "grid",
    "toolbox",
    "globe",
    "folder",
    "window",
    "shield",
    "settings",
    "terminal",
    "delete",
    "star",
)

# Paire de scripts présentée comme un seul interrupteur dans l'interface.
# Pair of scripts shown as a single switch in the interface.
ARROWS_ON = "Supprimer-fleche-raccourci.bat"
ARROWS_OFF = "Restaurer-fleche-raccourci.bat"

log = logging.getLogger("scripts_windows")


# --------------------------------------------------------------------------
# Emplacements / Locations
# --------------------------------------------------------------------------


def find_app_dir() -> Path:
    """Dossier qui contient scripts.json et les scripts.

    Avec un build PyInstaller « onedir », l'EXE est dans
    ``dist\\Script-Manager\\`` : on remonte alors jusqu'au
    dossier du projet, celui qui contient scripts.json.

    Folder that contains scripts.json and the scripts.

    With a PyInstaller "onedir" build, the EXE is in
    ``dist\\Script-Manager\\``: we then climb up to the
    project folder, the one that contains scripts.json.
    """
    if getattr(sys, "frozen", False):
        start = Path(sys.executable).resolve().parent
    else:
        start = Path(__file__).resolve().parent.parent
    for candidate in (start, *start.parents[:3]):
        if (candidate / MANIFEST_NAME).is_file():
            return candidate
    return start


def scripts_dir(app_dir: Path) -> Path:
    """Dossier des scripts .bat (et des favoris) : « scripts » à la racine du projet.

    Folder of the .bat scripts (and favorites): "scripts" at the project root.
    """
    return app_dir / SCRIPTS_FOLDER


def resource_path(relative: str) -> Path:
    """Fichier embarqué par PyInstaller (_internal) ou présent dans le projet.

    File bundled by PyInstaller (_internal) or present in the project.
    """
    bundle = getattr(sys, "_MEIPASS", None)
    return (Path(bundle) if bundle else Path(__file__).resolve().parent.parent) / relative


def data_dir() -> Path:
    """Dossier des réglages et du journal (%LOCALAPPDATA%\\Scripts-Windows).

    Folder for settings and the log (%LOCALAPPDATA%\\Scripts-Windows).
    """
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "Scripts-Windows"


# --------------------------------------------------------------------------
# Manifeste des scripts / Scripts manifest
# --------------------------------------------------------------------------


class ManifestError(ValueError):
    """scripts.json absent ou mal formé.

    scripts.json missing or malformed.
    """


@dataclass(frozen=True)
class Script:
    title: str
    filename: str
    description: str
    admin: bool = False
    registry: bool = False
    internet: bool = False
    category: str = "autres"
    icon: str = "window"
    # False : jamais de point de restauration automatique avant ce script.
    # False: never an automatic restore point before this script.
    restore_point: bool = True

    @property
    def badges(self) -> list[str]:
        labels = (
            (self.admin, tr("Administrateur")),
            (self.registry, tr("Registre")),
            (self.internet, "Internet"),
        )
        return [label for enabled, label in labels if enabled]


# Champs facultatifs « title_en » et « description_en » : texte affiché quand l'interface est en anglais.
# Optional "title_en" and "description_en" fields: text shown when the interface is in English.
TRANSLATED = ("title", "description")
FIELDS = frozenset(
    (
        "title",
        "filename",
        "description",
        "admin",
        "registry",
        "internet",
        "category",
        "icon",
        "restore_point",
        *(f"{key}_en" for key in TRANSLATED),
    )
)


def is_plain_name(name: str) -> bool:
    """Simple nom de fichier, sans dossier ni lecteur : il désigne un fichier du dossier des scripts.

    Plain file name, without a folder or drive: it refers to a file in the scripts folder.
    """
    return not any(char in name for char in "/\\:") and name.strip(". ") != ""


def localized(entry: dict[str, Any], key: str) -> str:
    """Texte de ``key`` dans la langue de l'interface (le français si la traduction manque).

    Text of ``key`` in the interface language (French if the translation is missing).
    """
    if language() == "en" and isinstance(entry.get(f"{key}_en"), str):
        return str(entry[f"{key}_en"])
    return str(entry[key])


def parse_scripts(data: Any) -> list[Script]:
    """Valide le contenu de scripts.json et le convertit en objets Script.

    Validates the content of scripts.json and converts it into Script objects.
    """
    if not isinstance(data, dict) or not isinstance(data.get("scripts"), list):
        raise ManifestError(tr("le fichier doit contenir un objet avec une liste « scripts »."))
    scripts: list[Script] = []
    seen: set[str] = set()
    for number, entry in enumerate(data["scripts"], start=1):
        where = tr("script n° {number}", number=number)
        if not isinstance(entry, dict):
            raise ManifestError(tr("{where} : un objet est attendu.", where=where))
        unknown = set(entry) - FIELDS
        if unknown:
            raise ManifestError(
                tr("{where} : champ inconnu {names}.", where=where, names=", ".join(sorted(unknown)))
            )
        optional_texts = [f"{name}_en" for name in TRANSLATED if f"{name}_en" in entry]
        for key in ("title", "filename", "description", *optional_texts):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ManifestError(
                    tr("{where} : « {key} » doit être un texte non vide.", where=where, key=key)
                )
        for key in ("admin", "registry", "internet", "restore_point"):
            if key in entry and not isinstance(entry[key], bool):
                raise ManifestError(
                    tr("{where} : « {key} » doit valoir true ou false.", where=where, key=key)
                )
        for key, default, allowed in (("category", "autres", CATEGORIES), ("icon", "window", ICONS)):
            if entry.get(key, default) not in allowed:
                raise ManifestError(
                    tr(
                        "{where} : « {key} » doit valoir {values}.",
                        where=where,
                        key=key,
                        values=", ".join(allowed),
                    )
                )
        filename = entry["filename"]
        folded = filename.lower()
        if not is_plain_name(filename):
            raise ManifestError(
                tr(
                    "{where} : « {filename} » doit être un nom de fichier, sans dossier.",
                    where=where,
                    filename=filename,
                )
            )
        if not folded.endswith(SCRIPT_SUFFIXES):
            raise ManifestError(
                tr(
                    "{where} : « {filename} » doit être un fichier .bat ou .cmd.",
                    where=where,
                    filename=filename,
                )
            )
        if folded in seen:
            raise ManifestError(
                tr("{where} : « {filename} » apparaît deux fois.", where=where, filename=filename)
            )
        seen.add(folded)
        scripts.append(
            Script(
                title=localized(entry, "title"),
                filename=filename,
                description=localized(entry, "description"),
                admin=entry.get("admin", False),
                registry=entry.get("registry", False),
                internet=entry.get("internet", False),
                category=entry.get("category", "autres"),
                icon=entry.get("icon", "window"),
                restore_point=entry.get("restore_point", True),
            )
        )
    if not scripts:
        raise ManifestError(tr("la liste « scripts » est vide."))
    return scripts


# --------------------------------------------------------------------------
# Favoris : scripts personnels du dossier des scripts, hors scripts.json
# Favorites: personal scripts from the scripts folder, outside scripts.json
# --------------------------------------------------------------------------

FAVORITES = "favoris"
# Outils et scripts d'appoint du projet, jamais proposés en favori (noms en minuscules).
# Project tools and helper scripts, never offered as favorites (lowercase names).
NOT_FAVORITES = frozenset({"build.bat", "creer-point-restauration.bat", "animations-windows.bat"})
FAVORITE_DESCRIPTION = N_("Script personnel, ajouté depuis le dossier des scripts.")


def is_script_name(name: str) -> bool:
    """Simple nom de fichier .bat ou .cmd, sans dossier (même règle que scripts.json).

    Plain .bat or .cmd file name, without a folder (same rule as scripts.json).
    """
    return is_plain_name(name) and name.lower().endswith(SCRIPT_SUFFIXES)


def find_user_scripts(folder: Path, exclude: Iterable[str] = ()) -> list[str]:
    """Scripts .bat/.cmd du dossier qui ne sont ni intégrés, ni déjà exclus.

    .bat/.cmd scripts in the folder that are neither built in nor already excluded.
    """
    taken = {name.lower() for name in exclude} | NOT_FAVORITES
    try:
        names = [
            entry.name
            for entry in folder.iterdir()
            if entry.is_file() and is_script_name(entry.name) and entry.name.lower() not in taken
        ]
    except OSError:
        return []
    return sorted(names, key=str.lower)


def read_script_comment(path: Path) -> str:
    """Premier commentaire (REM ou ::) en tête d'un script, s'il y en a un.

    First comment (REM or ::) at the top of a script, if there is one.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(4096).decode("cp1252", errors="replace")
    except OSError:
        return ""
    for raw in head.splitlines()[:15]:
        line = raw.strip()
        if line.lower().startswith("rem ") or line.lower() == "rem":
            text = line[3:].strip()
        elif line.startswith("::"):
            text = line[2:].strip()
        else:
            continue
        if text:
            return text[:160]
    return ""


def user_script(folder: Path, filename: str) -> Script:
    """Carte d'un favori : titre tiré du nom, description tirée du premier commentaire.

    Card for a favorite: title taken from the name, description from the first comment.
    """
    stem = Path(filename).stem.replace("-", " ").replace("_", " ").strip() or filename
    description = read_script_comment(folder / filename) or tr(FAVORITE_DESCRIPTION)
    return Script(stem, filename, description, category=FAVORITES, icon="star", restore_point=True)


def load_scripts(path: Path) -> list[Script]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ManifestError(tr("lecture impossible ({error}).", error=exc.strerror or exc)) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            tr("JSON invalide, ligne {line} colonne {column}.", line=exc.lineno, column=exc.colno)
        ) from exc
    return parse_scripts(data)


# --------------------------------------------------------------------------
# Réglages / Settings
# --------------------------------------------------------------------------

THEME_MODES = ("light", "dark", "system")
ACCENTS = ("#0067C0", "#8764B8", "#107C10", "#CA5010", "#C30052", "#038387")
# Transparence des surfaces, en pourcentage (au-delà, le texte devient difficile à lire).
# Surface transparency, as a percentage (beyond it, text becomes hard to read).
TRANSPARENCY_MAX = 70
# Fond flouté (Mica, Acrylic) disponible à partir de Windows 11.
# Blurred background (Mica, Acrylic) available from Windows 11.
BACKDROP_BUILD = 22000


@dataclass
class Settings:
    theme: str = "system"
    accent: str = ACCENTS[0]
    mica: bool = False
    transparency: int = 0
    # Langue de l'interface : system (comme Windows), fr ou en.
    # Interface language: system (same as Windows), fr or en.
    language: str = "system"
    # Point de restauration avant les scripts qui modifient le système.
    # Restore point before the scripts that change the system.
    restore_point: bool = False
    # Scripts personnels mis en favori (noms de fichiers du dossier des scripts).
    # Personal scripts marked as favorites (file names in the scripts folder).
    favorites: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        settings = cls()
        if data.get("theme") in THEME_MODES:
            settings.theme = data["theme"]
        accent = data.get("accent")
        if isinstance(accent, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent):
            settings.accent = accent
        if isinstance(data.get("mica"), bool):
            settings.mica = data["mica"]
        if data.get("language") in LANGUAGES:
            settings.language = data["language"]
        transparency = data.get("transparency")
        if isinstance(transparency, int) and not isinstance(transparency, bool):
            settings.transparency = min(max(transparency, 0), TRANSPARENCY_MAX)
        if isinstance(data.get("restore_point"), bool):
            settings.restore_point = data["restore_point"]
        favorites = data.get("favorites")
        if isinstance(favorites, list):
            seen: set[str] = set()
            for name in favorites:
                if isinstance(name, str) and is_script_name(name) and name.lower() not in seen:
                    seen.add(name.lower())
                    settings.favorites.append(name)
        return settings

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "accent": self.accent,
            "mica": self.mica,
            "transparency": self.transparency,
            "language": self.language,
            "restore_point": self.restore_point,
            "favorites": list(self.favorites),
        }


def load_settings(path: Path) -> Settings:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    return Settings.from_dict(data if isinstance(data, dict) else {})


def save_settings(path: Path, settings: Settings) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Fichier temporaire puis remplacement : une coupure en pleine écriture ne perd pas les réglages.
        # Temporary file then replacement: an interruption mid-write does not lose the settings.
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        log.warning(tr("Réglages non enregistrés dans %s"), path, exc_info=True)


# --------------------------------------------------------------------------
# Journal / Log
# --------------------------------------------------------------------------

LOG_NAME = "launcher.log"
JOURNAL_LIMIT = 120  # lignes affichées par la page Journal / lines shown by the Log page
# Une ligne du journal fait moins de 200 octets : on ne lit que la fin du fichier.
# A log line is under 200 bytes: only the end of the file is read.
_TAIL_BYTES = JOURNAL_LIMIT * 512
LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \w+ (.*)$")


def setup_logging(directory: Path) -> Path | None:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        log_file = directory / LOG_NAME
        handler = RotatingFileHandler(log_file, maxBytes=256_000, backupCount=2, encoding="utf-8")
    except OSError:
        log.addHandler(logging.NullHandler())
        return None
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log_file


@dataclass
class Entry:
    when: datetime
    kind: str  # success | critical | caution | info
    text: str


# Mots du journal, en français et en anglais : launcher.log garde les lignes écrites dans
# l'une ou l'autre langue.
# Log words, in French and English: launcher.log keeps the lines written in
# either language.
SUCCESS_WORDS = ("terminé", "finished")
SUCCESS_ENDINGS = (": créé", ": created")
CRITICAL_WORDS = ("échec", "impossible", "désactivée", "failed", "disabled")
CAUTION_WORDS = ("refusée", "fermée", "denied", "closed")


def classify(text: str) -> str:
    if any(word in text for word in SUCCESS_WORDS) or text.endswith(SUCCESS_ENDINGS):
        return "success"
    if any(word in text for word in CRITICAL_WORDS):
        return "critical"
    if any(word in text for word in CAUTION_WORDS):
        return "caution"
    return "info"


def read_journal(directory: Path, limit: int = JOURNAL_LIMIT) -> list[Entry]:
    """Derniers lancements de launcher.log, le plus récent en premier.

    Seule la fin du fichier est lue (le journal tournant peut atteindre 256 Ko).

    Latest runs from launcher.log, most recent first.

    Only the end of the file is read (the rotating log can reach 256 KB).
    """
    try:
        with (directory / LOG_NAME).open("rb") as handle:
            start = max(0, handle.seek(0, os.SEEK_END) - _TAIL_BYTES)
            handle.seek(start)
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    if start:
        # première ligne coupée par la lecture partielle
        # first line cut by the partial read
        lines = lines[1:]
    entries: list[Entry] = []
    for line in reversed(lines):
        match = LOG_LINE.match(line)
        if match:
            text = match.group(2)
            entries.append(Entry(datetime.fromisoformat(match.group(1)), classify(text), text))
            if len(entries) == limit:
                break
    return entries


# --------------------------------------------------------------------------
# Windows / Windows
# --------------------------------------------------------------------------

ERROR_CANCELLED = 1223
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NOASYNC = 0x00000100
SW_SHOWNORMAL = 1
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
CREATE_NEW_CONSOLE = 0x00000010
# Code de sortie d'une console fermée par sa croix (ou Ctrl+C) au lieu d'une touche.
# Exit code of a console closed with its X button (or Ctrl+C) instead of a key.
STATUS_CONTROL_C_EXIT = 0xC000013A


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def windows_build() -> int:
    if not IS_WINDOWS:
        return 0
    try:
        return int(sys.getwindowsversion().build)
    except AttributeError:
        return 0


def shell_execute_ex(verb: str, file: str, parameters: str, directory: str) -> int:
    """ShellExecuteExW. Renvoie le handle du processus lancé.

    Lève OSError en cas d'échec ; ``winerror == ERROR_CANCELLED`` quand
    l'utilisateur refuse la demande d'élévation (UAC).

    ShellExecuteExW. Returns the handle of the launched process.

    Raises OSError on failure; ``winerror == ERROR_CANCELLED`` when
    the user declines the elevation prompt (UAC).
    """
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    info.lpVerb = verb
    info.lpFile = file
    info.lpParameters = parameters or None
    info.lpDirectory = directory
    info.nShow = SW_SHOWNORMAL
    if not _shell32().ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(info.hProcess or 0)


# Bibliothèques chargées une seule fois, avec des prototypes déclarés : les
# handles 64 bits passent sans troncature et ctypes.windll reste intact.
# Libraries loaded once, with declared prototypes: 64-bit
# handles pass without truncation and ctypes.windll stays untouched.
@functools.cache
def _shell32() -> Any:
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    return shell32


@functools.cache
def _kernel32() -> Any:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetDriveTypeW.restype = wintypes.UINT
    return kernel32


class MARGINS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int) for name in ("left", "right", "top", "bottom")]


@functools.cache
def _dwmapi() -> Any:
    dwmapi = ctypes.WinDLL("dwmapi")
    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
    dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]
    dwmapi.DwmExtendFrameIntoClientArea.restype = ctypes.c_long
    return dwmapi


def set_window_attribute(hwnd: int, attribute: int, value: int) -> bool:
    """DwmSetWindowAttribute avec un entier. True si Windows accepte l'attribut.

    DwmSetWindowAttribute with an integer. True if Windows accepts the attribute.
    """
    data = ctypes.c_int(value)
    return int(_dwmapi().DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))) == 0


def extend_frame(hwnd: int) -> None:
    """Étend le cadre à toute la fenêtre : le fond système (Mica, Acrylic) apparaît derrière.

    Extends the frame to the whole window: the system backdrop (Mica, Acrylic) shows behind it.
    """
    _dwmapi().DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(-1, -1, -1, -1)))


def close_handle(handle: int) -> None:
    if handle:
        _kernel32().CloseHandle(handle)


def is_cancelled(exc: OSError) -> bool:
    return getattr(exc, "winerror", None) == ERROR_CANCELLED


class RunningScript(Protocol):
    def poll(self) -> int | None: ...


def script_command(path: Path) -> str:
    """Ligne de commande qui lance un .bat dans cmd.exe.

    ``/d`` ignore l'AutoRun de cmd ; la ligne est entourée de guillemets car ``cmd /c`` retire le premier
    et le dernier : un chemin qui contient « & », « ^ » ou des parenthèses reste intact.

    Command line that runs a .bat in cmd.exe.

    ``/d`` skips cmd's AutoRun; the line is wrapped in quotes because ``cmd /c`` strips the first
    and the last one: a path that contains "&", "^" or parentheses stays intact.
    """
    return f'"{cmd_exe()}" /d /c ""{path}""'


class PopenScript:
    """Script lancé avec les droits actuels de l'application.

    Script run with the application's current rights.
    """

    def __init__(self, path: Path) -> None:
        # Sous Windows, une chaîne est transmise telle quelle (pas de guillemets ajoutés par Python).
        # On Windows, a string is passed as is (no quotes added by Python).
        self._process = subprocess.Popen(
            script_command(path),
            cwd=str(path.parent),
            creationflags=CREATE_NEW_CONSOLE,
        )

    def poll(self) -> int | None:
        return self._process.poll()


class ElevatedProcess:
    """Programme lancé en administrateur : on suit son processus par son handle.

    Program run as administrator: its process is tracked through its handle.
    """

    def __init__(self, file: str, parameters: str, directory: str) -> None:
        self._handle = shell_execute_ex("runas", file, parameters, directory)
        self._code: int | None = None if self._handle else 0

    def poll(self) -> int | None:
        if self._code is not None:
            return self._code
        kernel32 = _kernel32()
        state = kernel32.WaitForSingleObject(self._handle, 0)
        if state == WAIT_TIMEOUT:
            return None
        # Processus terminé, ou handle inutilisable (WAIT_FAILED) : le suivi s'arrête dans les deux cas.
        # Process finished, or unusable handle (WAIT_FAILED): tracking stops in both cases.
        code = wintypes.DWORD(1)
        if state == WAIT_OBJECT_0 and not kernel32.GetExitCodeProcess(self._handle, ctypes.byref(code)):
            code.value = 1
        close_handle(self._handle)
        self._code = int(code.value)
        return self._code


def start_script(path: Path, elevate: bool) -> RunningScript:
    """Lance un .bat depuis son propre dossier, en administrateur si ``elevate``.

    Runs a .bat from its own folder, as administrator if ``elevate``.
    """
    if elevate:
        return ElevatedProcess(str(path), "", str(path.parent))
    return PopenScript(path)


# --------------------------------------------------------------------------
# Points de restauration / Restore points
# --------------------------------------------------------------------------

RESTORE_SCRIPT = "Creer-point-restauration.bat"
RESTORE_CLEANUP = "Supprimer-anciens-points-restauration.bat"
RESTORE_LABEL = N_("Point de restauration")
# Codes de sortie de Creer-point-restauration.bat
# Exit codes of Creer-point-restauration.bat
RESTORE_CREATED, RESTORE_FAILED, RESTORE_RECENT, RESTORE_DISABLED = 0, 1, 2, 3


def needs_restore_point(script: Script) -> bool:
    """Scripts concernés par le point de restauration automatique.

    Scripts affected by the automatic restore point.
    """
    return script.restore_point and (script.admin or script.registry)


def system32() -> Path:
    """Dossier System32, par chemin complet (pas de recherche dans le PATH).

    System32 folder, by full path (no PATH lookup).
    """
    return Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"


def cmd_exe() -> str:
    """Interpréteur de commandes, par chemin complet (pas de recherche dans le PATH).

    Command interpreter, by full path (no PATH lookup).
    """
    return str(system32() / "cmd.exe")


def restore_point_command(folder: Path, description: str) -> tuple[str, str]:
    """(programme, paramètres) qui créent le point de restauration.

    Le .bat est lancé par cmd.exe ; la description est nettoyée des caractères que cmd interpréterait.

    (program, parameters) that create the restore point.

    The .bat is run by cmd.exe; the description is stripped of the characters cmd would interpret.
    """
    clean = "".join(char for char in description[:200] if char not in '"%^!\r\n')
    # cmd /c retire le premier et le dernier guillemet de la ligne : on met donc la ligne entre guillemets.
    # cmd /c strips the first and last quote of the line: the whole line is therefore quoted.
    parameters = f'/d /c ""{folder / RESTORE_SCRIPT}" "{clean}""'
    return cmd_exe(), parameters


def start_restore_point(folder: Path, description: str) -> RunningScript:
    """Crée un point de restauration en administrateur (demande UAC si besoin).

    ``folder`` est le dossier des scripts, qui contient Creer-point-restauration.bat.

    Creates a restore point as administrator (UAC prompt if needed).

    ``folder`` is the scripts folder, which contains Creer-point-restauration.bat.
    """
    program, parameters = restore_point_command(folder, description)
    return ElevatedProcess(program, parameters, str(folder))


def describe_restore(code: int) -> tuple[str, str]:
    """(gravité, texte) pour le code de sortie de Creer-point-restauration.bat.

    (severity, text) for the exit code of Creer-point-restauration.bat.
    """
    if code == RESTORE_CREATED:
        return "success", tr("créé")
    if code == RESTORE_RECENT:
        return "caution", tr("un point de moins de 24 h existe déjà, Windows n’en crée pas d’autre")
    if code == RESTORE_DISABLED:
        return "critical", tr("protection du système désactivée")
    if code == STATUS_CONTROL_C_EXIT:
        return "caution", tr("fenêtre fermée avant la fin")
    return "critical", tr("échec (code {code})", code=code)


def restore_allows_launch(code: int) -> bool:
    """Un point vient d'être créé, ou un point récent protège déjà le PC.

    A point was just created, or a recent point already protects the PC.
    """
    return code in (RESTORE_CREATED, RESTORE_RECENT)


def describe_exit(code: int) -> tuple[str, str]:
    """(gravité, texte) pour le code de sortie d'un script.

    (severity, text) for the exit code of a script.
    """
    if code == 0:
        return "success", tr("terminé (code 0)")
    if code == STATUS_CONTROL_C_EXIT:
        return "caution", tr("fenêtre fermée par l'utilisateur")
    return "critical", tr("échec (code {code})", code=code)


def relaunch_as_admin() -> None:
    """Relance l'application en administrateur. Lève OSError si refusé.

    Restarts the application as administrator. Raises OSError if declined.
    """
    if getattr(sys, "frozen", False):
        parameters = ""
    else:
        parameters = subprocess.list2cmdline([str(Path(sys.argv[0]).resolve())])
    close_handle(shell_execute_ex("runas", sys.executable, parameters, str(find_app_dir())))


def read_registry(root: str, key_path: str, name: str) -> object | None:
    """Valeur du Registre, en lecture seule ; None si absente ou hors Windows.

    ``root`` est le nom d'une ruche de winreg, par exemple ``"HKEY_CURRENT_USER"``.

    Registry value, read-only; None if missing or outside Windows.

    ``root`` is the name of a winreg hive, for example ``"HKEY_CURRENT_USER"``.
    """
    if not IS_WINDOWS:
        return None
    try:
        import winreg

        with winreg.OpenKey(getattr(winreg, root), key_path) as key:
            value: object = winreg.QueryValueEx(key, name)[0]
    except (ImportError, AttributeError, OSError):
        return None
    return value


# Dossier Téléchargements (GUID du dossier connu) et types de lecteurs de GetDriveTypeW.
# Downloads folder (known folder GUID) and drive types from GetDriveTypeW.
USER_SHELL_FOLDERS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"
DRIVE_REMOVABLE, DRIVE_REMOTE = 2, 4


def downloads_dir() -> Path:
    """Dossier Téléchargements, même déplacé par l'utilisateur.

    Downloads folder, even when the user moved it.
    """
    value = read_registry("HKEY_CURRENT_USER", USER_SHELL_FOLDERS_KEY, DOWNLOADS_GUID)
    if isinstance(value, str) and value.strip():
        return Path(os.path.expandvars(value))
    return Path.home() / "Downloads"


def drive_type(path: Path) -> int:
    """Type du lecteur (GetDriveTypeW) ; 0 hors Windows ou si inconnu.

    Drive type (GetDriveTypeW); 0 outside Windows or if unknown.
    """
    if not IS_WINDOWS or not path.anchor:
        return 0
    try:
        return int(_kernel32().GetDriveTypeW(path.anchor))
    except (AttributeError, OSError):
        return 0


def exposed_location(folder: Path) -> str | None:
    """Raison pour laquelle le dossier des scripts est exposé, ou None.

    Les scripts administrateur sont lancés depuis ce dossier : dans Téléchargements, sur une clé USB
    ou sur un partage réseau, d'autres programmes ou d'autres personnes peuvent les modifier.

    Reason why the scripts folder is exposed, or None.

    Administrator scripts are run from this folder: in Downloads, on a USB drive or on a network
    share, other programs or other people can change them.
    """
    resolved = folder.resolve()
    downloads = downloads_dir().resolve()
    if resolved == downloads or downloads in resolved.parents:
        return tr("il est dans Téléchargements")
    kind = drive_type(resolved)
    if kind == DRIVE_REMOVABLE:
        return tr("il est sur un lecteur amovible")
    if kind == DRIVE_REMOTE or str(resolved).startswith("\\\\"):
        return tr("il est sur un lecteur réseau")
    return None


SHELL_ICONS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"
PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def arrows_hidden() -> bool:
    """Les flèches des raccourcis sont-elles masquées (valeur 29 de Shell Icons) ?

    Are the shortcut arrows hidden (value 29 of Shell Icons)?
    """
    value = str(read_registry("HKEY_LOCAL_MACHINE", SHELL_ICONS_KEY, "29") or "")
    return "NoArrow" in value or "shell32.dll,-50" in value


def system_prefers_dark_registry() -> bool:
    """Réglage « Mode d'application » de Windows, pour les Qt sans colorScheme().

    Windows "app mode" setting, for Qt versions without colorScheme().
    """
    return read_registry("HKEY_CURRENT_USER", PERSONALIZE_KEY, "AppsUseLightTheme") == 0
