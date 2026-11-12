"""Mises à jour depuis les releases GitHub (sans réseau : téléchargements simulés).

Updates from GitHub releases (no network: downloads are simulated).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts_windows import __version__, core, updater

ZIP_URL = "https://github.com/Bulls64/Script-Manager/releases/download/v9.0.0/Script-Manager-9.0.0.zip"


def release_json(version: str = "9.0.0", arm64: bool = False) -> dict[str, Any]:
    base = f"https://github.com/Bulls64/Script-Manager/releases/download/v{version}"
    names = [f"Script-Manager-{version}.zip"] + ([f"Script-Manager-{version}-arm64.zip"] if arm64 else [])
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/Bulls64/Script-Manager/releases/tag/v{version}",
        "assets": [
            {"name": name + ext, "browser_download_url": f"{base}/{name}{ext}"}
            for name in names
            for ext in ("", ".sha256")
        ],
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [("v2.17.0", (2, 17, 0)), ("2.18", (2, 18)), ("v10.0.1", (10, 0, 1)), ("v2.17.0-beta", None), ("", None)],
)
def test_parse_version(text: str, expected: tuple[int, ...] | None) -> None:
    assert updater.parse_version(text) == expected


def test_is_newer() -> None:
    assert updater.is_newer("2.18.0", "2.17.0")
    assert updater.is_newer("2.17.1", "2.17")
    assert updater.is_newer("10.0.0", "9.9.9")
    assert not updater.is_newer("2.17.0", "2.17.0")
    assert not updater.is_newer("2.17", "2.17.0")
    assert not updater.is_newer("2.9.0", "2.17.0")
    assert not updater.is_newer("pas une version", __version__)


def test_parse_release_finds_the_archive_and_its_hash() -> None:
    release = updater.parse_release(release_json())
    assert release.version == "9.0.0"
    assert release.zip_url == ZIP_URL
    assert release.sha256_url == ZIP_URL + ".sha256"
    assert release.page_url.endswith("/tag/v9.0.0")


def test_parse_release_picks_the_archive_of_the_processor() -> None:
    data = release_json(arm64=True)
    assert updater.parse_release(data, "x64").zip_url == ZIP_URL
    assert updater.parse_release(data, "arm64").zip_url == ZIP_URL.replace(".zip", "-arm64.zip")
    assert updater.parse_release(data, "arm64").sha256_url == ZIP_URL.replace(".zip", "-arm64.zip.sha256")
    # Release sans archive ARM64 : la version x64 (émulée) est proposée.
    # Release without an ARM64 archive: the (emulated) x64 version is offered.
    assert updater.parse_release(release_json(), "arm64").zip_url == ZIP_URL


def test_parse_release_needs_the_hash_of_the_same_archive() -> None:
    data = release_json(arm64=True)
    data["assets"] = [a for a in data["assets"] if a["name"] != "Script-Manager-9.0.0-arm64.zip.sha256"]
    assert updater.parse_release(data, "arm64").zip_url == ZIP_URL


def test_architectures() -> None:
    assert updater.build_arch() in updater.ARCHITECTURES
    assert updater.host_arch() in updater.ARCHITECTURES
    assert updater.asset_name("2.20.0", "x64") == "Script-Manager-2.20.0.zip"
    assert updater.asset_name("2.20.0", "arm64") == "Script-Manager-2.20.0-arm64.zip"


def test_parse_release_without_assets_and_bad_answers() -> None:
    release = updater.parse_release({"tag_name": "v9.0.0", "assets": []})
    assert release.zip_url is None and release.page_url == updater.RELEASES_PAGE
    with pytest.raises(updater.UpdateError):
        updater.parse_release({"tag_name": "nightly"})
    data = release_json()
    data["assets"][0]["browser_download_url"] = "http://example.com/a.zip"
    with pytest.raises(updater.UpdateError):
        updater.parse_release(data)


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_fetch_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def urlopen(request: Any, timeout: float) -> FakeResponse:
        seen.append(request)
        return FakeResponse(json.dumps(release_json()).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assert updater.fetch_latest().version == "9.0.0"
    assert seen[0].full_url == updater.LATEST_API
    assert seen[0].get_header("User-agent", "").startswith("Script-Manager/")


def test_fetch_latest_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def urlopen(_request: Any, timeout: float) -> FakeResponse:
        raise OSError("hors ligne")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    with pytest.raises(updater.UpdateError, match="hors ligne"):
        updater.fetch_latest()


def make_release_zip(path: Path, extra: dict[str, bytes] | None = None) -> bytes:
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("Script-Manager/Script-Manager.exe", b"MZ")
        zipped.writestr("Script-Manager/_internal/base_library.zip", b"x")
        zipped.writestr(
            "Script-Manager/scripts.json",
            json.dumps({"scripts": [{"title": "A", "filename": "A.bat", "description": "a"}]}),
        )
        zipped.writestr("Script-Manager/scripts/A.bat", b"@echo off\r\n")
        for name, data in (extra or {}).items():
            zipped.writestr(name, data)
    return path.read_bytes()


def serve(monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes]) -> None:
    def download(url: str, destination: Path, limit: int = updater.MAX_DOWNLOAD) -> None:
        destination.write_bytes(files[url])

    monkeypatch.setattr(updater, "download", download)


def installed_app(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    (app / "scripts").mkdir(parents=True)
    entries = [
        {"title": "A", "filename": "A.bat", "description": "ancienne"},
        {"title": "Perso", "filename": "Perso.bat", "description": "à moi"},
        {"title": "Disparu", "filename": "Disparu.bat", "description": "fichier supprimé"},
    ]
    (app / "scripts.json").write_text(json.dumps({"scripts": entries}), encoding="utf-8")
    (app / "scripts" / "Perso.bat").write_text("@echo off\r\n", encoding="ascii")
    return app


def test_prepare_checks_extracts_and_keeps_personal_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = make_release_zip(tmp_path / "r.zip")
    digest = hashlib.sha256(data).hexdigest()
    serve(monkeypatch, {ZIP_URL: data, ZIP_URL + ".sha256": f"{digest}  Script-Manager-9.0.0.zip\n".encode()})
    app = installed_app(tmp_path)
    source = updater.prepare(updater.parse_release(release_json()), app, tmp_path / "work")
    assert (source / "Script-Manager.exe").is_file()
    names = [
        e["filename"] for e in json.loads((source / "scripts.json").read_text(encoding="utf-8"))["scripts"]
    ]
    # A.bat vient de la nouvelle version ; Perso.bat est gardé ; Disparu.bat n'existe plus.
    # A.bat comes from the new version; Perso.bat is kept; Disparu.bat no longer exists.
    assert names == ["A.bat", "Perso.bat"]
    assert core.load_scripts(source / "scripts.json")[1].title == "Perso"


def test_prepare_rejects_a_wrong_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = make_release_zip(tmp_path / "r.zip")
    serve(monkeypatch, {ZIP_URL: data, ZIP_URL + ".sha256": b"0" * 64})
    with pytest.raises(updater.UpdateError, match="SHA-256"):
        updater.prepare(updater.parse_release(release_json()), installed_app(tmp_path), tmp_path / "w")
    assert not (tmp_path / "w" / "extracted").exists()


def test_prepare_rejects_paths_leaving_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = make_release_zip(tmp_path / "r.zip", {"../../evil.bat": b"x"})
    serve(monkeypatch, {ZIP_URL: data, ZIP_URL + ".sha256": hashlib.sha256(data).hexdigest().encode()})
    with pytest.raises(updater.UpdateError, match="chemin invalide"):
        updater.prepare(updater.parse_release(release_json()), installed_app(tmp_path), tmp_path / "w")
    assert not (tmp_path / "evil.bat").exists()


def test_prepare_needs_the_archive_and_its_hash(tmp_path: Path) -> None:
    release = updater.Release("9.0.0", updater.RELEASES_PAGE, None, None)
    with pytest.raises(updater.UpdateError):
        updater.prepare(release, tmp_path, tmp_path / "w")


def test_apply_script_quotes_paths_and_restarts_the_app(tmp_path: Path) -> None:
    script = updater.apply_script(
        Path("C:/Temp/new/Script-Manager"), Path("C:/Outils/L'atelier"), 1234, tmp_path, tmp_path / "u.log"
    )
    assert "$target = 'C:/Outils/L''atelier'" in script
    assert "Wait-Process -Id 1234" in script
    assert "/MIR @quiet" in script and "/E /XD" in script
    assert script.rstrip().endswith("Start-Process -FilePath (Join-Path $target 'Script-Manager.exe')")


def test_can_self_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not updater.can_self_update(tmp_path)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Script-Manager.exe"))
    assert updater.can_self_update(tmp_path)
    assert not updater.can_self_update(tmp_path / "ailleurs")
    assert updater.folder_is_writable(tmp_path)


def test_update_check_setting_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    assert core.Settings().update_check is True
    core.save_settings(path, core.Settings(update_check=False))
    assert core.load_settings(path).update_check is False
    path.write_text('{"update_check": "oui"}', encoding="utf-8")
    assert core.load_settings(path).update_check is True
