"""Jetons de couleur et feuille de style façon WinUI 3 (Fluent).

Color tokens and style sheet in the WinUI 3 (Fluent) style.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

from .core import ACCENTS, system_prefers_dark_registry


def mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def argb(color: QColor, alpha: int) -> str:
    return f"#{alpha:02x}{color.red():02x}{color.green():02x}{color.blue():02x}"


def fade(value: str, transparency: int) -> str:
    """Couleur ``value`` rendue plus transparente de ``transparency`` %.

    Color ``value`` made more transparent by ``transparency`` %.
    """
    color = QColor(value)
    return argb(color, round(color.alpha() * (100 - transparency) / 100))


def make_tokens(dark: bool, accent: str, mica: bool, transparency: int = 0) -> dict[str, str]:
    """Jetons du thème. ``transparency`` (0-100) rend translucides le fond, la couche et les cartes ;
    le texte et les contrôles restent opaques.

    Theme tokens. ``transparency`` (0-100) makes the background, layer and cards translucent;
    text and controls stay opaque.
    """
    base = QColor(accent)
    hue = max(base.hslHueF(), 0.0)
    sat = base.hslSaturationF()
    light = base.lightnessF()
    white, black = QColor("#ffffff"), QColor("#000000")
    if dark:
        acc = QColor.fromHslF(hue, sat, max(light, 0.72))
        layer = QColor("#272727")
        t = {
            "bg": "#202020",
            "layer": "#272727",
            "layer_stroke": "#1c1c1c",
            "card": "#2b2b2b",
            "card_stroke": "#1d1d1d",
            "text": "#ffffff",
            "text2": "#c5c5c5",
            "text3": "#8f8f8f",
            "subtle": "#0fffffff",
            "subtle2": "#0affffff",
            "control": "#2d2d2d",
            "control_hover": "#323232",
            "control_pressed": "#282828",
            "control_disabled": "#262626",
            "control_stroke": "#363636",
            "control_stroke2": "#2f2f2f",
            "field_focus": "#1f1f1f",
            "flyout": "#2c2c2c",
            "flyout_stroke": "#3c3c3c",
            "scroll": "#5a5a5a",
            "divider": "#15ffffff",
            "on_accent": "#000000",
            "on_accent2": "#99000000",
            "on_accent_disabled": "#80ffffff",
            "accent_disabled": "#29ffffff",
            "success_bg": "#393d1b",
            "success": "#6ccb5f",
            "caution_bg": "#433519",
            "caution": "#fce100",
            "critical_bg": "#442726",
            "critical": "#ff99a4",
        }
    else:
        acc = QColor.fromHslF(hue, sat, min(light, 0.40))
        layer = QColor("#f9f9f9")
        t = {
            "bg": "#f3f3f3",
            "layer": "#f9f9f9",
            "layer_stroke": "#e5e5e5",
            "card": "#ffffff",
            "card_stroke": "#e5e5e5",
            "text": "#1b1b1b",
            "text2": "#5f5f5f",
            "text3": "#8a8a8a",
            "subtle": "#0a000000",
            "subtle2": "#06000000",
            "control": "#fdfdfd",
            "control_hover": "#f8f8f8",
            "control_pressed": "#f4f4f4",
            "control_disabled": "#f5f5f5",
            "control_stroke": "#e5e5e5",
            "control_stroke2": "#cccccc",
            "field_focus": "#ffffff",
            "flyout": "#fbfbfb",
            "flyout_stroke": "#dedede",
            "scroll": "#a0a0a0",
            "divider": "#0f000000",
            "on_accent": "#ffffff",
            "on_accent2": "#b3ffffff",
            "on_accent_disabled": "#ffffff",
            "accent_disabled": "#37000000",
            "success_bg": "#dff6dd",
            "success": "#0f7b0f",
            "caution_bg": "#fff4ce",
            "caution": "#9d5d00",
            "critical_bg": "#fde7e9",
            "critical": "#c42b1c",
        }
    t["accent"] = acc.name()
    t["accent_hover"] = mix(acc, layer, 0.10).name()
    t["accent_pressed"] = mix(acc, layer, 0.20).name()
    t["accent_stroke"] = mix(acc, white, 0.10).name()
    t["accent_stroke2"] = mix(acc, black, 0.25).name()
    t["tile"] = argb(acc, 0x2A if dark else 0x1A)
    t["hero_a"] = QColor.fromHslF(hue, min(1.0, sat * 0.95), 0.24).name()
    t["hero_b"] = QColor.fromHslF((hue + 0.06) % 1.0, min(1.0, sat), 0.46).name()
    if mica:
        # Fond transparent : Windows dessine Mica derrière la fenêtre.
        # Transparent background: Windows draws Mica behind the window.
        t["bg"] = "#00000000"
        t["layer"] = "#4d3a3a3a" if dark else "#80ffffff"
        t["card"] = "#0dffffff" if dark else "#b3ffffff"
        t["layer_stroke"] = "#1a000000" if dark else "#0f000000"
    if transparency > 0:
        for name in ("bg", "layer", "card"):
            t[name] = fade(t[name], transparency)
    return t


class Theme:
    """État global du thème, lu par les widgets qui se dessinent eux-mêmes.

    Global theme state, read by the widgets that paint themselves.
    """

    tokens: dict[str, str] = {}
    colors: dict[str, QColor] = {}
    dark = False

    @classmethod
    def set(cls, dark: bool, tokens: dict[str, str]) -> None:
        # Les couleurs sont analysées une fois par thème, pas à chaque dessin.
        # Colors are parsed once per theme, not on every paint.
        cls.dark, cls.tokens = dark, tokens
        cls.colors = {name: QColor(value) for name, value in tokens.items()}


Theme.set(False, make_tokens(False, ACCENTS[0], False))


def tok(name: str) -> QColor:
    """Couleur du thème courant. Objet partagé : le copier avant de le modifier.

    Color of the current theme. Shared object: copy it before changing it.
    """
    return Theme.colors[name]


QSS = """
QWidget { color: %(text)s; font-size: 14px; }
QWidget#Root { background: %(bg)s; }
QFrame#Layer { background: %(layer)s; border: 1px solid %(layer_stroke)s;
  border-right: none; border-bottom: none; border-top-left-radius: 8px; }
