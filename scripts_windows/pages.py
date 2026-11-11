"""Pages : scripts (accueil et catégories), journal, paramètres.

Pages: scripts (home and categories), log, settings.
"""

from __future__ import annotations

import contextlib
import os
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QHelpEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .cards import ArrowsCard, ResponsiveGrid, ScriptCard
from .core import (
    ACCENTS,
    ARROWS_OFF,
    ARROWS_ON,
    BACKDROP_BUILD,
    FAVORITES,
    IS_WINDOWS,
    JOURNAL_LIMIT,
    NOT_FAVORITES,
    TRANSPARENCY_MAX,
    Entry,
    Script,
    find_user_scripts,
    system32,
    user_script,
    windows_build,
)
from .i18n import N_, tr
from .icons import AA, paint_icon
from .theme import tok
from .widgets import FluentCombo, Hero, IconView, SearchBox, ToggleSwitch, label

# Scripts qui annulent un autre script, comptés dans le bandeau d'accueil.
# Scripts that undo another script, counted in the home banner.
UNDO_SCRIPTS = (ARROWS_OFF, "Retirer-elements-Bureau.bat", "Restaurer-animations.bat")

SECTIONS = [
    ("bureau", N_("Bureau"), "desktop", N_("Raccourcis et dossiers ajoutés au Bureau.")),
    ("registre", N_("Registre"), "key", N_("Réglages système, toujours réversibles.")),
    ("systeme", N_("Système"), "shield", N_("Points de restauration et entretien de Windows.")),
    ("en_ligne", N_("En ligne"), "globe", N_("Outils de la communauté, téléchargés au lancement.")),
    ("autres", N_("Autres"), "folder", N_("Divers, et les scripts ajoutés à scripts.json.")),
]


def open_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


FAVORITES_SECTION = (
    FAVORITES,
    N_("Favoris"),
    "star",
    N_("Tes propres scripts .bat et .cmd, pris dans le dossier des scripts."),
)


def open_system_restore() -> None:
    """Ouvre rstrui.exe (Windows demande lui-même l'élévation).

    Opens rstrui.exe (Windows asks for elevation itself).
    """
    if not hasattr(os, "startfile"):
        return
    program = system32() / "rstrui.exe"
    with contextlib.suppress(OSError):  # élévation refusée / elevation declined
        os.startfile(str(program))  # type: ignore[attr-defined]


def section_head(icon: str, title: str, subtitle: str) -> QWidget:
    """En-tête de section : icône d'accent, titre et sous-titre (textes source, traduits ici).

    Section header: accent icon, title and subtitle (source texts, translated here).
    """
    head = QWidget()
    row = QHBoxLayout(head)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    row.addWidget(IconView(icon, 20, "accent"))
    row.addWidget(label(tr(title), "subtitle"))
    row.addSpacing(6)
    row.addWidget(label(tr(subtitle), "caption"), 0, Qt.AlignmentFlag.AlignBottom)
    row.addStretch(1)
    return head


def filter_grid(grid: ResponsiveGrid, shown: bool, query: str) -> int:
    """Masque les cartes hors catégorie ou hors recherche ; renvoie le nombre de cartes visibles.

    Hides the cards outside the category or the search; returns the number of visible cards.
    """
    for widget, _ in grid.items:
        match = shown and (not query or query in getattr(widget, "search_text", ""))
        widget.setProperty("filtered", not match)
    grid.relayout(force=True)
    return grid.visible_count()


def page_scroller(body: QWidget) -> QScrollArea:
    body.setObjectName("PageBody")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(body)
    return area


