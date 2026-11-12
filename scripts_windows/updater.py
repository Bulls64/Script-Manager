"""Mises à jour depuis les releases GitHub du projet (sans Qt).

La dernière release publiée est lue par l'API GitHub. Pour l'application construite et
décompressée depuis une release (l'EXE à côté de scripts.json), la nouvelle archive est
téléchargée, vérifiée par son empreinte SHA-256 et décompressée dans un dossier temporaire.
Un script PowerShell attend ensuite la fermeture de l'application, copie les nouveaux
fichiers par-dessus et la relance. Les scripts personnels (favoris) et les entrées ajoutées
à scripts.json sont conservés.

Updates from the project's GitHub releases (no Qt).

The latest published release is read through the GitHub API. For the app built and
extracted from a release (the EXE next to scripts.json), the new archive is downloaded,
checked against its SHA-256 hash and extracted to a temporary folder. A PowerShell script
then waits for the app to close, copies the new files over it and starts it again. Personal
scripts (favorites) and the entries added to scripts.json are kept.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .core import MANIFEST_NAME, system32
from .i18n import tr

REPOSITORY = "Bulls64/Script-Manager"
LATEST_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases/latest"
APP_FOLDER = "Script-Manager"
EXE_NAME = "Script-Manager.exe"
TIMEOUT = 15
# Taille maximale acceptée pour l'archive (garde-fou contre une réponse inattendue).
# Maximum accepted archive size (safeguard against an unexpected response).
MAX_DOWNLOAD = 300 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


class UpdateError(Exception):
    """Échec de la vérification ou du téléchargement, avec un message pour l'utilisateur.

    Check or download failure, with a message for the user.
    """


@dataclass(frozen=True)
class Release:
    version: str
    page_url: str
    zip_url: str | None
    sha256_url: str | None


def parse_version(text: str) -> tuple[int, ...] | None:
    """« v2.17.0 » -> (2, 17, 0) ; None si le texte n'est pas une version.

    "v2.17.0" -> (2, 17, 0); None if the text is not a version.
    """
    match = re.fullmatch(r"v?(\d+(?:\.\d+){0,3})", text.strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(candidate: str, current: str = __version__) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    if new is None or old is None:
        return False
    width = max(len(new), len(old))
    return new + (0,) * (width - len(new)) > old + (0,) * (width - len(old))


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Script-Manager/{__version__}",
        },
    )


def _https_only(url: str) -> str:
    if not url.startswith("https://"):
        raise UpdateError(tr("Adresse de téléchargement refusée : {url}", url=url))
    return url


# Architectures publiées : x64 garde le nom d'archive historique (lu par les versions 2.18-2.19).
# Published architectures: x64 keeps the historical archive name (read by versions 2.18-2.19).
ARCHITECTURES = ("x64", "arm64")
ARCH_LABELS = {"x64": "x64", "arm64": "ARM64"}
IMAGE_FILE_MACHINE_ARM64 = 0xAA64


def build_arch() -> str:
    """Architecture de l'interpréteur en cours : celle de l'EXE.

    Architecture of the running interpreter: the one of the EXE.
    """
    return "arm64" if sysconfig.get_platform().endswith("arm64") else "x64"


def host_arch() -> str:
    """Architecture du processeur, même quand l'appli x64 tourne en émulation sur ARM64.

    Processor architecture, even when the x64 app runs emulated on ARM64.
    """
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            check = kernel32.IsWow64Process2  # Windows 10 1709+
            check.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.USHORT),
                ctypes.POINTER(wintypes.USHORT),
            ]
            check.restype = wintypes.BOOL
            process, native = wintypes.USHORT(), wintypes.USHORT()
            if check(kernel32.GetCurrentProcess(), ctypes.byref(process), ctypes.byref(native)):
                return "arm64" if native.value == IMAGE_FILE_MACHINE_ARM64 else "x64"
        except (AttributeError, OSError):
            pass
    return build_arch()


def asset_name(version: str, arch: str) -> str:
    suffix = "" if arch == "x64" else f"-{arch}"
    return f"{APP_FOLDER}-{version}{suffix}.zip"


def parse_release(data: dict[str, Any], arch: str | None = None) -> Release:
    """Release GitHub ; l'archive de ``arch`` (par défaut celle du processeur), sinon celle en x64.

    GitHub release; the archive for ``arch`` (by default the processor one), otherwise the x64 one.
    """
    tag = data.get("tag_name")
    if not isinstance(tag, str) or parse_version(tag) is None:
        raise UpdateError(tr("Réponse de GitHub inattendue."))
    version = tag.lstrip("v")
    urls: dict[str, str] = {}
    for asset in data.get("assets") or []:
        name, url = asset.get("name"), asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(url, str) and name.startswith(f"{APP_FOLDER}-"):
            urls[name] = url
    zip_url = sha_url = None
    wanted = arch or host_arch()
    # ARM64 sans archive dédiée (anciennes releases) : la version x64 tourne en émulation.
    # ARM64 without its own archive (older releases): the x64 version runs emulated.
    for candidate in dict.fromkeys((wanted, "x64")):
        name = asset_name(version, candidate)
        if name in urls and f"{name}.sha256" in urls:
            zip_url, sha_url = _https_only(urls[name]), _https_only(urls[f"{name}.sha256"])
            break
    page = data.get("html_url")
    return Release(version, page if isinstance(page, str) else RELEASES_PAGE, zip_url, sha_url)


def fetch_latest(timeout: float = TIMEOUT) -> Release:
    """Dernière release publiée (hors brouillons et préversions).

    Latest published release (drafts and pre-releases excluded).
    """
    try:
        with urllib.request.urlopen(_request(LATEST_API), timeout=timeout) as response:
            data = json.loads(response.read(1024 * 1024).decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise UpdateError(tr("Impossible de joindre GitHub ({error}).", error=exc)) from exc
    if not isinstance(data, dict):
        raise UpdateError(tr("Réponse de GitHub inattendue."))
    return parse_release(data)


def can_self_update(app_dir: Path) -> bool:
    """Vrai pour l'EXE décompressé d'une release : il est dans le même dossier que scripts.json.

    Depuis les sources (git clone) ou un build local (dist\\…), la mise à jour se fait à la main.

    True for the EXE extracted from a release: it sits in the same folder as scripts.json.

    From the sources (git clone) or a local build (dist\\…), updating is done by hand.
    """
    if not getattr(sys, "frozen", False):
        return False
    return Path(sys.executable).resolve().parent == app_dir.resolve()


def folder_is_writable(folder: Path) -> bool:
    probe = folder / ".script-manager-write-test"
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError:
        return False
    return True


def download(url: str, destination: Path, limit: int = MAX_DOWNLOAD) -> None:
    try:
        with (
            urllib.request.urlopen(_request(_https_only(url)), timeout=TIMEOUT) as response,
            destination.open("wb") as file,
        ):
            total = 0
            while chunk := response.read(1024 * 256):
                total += len(chunk)
                if total > limit:
                    raise UpdateError(tr("Archive trop volumineuse."))
                file.write(chunk)
    except OSError as exc:
        raise UpdateError(tr("Téléchargement impossible ({error}).", error=exc)) from exc


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    """Décompresse en refusant tout chemin qui sortirait du dossier de destination.

    Extracts while refusing any path that would leave the destination folder.
    """
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (root / member.filename).resolve()
            if target != root and root not in target.parents:
                raise UpdateError(tr("Archive refusée : chemin invalide ({name}).", name=member.filename))
        zipped.extractall(root)


def merge_manifest(old: Path, new: Path, scripts_folder: Path) -> int:
    """Ajoute au nouveau scripts.json les entrées ajoutées par l'utilisateur à l'ancien.

    Une entrée est gardée si son script n'est pas fourni par la nouvelle version et si le
    fichier existe toujours dans le dossier des scripts. Renvoie le nombre d'entrées gardées.

    Adds to the new scripts.json the entries the user added to the old one.

    An entry is kept if its script is not shipped by the new version and if the file still
    exists in the scripts folder. Returns the number of kept entries.
    """
    try:
        old_data = json.loads(old.read_text(encoding="utf-8"))
        new_data = json.loads(new.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    old_entries, new_entries = old_data.get("scripts"), new_data.get("scripts")
    if not isinstance(old_entries, list) or not isinstance(new_entries, list):
        return 0
    shipped = {e.get("filename", "").lower() for e in new_entries if isinstance(e, dict)}
    kept = [
        entry
        for entry in old_entries
        if isinstance(entry, dict)
        and isinstance(entry.get("filename"), str)
        and entry["filename"].lower() not in shipped
        and (scripts_folder / entry["filename"]).is_file()
    ]
    if kept:
        new_data["scripts"] = new_entries + kept
        new.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(kept)


def prepare(release: Release, app_dir: Path, work_dir: Path) -> Path:
    """Télécharge, vérifie et décompresse la release ; renvoie le dossier des nouveaux fichiers.

    Downloads, checks and extracts the release; returns the folder of the new files.
    """
    if release.zip_url is None or release.sha256_url is None:
        raise UpdateError(tr("Cette release ne contient pas d’archive à installer."))
    work_dir.mkdir(parents=True, exist_ok=True)
    archive = work_dir / f"{APP_FOLDER}-{release.version}.zip"
    checksum = work_dir / f"{archive.name}.sha256"
    download(release.zip_url, archive)
    download(release.sha256_url, checksum, limit=4096)
    expected = checksum.read_text(encoding="ascii", errors="replace").split()[:1]
    if not expected or expected[0].lower() != sha256_of(archive):
        raise UpdateError(tr("Empreinte SHA-256 incorrecte : l’archive n’est pas installée."))
    extracted = work_dir / "extracted"
    if extracted.exists():
        shutil.rmtree(extracted)
    safe_extract(archive, extracted)
    source = extracted / APP_FOLDER
    if not (source / EXE_NAME).is_file() or not (source / MANIFEST_NAME).is_file():
        raise UpdateError(
            tr("Archive incomplète : {name} ou {manifest} manque.", name=EXE_NAME, manifest=MANIFEST_NAME)
        )
    merge_manifest(app_dir / MANIFEST_NAME, source / MANIFEST_NAME, app_dir / "scripts")
    return source


def _ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def apply_script(source: Path, target: Path, pid: int, work_dir: Path, log: Path) -> str:
    """Script PowerShell qui remplace les fichiers une fois l'application fermée, puis la relance.

    ``_internal`` (Python et Qt) est mis en miroir ; le reste est copié sans rien supprimer, pour
    garder les scripts personnels. En cas d'échec, l'ancienne version est relancée et l'erreur
    est écrite dans le journal de mise à jour.

    PowerShell script that replaces the files once the app has closed, then starts it again.

    ``_internal`` (Python and Qt) is mirrored; the rest is copied without deleting anything, to
    keep personal scripts. On failure, the old version is started again and the error is
    written to the update log.
    """
    return f"""$ErrorActionPreference = 'Stop'
