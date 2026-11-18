"""Fenêtre « Raccourcis sur le Bureau » : choisir des scripts et leur créer un raccourci.

"Desktop shortcuts" window: pick scripts and create a shortcut for each.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .core import CATEGORIES, FAVORITES, Script, shortcut_name
from .i18n import tr
from .pages import FAVORITES_SECTION, SECTIONS
from .widgets import CheckBox, IconTile, ThemedDialog, label


class ShortcutsDialog(ThemedDialog):
    """Liste des scripts groupés par section ; ceux déjà sur le Bureau ne peuvent pas être cochés.

    Scripts grouped by section; those already on the desktop cannot be checked.
    """

    def __init__(
        self,
        scripts: Iterable[Script],
        desktop: Path,
        parent: QWidget | None = None,
        checked: Iterable[str] = (),
    ) -> None:
        super().__init__(parent, "Shortcuts")
        self.setWindowTitle(tr("Raccourcis sur le Bureau"))
        self.setMinimumWidth(600)
        self.resize(660, 620)
        preselected = {name.lower() for name in checked}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(IconTile("desktop", 40))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label(tr("Raccourcis sur le Bureau"), "subtitle"))
        titles.addWidget(label(tr("Coche les scripts à placer sur le Bureau de Windows."), "body2"))
        head.addLayout(titles, 1)
        root.addLayout(head)

        card = QFrame()
        card.setObjectName("Card")
        rows = QVBoxLayout(card)
        rows.setContentsMargins(16, 12, 16, 14)
        rows.setSpacing(6)
        names = {key: tr(title) for key, title, _icon, _sub in [*SECTIONS, FAVORITES_SECTION]}
        by_category: dict[str, list[Script]] = {}
        for script in scripts:
            by_category.setdefault(script.category, []).append(script)
        self.boxes: list[tuple[CheckBox, Script]] = []
        self.on_desktop: list[str] = []
        for category in [*CATEGORIES, FAVORITES]:
            group = by_category.get(category)
            if not group:
                continue
            if self.boxes:
                rows.addSpacing(8)
            rows.addWidget(label(names.get(category, category), "caption"))
            for script in group:
                rows.addWidget(self._row(script, desktop, script.filename.lower() in preselected))
        rows.addStretch(1)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.Shape.NoFrame)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller.setWidget(card)
        root.addWidget(scroller, 1)

        root.addWidget(
            label(
                tr(
                    "Un raccourci lance le script directement, sans passer par Script Manager : "
                    "pas de point de restauration automatique ni de journal. Les scripts "
                    "administrateur demandent eux-mêmes les droits."
                ),
                "caption",
                wrap=True,
            )
        )

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.all_button = QPushButton(tr("Tout sélectionner"))
        self.all_button.clicked.connect(self._toggle_all)
        footer.addWidget(self.all_button)
        footer.addStretch(1)
        cancel = QPushButton(tr("Annuler"))
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self.create_button = QPushButton()
        self.create_button.setProperty("accent", True)
        self.create_button.setDefault(True)
        self.create_button.clicked.connect(self.accept)
        footer.addWidget(self.create_button)
        root.addLayout(footer)
        self._update()

    def _row(self, script: Script, desktop: Path, checked: bool) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)
        box = CheckBox(script.title)
        box.setToolTip(script.description)
        present = (desktop / shortcut_name(script.title)).exists()
        if present:
            box.setEnabled(False)
            self.on_desktop.append(script.filename)
        else:
            box.setChecked(checked)
            box.toggled.connect(self._update)
            self.boxes.append((box, script))
        layout.addWidget(box)
        layout.addStretch(1)
        name = label(tr("Déjà sur le Bureau") if present else script.filename, "caption")
        name.setMinimumWidth(0)
        layout.addWidget(name)
        return row

    def selected(self) -> list[Script]:
        return [script for box, script in self.boxes if box.isChecked()]

    def _toggle_all(self) -> None:
        check = not all(box.isChecked() for box, _ in self.boxes)
        for box, _ in self.boxes:
            box.blockSignals(True)
            box.setChecked(check)
            box.blockSignals(False)
            box.update()
        self._update()

    def _update(self) -> None:
        count = len(self.selected())
        self.create_button.setEnabled(count > 0)
        self.create_button.setText(
            tr("Créer {count} raccourcis", count=count) if count > 1 else tr("Créer le raccourci")
        )
        everything = bool(self.boxes) and count == len(self.boxes)
        self.all_button.setText(tr("Tout désélectionner") if everything else tr("Tout sélectionner"))
        self.all_button.setEnabled(bool(self.boxes))
