"""Pièges d'encodage des scripts Windows, vérifiés sans Windows.

Encoding pitfalls of the Windows scripts, checked without Windows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT / "scripts"
# Les scripts sont dans scripts\ ; build.bat reste à la racine.
# The scripts are in scripts\; build.bat stays at the root.
BATS = sorted(PROJECT.glob("*.bat")) + sorted(SCRIPTS.glob("*.bat"))
# Marqueur qui sépare la partie batch de la partie PowerShell embarquée.
# Marker separating the batch part from the embedded PowerShell part.
MARKER = b"\r\n#PS1#\r\n"
HYBRIDS = [path for path in BATS if MARKER in path.read_bytes()]


def split_hybrid(path: Path) -> tuple[bytes, str]:
    """(partie batch, partie PowerShell décodée) d'un .bat autonome.

    (batch part, decoded PowerShell part) of a self-contained .bat.
    """
    batch, _, powershell = path.read_bytes().partition(MARKER)
    return batch + b"\r\n", powershell.decode("utf-8")


# PowerShell traite les guillemets typographiques comme des guillemets droits.
# PowerShell treats typographic quotes as straight quotes.
SINGLE = "'‘’‚‛"
DOUBLE = '"“”„'


def is_crlf(data: bytes) -> bool:
    return data.count(b"\n") == data.count(b"\r\n")


@pytest.mark.parametrize("path", BATS, ids=lambda p: p.name)
def test_bat_is_ascii_crlf(path: Path) -> None:
    """Partie batch en ASCII (page de code OEM) ; la partie PowerShell embarquée est en UTF-8.

    Batch part in ASCII (OEM code page); the embedded PowerShell part is UTF-8.
    """
    data = path.read_bytes()
    batch = split_hybrid(path)[0] if path in HYBRIDS else data
    assert all(byte < 128 for byte in batch), "cmd.exe lit les .bat dans la page de code OEM"
    assert not data.startswith(b"\xef\xbb\xbf"), "un BOM en tête casse la première ligne de cmd.exe"
    assert is_crlf(data), "les .bat en LF cassent goto et les étiquettes"
    data.decode("utf-8")


@pytest.mark.parametrize("path", HYBRIDS, ids=lambda p: p.name)
def test_hybrid_bat_stops_before_powershell(path: Path) -> None:
    """cmd.exe doit sortir (exit /b) avant la partie PowerShell, que seul PowerShell lit.

    cmd.exe must leave (exit /b) before the PowerShell part, which only PowerShell reads.
    """
    batch = split_hybrid(path)[0].decode("ascii")
    lines = [line.strip().lower() for line in batch.splitlines() if line.strip()]
    assert lines[-1].startswith("exit /b"), "la dernière ligne batch doit quitter"
    assert 'set "self=%~f0"' in lines
    launcher = [line for line in lines if line.startswith("powershell.exe") and "readalltext" in line]
    assert len(launcher) == 1 and "'#'+'ps1'+'#'" in launcher[0], (
        "le lanceur ne doit pas contenir le marqueur"
    )
    assert "#PS1#" not in batch, "le marqueur ne doit pas apparaître dans la partie batch"


def test_no_ps1_file_left_in_the_scripts() -> None:
    assert not list(SCRIPTS.glob("*.ps1"))
    assert HYBRIDS, "aucun script autonome trouvé"


@pytest.mark.parametrize("path", HYBRIDS, ids=lambda p: p.name)
def test_embedded_powershell_quotes_and_delimiters(path: Path) -> None:
    """Chaînes fermées par un vrai guillemet, accolades et parenthèses équilibrées.

    Strings closed by a real quote, balanced braces and parentheses.
    """
    text = split_hybrid(path)[1]
    depth = {"{": 0, "(": 0, "[": 0}
    closing = {"}": "{", ")": "(", "]": "["}
    state, i, line = "code", 0, 1
    while i < len(text):
        char = text[i]
        if char == "\n":
            line += 1
        if state == "code":
            if char == "#":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue
            if char in SINGLE:
                assert char == "'", f"ligne {line} : chaîne ouverte par un guillemet typographique"
                state = "single"
            elif char in DOUBLE:
                assert char == '"', f"ligne {line} : chaîne ouverte par un guillemet typographique"
                state = "double"
            elif char in depth:
                depth[char] += 1
            elif char in closing:
                depth[closing[char]] -= 1
                assert depth[closing[char]] >= 0, f"ligne {line} : « {char} » sans ouverture"
        elif state == "single" and char in SINGLE:
            if text[i + 1 : i + 2] and text[i + 1] in SINGLE:
                i += 1  # '' : apostrophe échappée / '': escaped apostrophe
            else:
                assert char == "'", (
                    f"ligne {line} : « {char} » ferme la chaîne ; utiliser des guillemets doubles"
                )
                state = "code"
        elif state == "double":
            if char == "`":
                i += 1
            elif char in DOUBLE:
                assert char == '"', f"ligne {line} : « {char} » ferme la chaîne"
                state = "code"
        i += 1
    assert state == "code", "chaîne non fermée en fin de fichier"
    assert all(value == 0 for value in depth.values()), depth


@pytest.mark.parametrize("path", BATS, ids=lambda p: p.name)
def test_bat_labels_exist(path: Path) -> None:
    """Chaque goto / call :étiquette doit avoir son étiquette.

    Each goto / call :label must have its label.
    """
    import re

    text = (split_hybrid(path)[0] if path in HYBRIDS else path.read_bytes()).decode("ascii")
    labels = {m.lower() for m in re.findall(r"^:(\w+)", text, re.M)}
    jumps = {m.lower() for m in re.findall(r"(?:goto|call)\s+:?(\w+)", text, re.I)}
    assert not (jumps - labels - {"eof"}), jumps - labels


def test_arrow_scripts_share_the_same_data_locations() -> None:
    """Supprimer et Restaurer doivent chercher l'état aux mêmes endroits.

    Remove and Restore must look for the state in the same places.
    """
    import re

    def picks(name: str) -> list[str]:
        text = (SCRIPTS / name).read_text(encoding="ascii")
        return re.findall(r'call :pick "([^"]+)"', text)

    assert picks("Supprimer-fleche-raccourci.bat") == picks("Restaurer-fleche-raccourci.bat")
    assert (SCRIPTS / "NoArrow" / "NoArrow.ico").is_file()


def test_only_build_bat_stays_at_the_root() -> None:
    assert [p.name for p in PROJECT.glob("*.bat")] == ["build.bat"]
    assert not list(PROJECT.glob("*.ps1"))


def test_animation_scripts_share_one_helper() -> None:
    """Réduire et Restaurer passent par le même .bat d'appoint, qui porte la liste des réglages.

    Shorten and Restore go through the same helper .bat, which holds the list of settings.
    """
    reduce = (SCRIPTS / "Reduire-animations.bat").read_text(encoding="ascii")
    restore = (SCRIPTS / "Restaurer-animations.bat").read_text(encoding="ascii")
    assert 'call "%~dp0Animations-Windows.bat"\n' in reduce and "restaurer" not in reduce
    assert 'call "%~dp0Animations-Windows.bat" restaurer' in restore
    script = split_hybrid(SCRIPTS / "Animations-Windows.bat")[1]
    for name in ("MenuShowDelay", "MouseHoverTime", "ExtendedUIHoverTime", "DesktopLivePreviewHoverTime"):
        assert f"Name = '{name}'" in script
    assert "$Max = 200" in script
    assert "$env:SM_ARG1 -eq 'restaurer'" in script