$source = {_ps_quote(source)}
$target = {_ps_quote(target)}
$work = {_ps_quote(work_dir)}
$log = {_ps_quote(log)}
function Write-Log([string]$text) {{
    Add-Content -LiteralPath $log -Value ((Get-Date -Format 's') + ' ' + $text) -Encoding UTF8
}}
try {{
    Wait-Process -Id {pid} -Timeout 60 -ErrorAction SilentlyContinue
    $quiet = '/R:5', '/W:1', '/NP', '/NFL', '/NDL', '/NJH', '/NJS'
    robocopy (Join-Path $source '_internal') (Join-Path $target '_internal') /MIR @quiet | Out-Null
    if ($LASTEXITCODE -ge 8) {{ throw "robocopy _internal: $LASTEXITCODE" }}
    robocopy $source $target /E /XD (Join-Path $source '_internal') @quiet | Out-Null
    if ($LASTEXITCODE -ge 8) {{ throw "robocopy: $LASTEXITCODE" }}
    Write-Log 'Mise a jour installee.'
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    Write-Log ('Echec de la mise a jour : ' + $_.Exception.Message)
}}
Start-Process -FilePath (Join-Path $target '{EXE_NAME}')
"""


def launch_apply(source: Path, target: Path, work_dir: Path, log: Path) -> None:
    """Lance, sans fenêtre, le script qui installera la mise à jour après la fermeture de l'application.

    Starts, without a window, the script that will install the update after the app closes.
    """
    script = work_dir / "apply-update.ps1"
    # UTF-8 avec BOM : Windows PowerShell 5.1 lit sinon les chemins accentués de travers.
    # UTF-8 with BOM: otherwise Windows PowerShell 5.1 misreads accented paths.
    script.write_text(apply_script(source, target, os.getpid(), work_dir, log), encoding="utf-8-sig")
    powershell = system32() / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    subprocess.Popen(
        [
            str(powershell),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script),
        ],
        cwd=str(work_dir),
        creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