class ScriptsPage(QWidget):
    launch = Signal(object)
    launch_with_restore = Signal(object)
    launch_elevated = Signal(object)
    arrows = Signal(object, bool)
    favorite_added = Signal(str)
    favorite_removed = Signal(str)

    def __init__(
        self,
        scripts: list[Script],
        scripts_dir: Path,
        admin: bool,
        arrows_hidden: bool,
        favorites: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.category = "all"
        self.scripts_dir = scripts_dir
        # Noms en minuscules : Windows ne distingue pas la casse des noms de fichiers.
        # Lowercase names: Windows file names are case-insensitive.
        self.integrated = {s.filename.lower() for s in scripts}
        body = QWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(page_scroller(body))

        layout = QVBoxLayout(body)
        layout.setContentsMargins(36, 26, 36, 36)
        layout.setSpacing(0)

        header = QHBoxLayout()
        self.title = label(tr("Accueil"), "title")
        header.addWidget(self.title)
        header.addStretch(1)
        self.search = SearchBox()
        self.search.textChanged.connect(self.apply_filter)
        header.addWidget(self.search, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)
        self.caption = label("", "body2")
        layout.addSpacing(2)
        layout.addWidget(self.caption)
        layout.addSpacing(18)

        reversible = sum(1 for s in scripts if s.filename in UNDO_SCRIPTS)
        self.hero = Hero(
            [
                ("grid", tr("{count} scripts", count=len(scripts))),
                ("undo", tr("{count} annulations", count=reversible)),
                ("shield", tr("Administrateur") if admin else tr("Utilisateur standard")),
            ]
        )
        layout.addWidget(self.hero)
        self.hero_gap = QWidget()
        self.hero_gap.setFixedHeight(28)
        layout.addWidget(self.hero_gap)

        self.sections: dict[str, tuple[QWidget, ResponsiveGrid]] = {}
        self.section_heads: dict[str, QWidget] = {}
        self.cards: list[QWidget] = []
        self.script_cards: dict[str, ScriptCard] = {}
        self.arrows_card: ArrowsCard | None = None
        by_name = {s.filename: s for s in scripts}
        for key, title, icon, subtitle in SECTIONS:
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 28)
            box_layout.setSpacing(12)
            head_widget = section_head(icon, title, subtitle)
            box_layout.addWidget(head_widget)
            grid = ResponsiveGrid()
            box_layout.addWidget(grid)
            self.sections[key] = (box, grid)
            self.section_heads[key] = head_widget
            layout.addWidget(box)

        if ARROWS_ON in by_name and ARROWS_OFF in by_name:
            card = ArrowsCard(by_name[ARROWS_ON], by_name[ARROWS_OFF], arrows_hidden)
            card.toggled.connect(self.arrows.emit)
            self.arrows_card = card
            self.sections["registre"][1].add(card, wide=True)
            self.cards.append(card)
            skip = {ARROWS_ON, ARROWS_OFF}
        else:
            skip = set()
        for script in scripts:
            if script.filename in skip:
                continue
            script_card = ScriptCard(script, scripts_dir)
            script_card.launch.connect(self.launch.emit)
            script_card.launch_with_restore.connect(self.launch_with_restore.emit)
            self.sections[script.category][1].add(script_card)
            self.script_cards[script.filename] = script_card
            self.cards.append(script_card)

        # Favoris, sous les scripts intégrés.
        # Favorites, below the built-in scripts.
        self.favorite_cards: dict[str, ScriptCard] = {}
        layout.addWidget(self._build_favorites())
        for filename in favorites or []:
            self.add_favorite(filename, refresh=False)

        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setContentsMargins(0, 60, 0, 0)
        icon_view = IconView("search", 40, "text3")
        empty_layout.addWidget(icon_view, 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_label = label("", "body2")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label)
        layout.addWidget(self.empty)
        layout.addStretch(1)
        self.set_category("all")

    # -- favoris / favorites -------------------------------------------------

    def _build_favorites(self) -> QWidget:
        self.favorites_box = QWidget()
        box_layout = QVBoxLayout(self.favorites_box)
        box_layout.setContentsMargins(0, 0, 0, 28)
        box_layout.setSpacing(12)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        _, title, icon, subtitle = FAVORITES_SECTION
        self.favorites_title = section_head(icon, title, subtitle)
        head.addWidget(self.favorites_title)
        head.addStretch(1)
        self.add_button = QPushButton(tr("Ajouter un favori"))
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(lambda: self._favorites_menu(self.add_button))
        head.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        box_layout.addLayout(head)
        self.favorites_grid = ResponsiveGrid()
        box_layout.addWidget(self.favorites_grid)

        self.favorites_empty = QFrame()
        self.favorites_empty.setObjectName("Card")
        empty = QHBoxLayout(self.favorites_empty)
        empty.setContentsMargins(18, 16, 18, 16)
        empty.setSpacing(14)
        empty.addWidget(IconView("star", 20, "text3"))
        empty.addWidget(
            label(
                tr(
                    "Aucun favori pour l’instant. Dépose tes scripts .bat ou .cmd dans le dossier des "
                    "scripts, puis « Ajouter un favori » pour les retrouver ici."
                ),
                "body2",
                wrap=True,
            ),
            1,
        )
        open_button = QPushButton(tr("Ouvrir le dossier"))
        open_button.clicked.connect(lambda: open_folder(self.scripts_dir))
        empty.addWidget(open_button)
        box_layout.addWidget(self.favorites_empty)
        return self.favorites_box

    def available_favorites(self) -> list[str]:
        """Scripts du dossier qu'on peut encore mettre en favori.

        Scripts in the folder that can still be marked as favorites.
        """
        return find_user_scripts(self.scripts_dir, [*self.integrated, *self.favorite_cards])

    def _favorites_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        menu.setWindowFlags(
            menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        names = self.available_favorites()
        for name in names:
            menu.addAction(name).triggered.connect(lambda _c=False, n=name: self.favorite_added.emit(n))
        if not names:
            menu.addAction(tr("Aucun autre script .bat ou .cmd dans le dossier")).setEnabled(False)
        menu.addSeparator()
        menu.addAction(tr("Ouvrir le dossier des scripts")).triggered.connect(
            lambda: open_folder(self.scripts_dir)
        )
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def add_favorite(self, filename: str, refresh: bool = True) -> ScriptCard | None:
        folded = filename.lower()
        taken = folded in self.integrated or folded in NOT_FAVORITES
        if taken or any(name.lower() == folded for name in self.favorite_cards):
            return None
        card = ScriptCard(user_script(self.scripts_dir, filename), self.scripts_dir, favorite=True)
        card.launch.connect(self.launch.emit)
        card.launch_with_restore.connect(self.launch_with_restore.emit)
        card.launch_elevated.connect(self.launch_elevated.emit)
        card.unfavorite.connect(lambda c: self.favorite_removed.emit(c.script.filename))
        self.favorite_cards[filename] = card
        self.favorites_grid.add(card)
        if refresh:
            self.apply_filter()
        return card

    def remove_favorite(self, filename: str) -> None:
        card = self.favorite_cards.pop(filename, None)
        if card is not None:
            self.favorites_grid.remove(card)
            self.apply_filter()

    # -- catégories et recherche / categories and search -------------------------

    def set_category(self, category: str) -> None:
        self.category = category
        if category == "all":
            self.title.setText(tr("Accueil"))
            self.caption.setText(tr("Tous les scripts, rangés par usage. Ctrl+F pour chercher."))
        else:
            _, title, _, subtitle = next(s for s in [*SECTIONS, FAVORITES_SECTION] if s[0] == category)
            self.title.setText(tr(title))
            self.caption.setText(tr(subtitle))
        self.apply_filter()

    def apply_filter(self, _text: str = "") -> None:
        query = self.search.text().strip().lower()
        total = 0
        for key, (box, grid) in self.sections.items():
            count = filter_grid(grid, self.category in ("all", key), query)
            box.setVisible(count > 0)
            # Sur une page de catégorie, le titre de la page suffit.
            # On a category page, the page title is enough.
            self.section_heads[key].setVisible(self.category == "all")
            total += count
        # Favoris : la section reste visible hors recherche, pour pouvoir en ajouter.
        # Favorites: the section stays visible outside a search, so favorites can be added.
        favorites_page = self.category in ("all", FAVORITES)
        count = filter_grid(self.favorites_grid, favorites_page, query)
        show_favorites = favorites_page and (count > 0 or not query)
        self.favorites_box.setVisible(show_favorites)
        self.favorites_empty.setVisible(not self.favorite_cards)
        self.favorites_grid.setVisible(bool(self.favorite_cards))
        self.favorites_title.setVisible(self.category == "all")
        if show_favorites:
            total += max(count, 1)
        show_hero = self.category == "all" and not query
        self.hero.setVisible(show_hero)
        self.hero_gap.setVisible(show_hero)
        self.empty.setVisible(total == 0)
        self.empty_label.setText(
            tr("Aucun script ne correspond à « {query} ».", query=query)
            if query
            else tr("Aucun script dans cette catégorie.")
        )


class JournalDay(QFrame):
    """Carte d'une journée du journal. Les lignes sont dessinées, pas construites
    en widgets : 120 lignes coûtaient ~1 400 widgets, que chaque changement de
    thème devait repasser au crible de la feuille de style.

    Card for one day of the log. The lines are painted, not built
    as widgets: 120 lines cost ~1,400 widgets, which every theme
    change had to run through the style sheet.
    """

    ROW = 42
    PAD = 4

    def __init__(self, entries: list[Entry]) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.entries = entries
        self.setFixedHeight(2 * self.PAD + len(entries) * self.ROW + max(0, len(entries) - 1))
        self._fonts()

    def _fonts(self) -> None:
        self._body = QFont(self.font())
        self._body.setPixelSize(14)
        self._strong = QFont(self._body)
        self._strong.setWeight(QFont.Weight.DemiBold)
        self._caption = QFont(self._body)
        self._caption.setPixelSize(12)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.FontChange:
            self._fonts()
        super().changeEvent(event)

    def row_at(self, y: float) -> int | None:
        index = int((y - self.PAD) // (self.ROW + 1))
        return index if 0 <= index < len(self.entries) else None

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip and isinstance(event, QHelpEvent):
            index = self.row_at(event.pos().y())
            if index is None:
                QToolTip.hideText()
            else:
                QToolTip.showText(event.globalPos(), self.entries[index].text, self)
            return True
        return super().event(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        # fond et bordure de la carte (feuille de style)
        # card background and border (style sheet)
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(AA)
        left, right = 18.0, self.width() - 18.0
        align = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        elide = Qt.TextElideMode.ElideRight
        y = float(self.PAD)
        for index, entry in enumerate(self.entries):
            if index:
                p.fillRect(QRectF(0, y, self.width(), 1), tok("divider"))
                y += 1
            if event.rect().intersects(QRectF(0, y, self.width(), self.ROW).toAlignedRect()):
                middle = y + self.ROW / 2
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(tok("accent" if entry.kind == "info" else entry.kind))
                p.drawEllipse(QRectF(left + 1, middle - 4, 8, 8))
                p.setFont(self._caption)
                p.setPen(tok("text2"))
                p.drawText(QRectF(left + 24, y, 40, self.ROW), align, entry.when.strftime("%H:%M"))
                script, _, result = entry.text.partition(" : ")
                x = left + 78
                p.setFont(self._strong)
                p.setPen(tok("text"))
                metrics = p.fontMetrics()
                script = metrics.elidedText(script, elide, int((right - x) * 0.6))
                width = metrics.horizontalAdvance(script)
                p.drawText(QRectF(x, y, width + 1, self.ROW), align, script)
                x += width + 14
                p.setFont(self._body)
                p.setPen(tok("text2"))
                result = p.fontMetrics().elidedText(result, elide, int(max(0.0, right - x)))
                p.drawText(QRectF(x, y, max(0.0, right - x), self.ROW), align, result)
            y += self.ROW


class JournalPage(QWidget):
    """Lancements récents, regroupés par jour. Reconstruite seulement quand elle
    est affichée : un lancement pendant qu'on regarde l'accueil ne coûte rien.

    Recent runs, grouped by day. Rebuilt only when it is
    shown: a run while looking at the home page costs nothing.
    """

    def __init__(self, entries: list[Entry]) -> None:
        super().__init__()
        self.entries = entries[:JOURNAL_LIMIT]
        self._dirty = True
        body = QWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(page_scroller(body))
        layout = QVBoxLayout(body)
        layout.setContentsMargins(36, 26, 36, 36)
        layout.setSpacing(0)
        layout.addWidget(label(tr("Journal"), "title"))
        layout.addSpacing(2)
        layout.addWidget(label(tr("Lancements récents, d’après launcher.log."), "body2"))
        layout.addSpacing(22)
        content = QWidget()
        self.layout_ = QVBoxLayout(content)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        layout.addWidget(content)
        layout.addStretch(1)

    def add(self, entry: Entry) -> None:
        self.entries.insert(0, entry)
        del self.entries[JOURNAL_LIMIT:]
        if self.isVisible():
            self.rebuild()
        else:
            self._dirty = True

    def showEvent(self, event: QShowEvent) -> None:
        if self._dirty:
            self.rebuild()
        super().showEvent(event)

    def rebuild(self) -> None:
        self._dirty = False
        while self.layout_.count():
            item = self.layout_.takeAt(self.layout_.count() - 1)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        if not self.entries:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(0, 60, 0, 0)
            empty_layout.addWidget(IconView("history", 40, "text3"), 0, Qt.AlignmentFlag.AlignHCenter)
            text = label(tr("Aucun lancement pour l’instant."), "body2")
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(text)
            self.layout_.addWidget(empty)
            return
        today = date.today()
        groups: dict[date, list[Entry]] = {}
        for entry in self.entries:
            groups.setdefault(entry.when.date(), []).append(entry)
        for day, items in groups.items():
            if day == today:
                name = tr("Aujourd’hui")
            elif day == today - timedelta(days=1):
                name = tr("Hier")
            else:
                name = day.strftime(tr("%d/%m/%Y"))
            self.layout_.addWidget(label(name, "strong"))
            self.layout_.addSpacing(8)
            self.layout_.addWidget(JournalDay(items))
            self.layout_.addSpacing(22)


class SettingsCard(QFrame):
    def __init__(self, icon: str, title: str, description: str, control: QWidget | None = None) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(70)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(16)
        layout.addWidget(IconView(icon, 20))
        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(label(title))
        self.description = label(description, "caption", wrap=True)
        text.addWidget(self.description)
        layout.addLayout(text, 1)
        if control is not None:
            layout.addWidget(control)


class Swatch(QAbstractButton):
    def __init__(self, color: str) -> None:
        super().__init__()
        self.color = color
        self.setCheckable(True)
        self.setFixedSize(30, 30)
        self.setToolTip(color)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        if self.isChecked():
            p.setPen(QPen(tok("text"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(1, 1, 28, 28))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(QRectF(5, 5, 20, 20))
        if self.isChecked():
            paint_icon(p, "check", QRectF(8, 8, 14, 14), QColor("white"), 2.2)


class SettingsPage(QWidget):
    mode_changed = Signal(str)
    language_changed = Signal(str)
    accent_changed = Signal(str)
    mica_changed = Signal(bool)
    transparency_changed = Signal(int)
    relaunch_requested = Signal()
    restore_auto_changed = Signal(bool)
    restore_now_requested = Signal()
    restore_cleanup_requested = Signal()
    update_check_changed = Signal(bool)
    update_check_requested = Signal()
    update_install_requested = Signal()

    def __init__(
        self,
        mode: str,
        accent: str,
        mica: bool,
        scripts_dir: Path,
        data_dir: Path,
        admin: bool,
        restore_auto: bool = False,
        cleanup_available: bool = False,
        transparency: int = 0,
        language: str = "system",
        update_check: bool = True,
    ) -> None:
        super().__init__()
        body = QWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(page_scroller(body))
        layout = QVBoxLayout(body)
        layout.setContentsMargins(36, 26, 36, 36)
        layout.setSpacing(4)
        layout.addWidget(label(tr("Paramètres"), "title"))
        layout.addSpacing(22)

        layout.addWidget(label(tr("Apparence"), "strong"))
        layout.addSpacing(6)
        self.combo = FluentCombo()
        self.combo.addItem(tr("Clair"), "light")
        self.combo.addItem(tr("Sombre"), "dark")
        self.combo.addItem(tr("Utiliser le paramètre système"), "system")
        self.combo.setCurrentIndex(max(0, self.combo.findData(mode)))
        self.combo.currentIndexChanged.connect(lambda _i: self.mode_changed.emit(self.combo.currentData()))
        layout.addWidget(
            SettingsCard(
                "palette", tr("Thème de l’application"), tr("Clair, sombre ou comme Windows."), self.combo
            )
        )

        self.language = FluentCombo()
        self.language.addItem(tr("Utiliser la langue du système"), "system")
        # Chaque langue est écrite dans sa propre langue, pour qu'on la retrouve toujours.
        # Each language is written in its own language, so it can always be found.
        self.language.addItem("Français", "fr")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(max(0, self.language.findData(language)))
        self.language.currentIndexChanged.connect(
            lambda _i: self.language_changed.emit(self.language.currentData())
        )
        layout.addWidget(
            SettingsCard(
                "globe",
                tr("Langue"),
                tr("Français, anglais ou comme Windows. Appliquée au prochain démarrage."),
                self.language,
            )
        )

        swatches = QWidget()
        swatch_layout = QHBoxLayout(swatches)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setSpacing(4)
        group = QButtonGroup(self)
        self.swatches: list[Swatch] = []
        for color in ACCENTS:
            swatch = Swatch(color)
            swatch.setChecked(color.lower() == accent.lower())
            swatch.clicked.connect(lambda _c=False, value=color: self.accent_changed.emit(value))
            group.addButton(swatch)
            swatch_layout.addWidget(swatch)
            self.swatches.append(swatch)
        layout.addWidget(
            SettingsCard(
                "sparkle",
                tr("Couleur d’accentuation"),
                tr("Boutons, sélection et bandeau d’accueil."),
                swatches,
            )
        )

        self.mica = ToggleSwitch()
        self.mica.set_checked_silently(mica)
        backdrop = windows_build() >= BACKDROP_BUILD
        self.mica.setEnabled(backdrop)
        self.mica.toggled.connect(self.mica_changed.emit)
        layout.addWidget(
            SettingsCard(
                "window",
                tr("Effet Mica"),
                tr(
                    "Laisse transparaître le fond d’écran, comme les applis Windows 11. "
                    "Appliqué au prochain démarrage."
                )
                if backdrop
                else tr("Disponible sous Windows 11 uniquement."),
                self.mica,
            )
        )

        slider_box = QWidget()
        slider_layout = QHBoxLayout(slider_box)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(12)
        self.transparency = QSlider(Qt.Orientation.Horizontal)
        self.transparency.setRange(0, TRANSPARENCY_MAX)
        self.transparency.setSingleStep(5)
        self.transparency.setPageStep(10)
        self.transparency.setFixedWidth(200)
        self.transparency.setCursor(Qt.CursorShape.PointingHandCursor)
        self.transparency.setAccessibleName(tr("Transparence"))
        self.transparency_value = label("", "body2")
        self.transparency_value.setMinimumWidth(40)
        self.transparency_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.transparency.setValue(min(max(transparency, 0), TRANSPARENCY_MAX))
        self._show_transparency(self.transparency.value())
        self.transparency.valueChanged.connect(self._transparency_moved)
        slider_layout.addWidget(self.transparency)
        slider_layout.addWidget(self.transparency_value)
        layout.addWidget(
            SettingsCard(
                "opacity",
                tr("Transparence"),
                tr(
                    "Rend le fond, le panneau et les cartes translucides ; le texte reste net. "
                    "Windows floute ce qui se trouve derrière la fenêtre (ou montre Mica s’il est activé)."
                )
                if backdrop
                else tr("Rend toute la fenêtre transparente (le flou n’existe qu’à partir de Windows 11)."),
                slider_box,
            )
        )

        layout.addSpacing(18)
        layout.addWidget(label(tr("Sécurité"), "strong"))
        layout.addSpacing(6)
        self.restore_auto = ToggleSwitch()
        self.restore_auto.set_checked_silently(restore_auto)
        self.restore_auto.toggled.connect(self.restore_auto_changed.emit)
        layout.addWidget(
            SettingsCard(
                "shield",
                tr("Point de restauration automatique"),
                tr(
                    "Avant chaque script qui demande les droits administrateur ou modifie le Registre "
                    "(flèches des raccourcis, WinUtil). Si la création échoue, le script n’est pas lancé."
                ),
                self.restore_auto,
            )
        )
        restore_buttons = QWidget()
        restore_layout = QHBoxLayout(restore_buttons)
        restore_layout.setContentsMargins(0, 0, 0, 0)
        restore_layout.setSpacing(8)
        self.restore_now = QPushButton(tr("Créer"))
        self.restore_now.setEnabled(IS_WINDOWS)
        self.restore_now.clicked.connect(self.restore_now_requested.emit)
        open_rstrui = QPushButton(tr("Restaurer…"))
        open_rstrui.setEnabled(IS_WINDOWS)
        open_rstrui.setToolTip(tr("Ouvre la Restauration du système de Windows"))
        open_rstrui.clicked.connect(open_system_restore)
        cleanup = QPushButton(tr("Nettoyer…"))
        cleanup.setEnabled(IS_WINDOWS and cleanup_available)
        cleanup.setToolTip(tr("Supprime tous les points sauf le plus récent, après confirmation"))
        cleanup.clicked.connect(self.restore_cleanup_requested.emit)
        restore_layout.addWidget(self.restore_now)
        restore_layout.addWidget(cleanup)
        restore_layout.addWidget(open_rstrui)
        layout.addWidget(
            SettingsCard(
                "undo",
                tr("Points de restauration"),
                tr(
                    "Crée un point maintenant, supprime les anciens pour libérer de la place (le plus "
                    "récent est gardé), ou ouvre la Restauration du système pour revenir à un point."
                ),
                restore_buttons,
            )
        )

        layout.addSpacing(18)
        layout.addWidget(label(tr("Compte"), "strong"))
        layout.addSpacing(6)
        relaunch = QPushButton(tr("Administrateur : actif") if admin else tr("Relancer en administrateur"))
        relaunch.setEnabled(not admin)
        relaunch.clicked.connect(self.relaunch_requested.emit)
        layout.addWidget(
            SettingsCard(
                "shield",
                tr("Droits administrateur"),
                tr(
                    "Inutile en temps normal : chaque script demande lui-même l’élévation "
                    "quand il en a besoin."
                ),
                relaunch,
            )
        )

        layout.addSpacing(18)
        layout.addWidget(label(tr("Dossiers"), "strong"))
        layout.addSpacing(6)
        for icon, title, folder in (
            ("folder", tr("Dossier des scripts"), scripts_dir),
            ("history", tr("Réglages et journal"), data_dir),
        ):
            button = QPushButton(tr("Ouvrir"))
            button.clicked.connect(lambda _c=False, f=folder: open_folder(f))
            layout.addWidget(SettingsCard(icon, title, str(folder), button))

        layout.addSpacing(18)
        layout.addWidget(label(tr("Mises à jour"), "strong"))
        layout.addSpacing(6)
        self.update_auto = ToggleSwitch()
        self.update_auto.set_checked_silently(update_check)
        self.update_auto.toggled.connect(self.update_check_changed.emit)
        layout.addWidget(
            SettingsCard(
                "globe",
                tr("Rechercher les mises à jour au démarrage"),
                tr("Interroge les releases GitHub du projet à chaque lancement, sans rien installer."),
                self.update_auto,
            )
        )
        update_buttons = QWidget()
        update_layout = QHBoxLayout(update_buttons)
        update_layout.setContentsMargins(0, 0, 0, 0)
        update_layout.setSpacing(8)
        self.update_check = QPushButton(tr("Rechercher"))
        self.update_check.clicked.connect(self.update_check_requested.emit)
        self.update_install = QPushButton(tr("Installer"))
        self.update_install.setProperty("accent", True)
        self.update_install.clicked.connect(self.update_install_requested.emit)
        self.update_install.hide()
        update_layout.addWidget(self.update_check)
        update_layout.addWidget(self.update_install)
        self.update_card = SettingsCard(
            "undo",
            tr("Version {version}", version=__version__),
            tr("Pas encore vérifié."),
            update_buttons,
        )
        layout.addWidget(self.update_card)

        layout.addSpacing(18)
        layout.addWidget(label(tr("À propos"), "strong"))
        layout.addSpacing(6)
        layout.addWidget(
            SettingsCard(
                "info",
                f"Script Manager {__version__}",
                tr(
                    "© 2026 Bulls64, licence MIT. Code source : github.com/Bulls64/Script-Manager. "
                    "WinUtil et Super God Mode restent soumis à leurs propres licences."
                ),
            )
        )
        layout.addStretch(1)

    def set_update_status(self, text: str, busy: bool = False, install: str = "") -> None:
        """Texte de la carte des mises à jour ; ``install`` : libellé du bouton d'action, vide = masqué.

        Update card text; ``install``: action button label, empty = hidden.
        """
        self.update_card.description.setText(text)
        self.update_check.setEnabled(not busy)
        self.update_install.setEnabled(not busy)
        self.update_install.setText(install)
        self.update_install.setVisible(bool(install))

    def _show_transparency(self, value: int) -> None:
        self.transparency_value.setText(tr("{value} %", value=value))

    def _transparency_moved(self, value: int) -> None:
        self._show_transparency(value)
        self.transparency_changed.emit(value)

    def set_restore_busy(self, busy: bool) -> None:
        self.restore_now.setEnabled(IS_WINDOWS and not busy)
        self.restore_now.setText(tr("Création…") if busy else tr("Créer"))

    def select_accent(self, accent: str) -> None:
        for swatch in self.swatches:
            swatch.setChecked(swatch.color.lower() == accent.lower())
