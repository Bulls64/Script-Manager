"""Cartes de scripts et grille adaptative.

Script cards and adaptive grid.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QMenu, QPushButton, QVBoxLayout, QWidget

from .core import Script
from .i18n import tr
from .widgets import IconButton, IconTile, ProgressLine, ToggleSwitch, label


def edit_file(path: Path) -> None:
    """Ouvre le script dans l'éditeur associé (aucun éditeur associé : rien ne se passe).

    Opens the script in the associated editor (no associated editor: nothing happens).
    """
    with contextlib.suppress(OSError):
        os.startfile(str(path), "edit")  # type: ignore[attr-defined]


class ScriptCard(QFrame):
    launch = Signal(object)
    launch_with_restore = Signal(object)
    # Favoris seulement : lancement en administrateur, retrait des favoris.
    # Favorites only: run as administrator, remove from favorites.
    launch_elevated = Signal(object)
    unfavorite = Signal(object)

    def __init__(self, script: Script, scripts_dir: Path, favorite: bool = False) -> None:
        super().__init__()
        self.script = script
        self.scripts_dir = scripts_dir
        self.favorite = favorite
        self.running = False
        self.setObjectName("Card")
        self.setMinimumHeight(178)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.search_text = f"{script.title} {script.description} {script.filename}".lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 12, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(IconTile(script.icon), 0, Qt.AlignmentFlag.AlignTop)
        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(label(script.title, "strong", wrap=True))
        heading.addWidget(label(script.filename, "caption"))
        top.addLayout(heading, 1)
        more = IconButton("more", tr("Plus d’options"))
        more.clicked.connect(lambda: self._menu(more))
        top.addWidget(more, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        description = label(script.description, "body2", wrap=True)
        description.setMinimumHeight(38)
        layout.addWidget(description)
        layout.addStretch(1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 6, 0)
        bottom.setSpacing(6)
        for text in script.badges:
            bottom.addWidget(label(text, "badge"))
        self.missing = not (scripts_dir / script.filename).is_file()
        if self.missing:
            bottom.addWidget(label(tr("Fichier introuvable"), "badgeCritical"))
        bottom.addStretch(1)
        self.button = QPushButton(tr("Lancer"))
        self.button.setProperty("accent", True)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setMinimumWidth(104)
        self.button.clicked.connect(lambda: self.launch.emit(self))
        bottom.addWidget(self.button)
        layout.addLayout(bottom)

        self.progress = ProgressLine()
        layout.addSpacing(8)
        layout.addWidget(self.progress)
        layout.addSpacing(3)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        layout = self.layout()
        if layout is not None and layout.hasHeightForWidth():
            needed = max(178, layout.heightForWidth(self.width()))
            if needed != self.minimumHeight():
                self.setMinimumHeight(needed)

    def set_running(self, running: bool, text: str = "") -> None:
        # Texte par défaut traduit à l'appel : une valeur par défaut serait figée avant le choix de la langue.
        # Default text translated at call time: a default value would be frozen before the language is chosen.
        self.running = running
        self.button.setEnabled(not running)
        self.button.setText((text or tr("En cours…")) if running else tr("Lancer"))
        if running:
            self.progress.start()
        else:
            self.progress.stop()

    def _menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        menu.setWindowFlags(
            menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        path = self.scripts_dir / self.script.filename
        menu.addAction(tr("Ouvrir l’emplacement du fichier")).triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.scripts_dir)))
        )
        menu.addAction(tr("Copier le chemin")).triggered.connect(
            lambda: QGuiApplication.clipboard().setText(str(path))
        )
        menu.addSeparator()
        restore = menu.addAction(tr("Créer un point de restauration, puis lancer"))
        restore.setEnabled(self.button.isEnabled())
        restore.triggered.connect(lambda: self.launch_with_restore.emit(self))
        if self.favorite:
            elevated = menu.addAction(tr("Lancer en administrateur"))
            elevated.setEnabled(self.button.isEnabled())
            elevated.triggered.connect(lambda: self.launch_elevated.emit(self))
        edit = menu.addAction(tr("Modifier le script"))
        edit.setEnabled(path.is_file() and hasattr(os, "startfile"))
        edit.triggered.connect(lambda: edit_file(path))
        if self.favorite:
            menu.addSeparator()
            remove = menu.addAction(tr("Retirer des favoris"))
            remove.setEnabled(not self.running)
            remove.triggered.connect(lambda: self.unfavorite.emit(self))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


class ArrowsCard(QFrame):
    """Supprimer + Restaurer réunis en un seul réglage, comme un SettingsCard.

    Remove + Restore combined into a single setting, like a SettingsCard.
    """

    toggled = Signal(object, bool)

    def __init__(self, on: Script, off: Script, hidden: bool) -> None:
        super().__init__()
        self.on_script, self.off_script = on, off
        self.setObjectName("Card")
        self.search_text = f"{on.title} {off.title} {on.description} {tr('flèches raccourcis')}".lower()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 0)
        outer.setSpacing(0)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(IconTile("key"), 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        text.addWidget(label(tr("Flèches des raccourcis"), "strong"))
        text.addWidget(
            label(
                tr(
                    "Masque la petite flèche des icônes de raccourcis, pour tous les utilisateurs. "
                    "L’état d’origine est enregistré : désactiver l’interrupteur le restaure."
                ),
                "body2",
                wrap=True,
            )
        )
        badges = QHBoxLayout()
        badges.setSpacing(6)
        for b in (tr("Administrateur"), tr("Registre"), tr("Réversible")):
            badges.addWidget(label(b, "badge"))
        badges.addStretch(1)
        text.addSpacing(4)
        text.addLayout(badges)
        row.addLayout(text, 1)
        right = QHBoxLayout()
        right.setSpacing(12)
        self.state = label("", "body2")
        self.switch = ToggleSwitch()
        self.switch.toggled.connect(lambda checked: self.toggled.emit(self, checked))
        right.addWidget(self.state)
        right.addWidget(self.switch)
        row.addLayout(right)
        outer.addLayout(row)
        outer.addSpacing(14)
        self.progress = ProgressLine()
        outer.addWidget(self.progress)
        outer.addSpacing(3)
        self.set_state(hidden)

    def set_state(self, hidden: bool) -> None:
        self.switch.set_checked_silently(hidden)
        self.state.setText(tr("Masquées") if hidden else tr("Visibles"))

    def set_running(self, running: bool, text: str = "") -> None:
        self.switch.setEnabled(not running)
        if running:
            self.state.setText(text or tr("En cours…"))
            self.progress.start()
        else:
            self.progress.stop()


class ResponsiveGrid(QWidget):
    """Grille qui passe de 1 à N colonnes selon la largeur disponible.

    Grid that goes from 1 to N columns depending on the available width.
    """

    def __init__(self, min_column: int = 330, spacing: int = 12) -> None:
        super().__init__()
        self.min_column, self.spacing = min_column, spacing
        self.items: list[tuple[QWidget, bool]] = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(spacing)
        self.columns = 0

    def add(self, widget: QWidget, wide: bool = False) -> None:
        # Pas de mise en page à chaque ajout : la prochaine relayout() s'en charge.
        # No layout on every addition: the next relayout() takes care of it.
        self.items.append((widget, wide))
        self.columns = 0

    def remove(self, widget: QWidget) -> None:
        # Pas de relayout ici : l'appelant refiltre la page, ce qui remet la grille en page.
        # No relayout here: the caller filters the page again, which lays the grid out.
        self.items = [(w, wide) for w, wide in self.items if w is not widget]
        self.grid.removeWidget(widget)
        widget.hide()
        widget.deleteLater()
        self.columns = 0

    def visible_count(self) -> int:
        return sum(1 for w, _ in self.items if not w.property("filtered"))

    def relayout(self, force: bool = False) -> None:
        width = self.width() or 700
        columns = max(1, (width + self.spacing) // (self.min_column + self.spacing))
        if columns == self.columns and not force:
            return
        self.columns = columns
        for index in reversed(range(self.grid.count())):
            self.grid.takeAt(index)
        row = col = 0
        for widget, wide in self.items:
            hidden = bool(widget.property("filtered"))
            widget.setVisible(not hidden)
            if hidden:
                continue
            if wide:
                if col:
                    row, col = row + 1, 0
                self.grid.addWidget(widget, row, 0, 1, columns)
                row += 1
                continue
            self.grid.addWidget(widget, row, col)
            col += 1
            if col == columns:
                row, col = row + 1, 0
        # Toutes les colonnes déjà créées par la grille, même au-delà des colonnes actuelles.
        # Every column the grid has already created, even beyond the current columns.
        for i in range(max(columns, self.grid.columnCount())):
            self.grid.setColumnStretch(i, 1 if i < columns else 0)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self.relayout()
