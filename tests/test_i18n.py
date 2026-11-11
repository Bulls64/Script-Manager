"""Traduction anglaise : chaque texte marqué a sa traduction, avec les mêmes variables.

English translation: every marked text has its translation, with the same variables.
"""

from __future__ import annotations

import ast
import json
import string
from pathlib import Path

import pytest

from scripts_windows import core, i18n
from scripts_windows.translations import EN

PROJECT = Path(__file__).resolve().parent.parent
PACKAGE = PROJECT / "scripts_windows"


def marked_texts() -> set[str]:
    """Premier argument littéral de chaque appel tr(...) ou N_(...) du code.

    First literal argument of each tr(...) or N_(...) call in the code.
    """
    texts: set[str] = set()
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("tr", "N_")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                texts.add(node.args[0].value)
    return texts


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_marked_text_is_translated() -> None:
    missing = sorted(marked_texts() - EN.keys())
    assert not missing, missing


def test_no_unused_translation() -> None:
    assert not sorted(EN.keys() - marked_texts())


@pytest.mark.parametrize("source", sorted(EN))
def test_translation_keeps_the_same_variables(source: str) -> None:
    assert fields(source) == fields(EN[source])
    assert source.count("%") == EN[source].count("%")


def test_tr_follows_the_language() -> None:
    assert i18n.tr("{title} est lancé.", title="X") == "X est lancé."
    i18n.set_language("en")
    assert i18n.tr("{title} est lancé.", title="X") == "X is running."
    assert i18n.tr("texte sans traduction") == "texte sans traduction"


def test_system_language_resolves_to_french_or_english() -> None:
    assert i18n.resolve("fr") == "fr" and i18n.resolve("en") == "en"
    assert i18n.resolve("system") in ("fr", "en")


@pytest.mark.parametrize(
    ("value", "expected"), [("en", "en"), ("fr", "fr"), ("system", "system"), ("de", "system")]
)
def test_language_setting_is_validated(value: str, expected: str) -> None:
    assert core.Settings.from_dict({"language": value}).language == expected


def test_manifest_has_english_texts() -> None:
    entries = json.loads((PROJECT / "scripts.json").read_text(encoding="utf-8"))["scripts"]
    assert all(entry.get("title_en") and entry.get("description_en") for entry in entries)
    french = core.load_scripts(PROJECT / "scripts.json")
    i18n.set_language("en")
    english = core.load_scripts(PROJECT / "scripts.json")
    assert [s.filename for s in english] == [s.filename for s in french]
    assert all(e.title == entry["title_en"] for e, entry in zip(english, entries, strict=True))
    assert all(f.title == entry["title"] for f, entry in zip(french, entries, strict=True))


def test_english_title_is_optional_and_must_be_text() -> None:
    entry = {"title": "Titre", "filename": "a.bat", "description": "Texte"}
    i18n.set_language("en")
    assert core.parse_scripts({"scripts": [entry]})[0].title == "Titre"
    with pytest.raises(core.ManifestError, match="title_en"):
        core.parse_scripts({"scripts": [{**entry, "title_en": ""}]})


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("a.bat : finished (code 0)", "success"),
        ("Restore point : created", "success"),
        ("a.bat : failed (code 1)", "critical"),
        ("Restore point : system protection is disabled", "critical"),
        ("a.bat : elevation denied", "caution"),
        ("a.bat : window closed by the user", "caution"),
        ("a.bat : started", "info"),
    ],
)
def test_english_journal_lines_are_classified(text: str, kind: str) -> None:
    assert core.classify(text) == kind


def test_english_journal_texts_keep_their_colors() -> None:
    """Chaque texte du journal garde la même couleur une fois traduit.

    Each log text keeps the same color once translated.
    """
    journal = ("terminé (code 0)", "échec (code {code})", "élévation refusée", "fenêtre fermée avant la fin")
    for french in journal:
        assert core.classify(f"a : {french}") == core.classify(f"a : {EN[french]}")
    assert core.classify("a : créé") == core.classify(f"a : {EN['créé']}")
