"""Fenêtre « Nouveautés de la v… » : ce qui a changé dans la version installée.

"What's new in v…" window: what changed in the installed version.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import __version__, core
from .i18n import N_, tr
from .icons import AA
from .theme import tok
from .widgets import IconTile, ThemedDialog, label

# Nouveautés par version, la plus récente en premier. À compléter à chaque version :
# un test vérifie que la version en cours a sa liste.
# What's new per version, most recent first. To be filled in for each version:
# a test checks that the current version has its list.
NOTES: dict[str, tuple[str, ...]] = {
    "2.22.0": (
        N_(
            "Nouveau bouton « Raccourcis sur le Bureau » sur l’accueil : coche des scripts, intégrés "
            "ou favoris, et Script Manager leur crée un raccourci sur le Bureau de Windows."
        ),
        N_("Le menu « … » de chaque carte propose aussi « Créer un raccourci sur le Bureau »."),
        N_(
            "Un raccourci déjà présent n’est jamais remplacé, et le Bureau redirigé vers "
            "OneDrive est pris en compte."
        ),
    ),
    "2.21.0": (
        N_(
            "Nouveau script « Désactiver les notifications » : notifications des applications, "
            "de l’écran de verrouillage et conseils de Windows, pour le compte courant."
        ),
        N_(
            "Nouveau script « Désactiver les widgets » : bouton de la barre des tâches, panneau et "
            "Windows+W, pour tout l’ordinateur (droits administrateur)."
        ),
        N_(
            "Chacun a son script « Restaurer » qui remet les réglages d’origine. "
            "Ils sont dans la section Registre."
        ),
    ),
    "2.20.0": (
        N_(
            "Version ARM64 pour les PC ARM (Snapdragon, PC Copilot+) : chaque release propose "
            "aussi une archive « -arm64 », native, à côté de l’archive x64."
        ),
        N_(
            "Les mises à jour téléchargent l’archive du processeur : sur un PC ARM, la version x64 "
            "émulée est remplacée par la version ARM64 native."
        ),
        N_("Paramètres › Mises à jour affiche l’architecture à côté du numéro de version."),
    ),
    "2.19.0": (
        N_(
            "Fenêtre « Nouveautés » : elle s’affiche au premier lancement d’une nouvelle version "
            "et liste ce qui a changé."
        ),
        N_("Elle peut être rouverte à tout moment depuis Paramètres › Mises à jour › Nouveautés."),
        N_(
            "Son affichage automatique se désactive dans Paramètres › Mises à jour, avec "
            "« Afficher les nouveautés après une mise à jour »."
        ),
    ),
    "2.18.0": (
        N_(
            "Mises à jour depuis les releases GitHub : recherche automatique au démarrage "
            "(désactivable) et bouton « Rechercher » dans Paramètres › Mises à jour."
        ),
        N_(
            "« Installer » télécharge l’archive, vérifie son empreinte SHA-256, puis ferme l’appli, "
            "copie les nouveaux fichiers et la relance."
        ),
        N_("Réglages, favoris et scripts ajoutés à scripts.json sont conservés."),
    ),
}


def notes(version: str = __version__) -> tuple[str, ...]:
    """Nouveautés traduites de ``version`` ; vide si elle n'en a pas.

    Translated news of ``version``; empty if it has none.
    """
    return tuple(tr(text) for text in NOTES.get(version, ()))


def should_show(settings: core.Settings, version: str = __version__) -> bool:
    """Affichage automatique : premier lancement de cette version, option active, liste non vide.

    Automatic display: first run of this version, option enabled, non-empty list.
    """
    return settings.whats_new and settings.seen_version != version and bool(NOTES.get(version))


class Bullet(QWidget):
    """Puce ronde à la couleur d'accent. / Round bullet in the accent color."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(14, 20)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(AA)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(tok("accent"))
        painter.drawEllipse(3, 7, 6, 6)


class WhatsNewDialog(ThemedDialog):
    def __init__(self, parent: QWidget | None = None, version: str = __version__) -> None:
        super().__init__(parent, "WhatsNew")
        self.setWindowTitle(tr("Nouveautés de la v{version}", version=version))
        self.setMinimumWidth(520)
        self.resize(560, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(IconTile("info", 40))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label(tr("Nouveautés de la v{version}", version=version), "subtitle"))
        titles.addWidget(label(tr("Ce qui a changé dans cette version de Script Manager."), "body2"))
        head.addLayout(titles, 1)
        root.addLayout(head)

        card = QFrame()
        card.setObjectName("Card")
        items = QVBoxLayout(card)
        items.setContentsMargins(16, 14, 16, 14)
        items.setSpacing(10)
        self.items: list[str] = list(notes(version))
        for text in self.items or [tr("Aucune nouveauté listée pour cette version.")]:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.addWidget(Bullet(), 0, Qt.AlignmentFlag.AlignTop)
            item = label(text, wrap=True)
            item.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(item, 1)
            items.addLayout(row)
        items.addStretch(1)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.Shape.NoFrame)
        scroller.setWidget(card)
        root.addWidget(scroller, 1)

        footer = QHBoxLayout()
        footer.addWidget(label(tr("Historique complet : CHANGELOG.md sur GitHub."), "caption"), 1)
        close = QPushButton(tr("Fermer"))
        close.setProperty("accent", True)
        close.setDefault(True)
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)