QScrollArea, QScrollArea > QWidget > QWidget#PageBody { background: transparent; border: none; }
QFrame#Card { background: %(card)s; border: 1px solid %(card_stroke)s; border-radius: 8px; }
QLabel { background: transparent; }
QLabel[role="caption"] { font-size: 12px; color: %(text2)s; }
QLabel[role="body2"] { color: %(text2)s; }
QLabel[role="strong"] { font-weight: 600; }
QLabel[role="subtitle"] { font-size: 20px; font-weight: 600; }
QLabel[role="title"] { font-size: 28px; font-weight: 600; }
QLabel[role="badge"] { font-size: 11px; color: %(text2)s; background: %(subtle)s;
  border-radius: 10px; padding: 0 9px; min-height: 20px; max-height: 20px; }
QLabel[role="badgeCritical"] { font-size: 11px; color: %(critical)s; background: %(critical_bg)s;
  border-radius: 10px; padding: 0 9px; min-height: 20px; max-height: 20px; }
QPushButton { background: %(control)s; border: 1px solid %(control_stroke)s;
  border-bottom-color: %(control_stroke2)s; border-radius: 4px; padding: 5px 14px; min-height: 20px; }
QPushButton:hover { background: %(control_hover)s; }
QPushButton:pressed { background: %(control_pressed)s; color: %(text2)s; }
QPushButton:disabled { background: %(control_disabled)s; color: %(text3)s; }
QPushButton[accent="true"] { background: %(accent)s; color: %(on_accent)s;
  border: 1px solid %(accent_stroke)s; border-bottom-color: %(accent_stroke2)s; }
QPushButton[accent="true"]:hover { background: %(accent_hover)s; }
QPushButton[accent="true"]:pressed { background: %(accent_pressed)s; color: %(on_accent2)s; }
QPushButton[accent="true"]:disabled { background: %(accent_disabled)s; color: %(on_accent_disabled)s;
  border-color: transparent; }
QLineEdit { background: %(control)s; border: 1px solid %(control_stroke)s;
  border-bottom: 1px solid %(text3)s; border-radius: 4px; padding: 5px 10px 5px 34px; min-height: 20px;
  selection-background-color: %(accent)s; selection-color: %(on_accent)s; }
QLineEdit:hover { background: %(control_hover)s; }
QLineEdit:focus { background: %(field_focus)s; border-bottom: 2px solid %(accent)s; padding-bottom: 4px; }
QComboBox { background: %(control)s; border: 1px solid %(control_stroke)s;
  border-bottom-color: %(control_stroke2)s; border-radius: 4px; padding: 5px 34px 5px 11px;
  min-height: 20px; min-width: 190px; }
QComboBox:hover { background: %(control_hover)s; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow { image: none; width: 0; height: 0; }
QComboBox QAbstractItemView { background: %(flyout)s; border: 1px solid %(flyout_stroke)s;
  padding: 4px; outline: none; selection-background-color: %(subtle)s; selection-color: %(text)s; }
QMenu { background: %(flyout)s; border: 1px solid %(flyout_stroke)s; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 7px 28px 7px 12px; border-radius: 4px; margin: 1px 0; }
QMenu::item:selected { background: %(subtle)s; }
QMenu::separator { height: 1px; background: %(divider)s; margin: 4px 8px; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: %(scroll)s; border-radius: 2px; min-height: 40px; margin: 0 3px; }
QScrollBar::handle:vertical:hover { margin: 0 1px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSlider { background: transparent; min-height: 24px; }
QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: %(scroll)s; }
QSlider::sub-page:horizontal { height: 4px; border-radius: 2px; background: %(accent)s; }
QSlider::handle:horizontal { width: 20px; height: 20px; margin: -8px 0; border-radius: 10px;
  border: 1px solid %(control_stroke)s;
  background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 %(accent)s, stop:0.5 %(accent)s, stop:0.56 %(control)s, stop:1 %(control)s); }
QSlider::handle:horizontal:hover { background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 %(accent)s, stop:0.6 %(accent)s, stop:0.66 %(control)s, stop:1 %(control)s); }
QToolTip { background: %(flyout)s; color: %(text)s; border: 1px solid %(flyout_stroke)s;
  border-radius: 4px; padding: 4px 8px; }
"""


def system_prefers_dark() -> bool:
    """Mode clair ou sombre de Windows (Qt 6.5+, sinon lecture du Registre).

    Windows light or dark mode (Qt 6.5+, otherwise read from the Registry).
    """
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
    except AttributeError:
        return system_prefers_dark_registry()
    if scheme == Qt.ColorScheme.Unknown:
        return system_prefers_dark_registry()
    return bool(scheme == Qt.ColorScheme.Dark)
