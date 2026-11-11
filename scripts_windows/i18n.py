"""Traduction de l'interface : le français est la langue source, l'anglais est traduit.

``tr("texte français")`` renvoie le texte dans la langue choisie. Les variables passent par
``str.format`` : ``tr("{name} est lancé.", name=...)``. Un texte sans traduction reste en français.
``N_("…")`` marque un texte défini au chargement du module (avant le choix de la langue) :
il est traduit plus tard, là où il s'affiche, par ``tr(constante)``.

Interface translation: French is the source language, English is translated.

``tr("French text")`` returns the text in the chosen language. Variables go through
``str.format``: ``tr("{name} est lancé.", name=...)``. A text without a translation stays in French.
``N_("…")`` marks a text defined when the module loads (before the language is chosen):
it is translated later, where it is shown, with ``tr(constant)``.
"""

from __future__ import annotations

import locale
import os

from .translations import EN

# Choix proposés dans les Paramètres ; « system » suit la langue de Windows.
# Choices offered in Settings; "system" follows the Windows language.
LANGUAGES = ("system", "fr", "en")
_current = "fr"


def system_language() -> str:
    """« fr » si l'interface de Windows est en français, sinon « en ».

    "fr" if the Windows interface is in French, otherwise "en".
    """
    try:
        from PySide6.QtCore import QLocale

        names = QLocale.system().uiLanguages()
        code = names[0] if names else QLocale.system().name()
    except ImportError:
        code = os.environ.get("LANG") or (locale.getlocale()[0] or "")
    return "fr" if code.lower().startswith("fr") else "en"


def resolve(choice: str) -> str:
    """Langue effective (« fr » ou « en ») pour un choix des Paramètres.

    Effective language ("fr" or "en") for a choice made in Settings.
    """
    return choice if choice in ("fr", "en") else system_language()


def set_language(choice: str) -> str:
    global _current
    _current = resolve(choice)
    return _current


def language() -> str:
    return _current


def N_(text: str) -> str:  # noqa: N802 - nom habituel du marqueur gettext
    return text


def tr(text: str, /, **values: object) -> str:
    if _current == "en":
        text = EN.get(text, text)
    return text.format(**values) if values else text
