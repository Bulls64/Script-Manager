"""Fenêtre principale : navigation, pages et lancement réel des scripts.

Main window: navigation, pages and actual script launching.
"""

from __future__ import annotations

import contextlib
import ctypes
import logging
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QLibraryInfo,
    QPropertyAnimation,
    Qt,
    QTimer,
    QTranslator,
)
from PySide6.QtGui import (
    QCloseEvent,
    QFont,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QResizeEvent,
    QShortcut,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import core, i18n
from .cards import ArrowsCard, ScriptCard
from .core import (
    APP_NAME,
    IS_WINDOWS,
    MANIFEST_NAME,
    Entry,
    RunningScript,
    Script,
    Settings,
)
from .i18n import tr
from .pages import SECTIONS, JournalPage, ScriptsPage, SettingsPage
from .theme import QSS, Theme, make_tokens, system_prefers_dark
from .widgets import InfoBar, NavItem

log = logging.getLogger("scripts_windows")
POLL_MS = 500
DWMWA_USE_IMMERSIVE_DARK_MODE = (20, 19)  # 19 : Windows 10 avant 20H1 / 19: Windows 10 before 20H1
DWMWA_SYSTEMBACKDROP_TYPE = 38
LANGUAGE_NOTICE = {
    "fr": ("Langue", "Script Manager passera en français au prochain démarrage."),
    "en": ("Language", "Script Manager will switch to English the next time it starts."),
}
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2  # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic


Card = ScriptCard | ArrowsCard


def sentence(text: str) -> str:
    """Première lettre en majuscule (les textes du journal commencent en minuscule).

    First letter capitalized (log texts start in lowercase).
    """
    return text[:1].upper() + text[1:]


@dataclass
class Job:
    """Processus suivi : un script, ou un point de restauration (suivi ou non d'un script).

    Tracked process: a script, or a restore point (followed or not by a script).
    """

    process: RunningScript
    card: Card | None
    script: Script | None
    restore: bool = False


class MainWindow(QWidget):
    PANE_OPEN, PANE_COMPACT = 288, 56

    def __init__(
        self,
        scripts: list[Script],
        settings: Settings,
        settings_path: Path | None,
        app_dir: Path,
        data_dir: Path,
    ) -> None:
        super().__init__()
        self.scripts = scripts
        self.settings = settings
        self.settings_path = settings_path
        self.app_dir = app_dir
        self.scripts_dir = core.scripts_dir(app_dir)
        self.admin = core.is_admin()
        # Windows 11 : fond de fenêtre transparent, Windows dessine Mica ou Acrylic derrière.
        # Sinon, la transparence s'applique à toute la fenêtre (setWindowOpacity).
        # Windows 11: transparent window background, Windows draws Mica or Acrylic behind it.
        # Otherwise, transparency applies to the whole window (setWindowOpacity).
        self.backdrop = core.windows_build() >= core.BACKDROP_BUILD
        self.mica = settings.mica and self.backdrop
        self.user_compact: bool | None = None
        # Script en cours (ou point de restauration) -> processus suivi
        # Running script (or restore point) -> tracked process
        self.running: dict[str, Job] = {}

        self.setObjectName("Root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        if self.backdrop:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(APP_NAME)
        icon = core.resource_path("assets/app.ico")
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width, height = 1240, 820
        if available is not None:
            width, height = min(width, available.width() - 40), min(height, available.height() - 60)
        self.resize(width, height)
        self.setMinimumSize(760, 560)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_pane())

        # Couche de contenu, au coin supérieur gauche arrondi.
        # Content layer, with a rounded top-left corner.
        layer = QFrame()
        layer.setObjectName("Layer")
        layer_layout = QVBoxLayout(layer)
        layer_layout.setContentsMargins(0, 0, 0, 0)
        layer_layout.setSpacing(0)
        self.info = InfoBar()
        self.info_host = QWidget()
        info_layout = QVBoxLayout(self.info_host)
        info_layout.setContentsMargins(36, 16, 36, 0)
        info_layout.addWidget(self.info)
        self.info.closed.connect(lambda: self.info_host.setVisible(False))
        self.info_host.setVisible(False)
        layer_layout.addWidget(self.info_host)

        self.stack = QStackedWidget()
        integrated = {s.filename.lower() for s in scripts}
        favorites = [name for name in settings.favorites if name.lower() not in integrated]
        self.scripts_page = ScriptsPage(
            scripts, self.scripts_dir, self.admin, core.arrows_hidden(), favorites
        )
        self.scripts_page.launch.connect(self.launch_card)
        self.scripts_page.launch_elevated.connect(self.launch_elevated)
        self.scripts_page.favorite_added.connect(self.add_favorite)
        self.scripts_page.favorite_removed.connect(self.remove_favorite)
        self.scripts_page.launch_with_restore.connect(lambda card: self.launch_card(card, restore=True))
        self.scripts_page.arrows.connect(self.toggle_arrows)
        self.journal_page = JournalPage(core.read_journal(data_dir))
        self.settings_page = SettingsPage(
            settings.theme,
            settings.accent,
            self.mica,
            self.scripts_dir,
            data_dir,
            self.admin,
            settings.restore_point,
            core.RESTORE_CLEANUP in self.scripts_page.script_cards,
            settings.transparency,
            settings.language,
        )
        self.settings_page.mode_changed.connect(self.set_mode)
        self.settings_page.accent_changed.connect(self.set_accent)
        self.settings_page.mica_changed.connect(self.set_mica)
        self.settings_page.transparency_changed.connect(self.set_transparency)
        self.settings_page.language_changed.connect(self.set_language)
        # Pendant qu'on fait glisser le curseur : thème regroupé, enregistrement différé.
        # While the slider is dragged: theme updates grouped, saving delayed.
        self._theme_timer = QTimer(self)
        self._theme_timer.setSingleShot(True)
        self._theme_timer.setInterval(30)
        self._theme_timer.timeout.connect(self.apply_theme)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save)
        self.settings_page.relaunch_requested.connect(self.relaunch_as_admin)
        self.settings_page.restore_auto_changed.connect(self.set_restore_auto)
        self.settings_page.restore_now_requested.connect(lambda: self._start_restore(None, None))
        self.settings_page.restore_cleanup_requested.connect(self.clean_restore_points)
        for page in (self.scripts_page, self.journal_page, self.settings_page):
            self.stack.addWidget(page)
        layer_layout.addWidget(self.stack)
        root.addWidget(layer, 1)

        self._pane_anim = QPropertyAnimation(self, b"paneWidth", self)
        self._pane_anim.setDuration(180)
        self._pane_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._poll = QTimer(self)
        self._poll.setInterval(POLL_MS)
        self._poll.timeout.connect(self._watch)

        with contextlib.suppress(AttributeError):
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                lambda _scheme: self.apply_theme() if self.settings.theme == "system" else None
            )
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+,"), self, lambda: self.nav[-1].click())

        self.nav[0].setChecked(True)
        self.apply_theme()
        if not self.scripts_dir.is_dir():
            QTimer.singleShot(
                0,
                lambda: self.notify(
                    "critical",
                    tr("Dossier des scripts introuvable"),
                    tr("Les scripts doivent être dans {folder}.", folder=self.scripts_dir),
                ),
            )
        exposed = core.exposed_location(self.scripts_dir) if self.scripts_dir.is_dir() else None
        if exposed:
            QTimer.singleShot(
                0,
                lambda: self.notify(
                    "caution",
                    tr("Dossier des scripts exposé"),
                    tr(
                        "Les scripts administrateur sont lancés depuis {folder}, mais {reason} : d’autres "
                        "programmes peuvent les modifier. Range Script Manager dans un dossier à toi, "
                        "sur un disque interne.",
                        folder=self.scripts_dir,
                        reason=exposed,
                    ),
                ),
            )
        if not IS_WINDOWS:
            for card in [
                *self.scripts_page.script_cards.values(),
                *self.scripts_page.favorite_cards.values(),
            ]:
                card.button.setEnabled(False)
            if self.scripts_page.arrows_card is not None:
                self.scripts_page.arrows_card.switch.setEnabled(False)
            QTimer.singleShot(
                0,
                lambda: self.notify(
                    "caution",
                    tr("Windows requis"),
                    tr("Les scripts ne peuvent être lancés que sous Windows."),
                ),
            )

    # -- volet de navigation / navigation pane ----------------------------------

    def _build_pane(self) -> QWidget:
        self.pane = QWidget()
        self._pane_width = float(self.PANE_OPEN)
        self.pane.setFixedWidth(self.PANE_OPEN)
        pane = QVBoxLayout(self.pane)
        pane.setContentsMargins(4, 6, 4, 8)
        pane.setSpacing(2)
        self.header_item = NavItem("menu", APP_NAME, checkable=False, strong=True)
        self.header_item.setToolTip(tr("Réduire ou agrandir le volet"))
        self.header_item.clicked.connect(self.toggle_pane)
        pane.addWidget(self.header_item)
        pane.addSpacing(10)

        self.nav_group = QButtonGroup(self)
        self.nav: list[NavItem] = []
        used = {script.category for script in self.scripts}
        self._add_nav(pane, "home", tr("Accueil"), ("scripts", "all"))
        for key, title, icon, _subtitle in SECTIONS:
            if key in used:
                self._add_nav(pane, icon, tr(title), ("scripts", key))
        self._add_nav(pane, "star", tr("Favoris"), ("scripts", core.FAVORITES))
        self._add_nav(pane, "history", tr("Journal"), ("journal", ""))
        pane.addStretch(1)
        self.theme_item = NavItem("moon", tr("Thème sombre"), checkable=False)
        self.theme_item.clicked.connect(self.quick_toggle_theme)
        pane.addWidget(self.theme_item)
        self._add_nav(pane, "settings", tr("Paramètres"), ("settings", ""))
        return self.pane

    def _add_nav(self, layout: QVBoxLayout, icon: str, text: str, target: tuple[str, str]) -> None:
        item = NavItem(icon, text)
        item.clicked.connect(lambda _c=False, t=target: self.navigate(*t))
        self.nav_group.addButton(item)
        self.nav.append(item)
        layout.addWidget(item)

    def navigate(self, page: str, category: str) -> None:
        if page == "scripts":
            self.stack.setCurrentWidget(self.scripts_page)
            self.scripts_page.set_category(category)
        elif page == "journal":
            self.stack.setCurrentWidget(self.journal_page)
        else:
            self.stack.setCurrentWidget(self.settings_page)

    def focus_search(self) -> None:
        if self.stack.currentWidget() is not self.scripts_page:
            self.nav[0].click()
        self.scripts_page.search.setFocus()
        self.scripts_page.search.selectAll()

    def _get_pane_width(self) -> float:
        return self._pane_width

    def _set_pane_width(self, value: float) -> None:
        self._pane_width = value
        self.pane.setFixedWidth(int(value))
        compact = value < 140
        # Le changement de largeur redessine déjà les éléments : seul le passage
        # en mode compact a besoin d'être signalé.
        # The width change already repaints the items: only switching
        # to compact mode needs to be signaled.
        for item in (self.header_item, self.theme_item, *self.nav):
            if item.compact != compact:
                item.set_compact(compact)

    paneWidth = Property(float, _get_pane_width, _set_pane_width)

    def toggle_pane(self) -> None:
        compact = self._pane_width > (self.PANE_OPEN + self.PANE_COMPACT) / 2
        self.user_compact = compact
        self._pane_anim.stop()
        self._pane_anim.setStartValue(self._pane_width)
        self._pane_anim.setEndValue(float(self.PANE_COMPACT if compact else self.PANE_OPEN))
        self._pane_anim.start()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Comme NavigationView : volet compact sous 1008 px, sauf choix explicite.
        # Like NavigationView: compact pane below 1008 px, unless chosen explicitly.
        wanted = self.width() < 1008 if self.user_compact is None else self.user_compact
        target = self.PANE_COMPACT if wanted else self.PANE_OPEN
        running = self._pane_anim.state() == QPropertyAnimation.State.Running
        if abs(self._pane_width - target) > 1 and not running:
            self._set_pane_width(float(target))

    # -- thème / theme -----------------------------------------------------------

    def effective_dark(self) -> bool:
        mode = self.settings.theme
        return system_prefers_dark() if mode == "system" else mode == "dark"

    def apply_theme(self) -> None:
        dark = self.effective_dark()
        surfaces = self.settings.transparency if self.backdrop else 0
        Theme.set(dark, make_tokens(dark, self.settings.accent, self.mica, surfaces))
        self.setWindowOpacity(1.0 if self.backdrop else 1.0 - self.settings.transparency / 100)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(QSS % Theme.tokens)
            for widget in app.allWidgets():
                widget.update()
        self.theme_item.icon_name = "sun" if Theme.dark else "moon"
        self.theme_item.setText(tr("Thème clair") if Theme.dark else tr("Thème sombre"))
        self._apply_window_chrome()

    def _save(self) -> None:
        if self.settings_path is not None:
            core.save_settings(self.settings_path, self.settings)

    def quick_toggle_theme(self) -> None:
        self.set_mode("light" if self.effective_dark() else "dark")

    def set_mode(self, mode: str) -> None:
        self.settings.theme = mode
        self._save()
        combo = self.settings_page.combo
        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(mode)))
        combo.blockSignals(False)
        self.apply_theme()

    def set_accent(self, accent: str) -> None:
        self.settings.accent = accent
        self._save()
        self.settings_page.select_accent(accent)
        self.apply_theme()

    def set_mica(self, enabled: bool) -> None:
        self.settings.mica = enabled
        self._save()
        self.notify("info", tr("Effet Mica"), tr("Le changement s’appliquera au prochain démarrage."))

    def set_language(self, choice: str) -> None:
        self.settings.language = choice
        self._save()
        # Message écrit dans la langue choisie : c'est celle que l'on sait lire.
        # Message written in the chosen language: that is the one the user can read.
        title, message = LANGUAGE_NOTICE[i18n.resolve(choice)]
        self.notify("info", title, message)

    def set_transparency(self, value: int) -> None:
        self.settings.transparency = min(max(value, 0), core.TRANSPARENCY_MAX)
        self._save_timer.start()
        self._theme_timer.start()

    def set_restore_auto(self, enabled: bool) -> None:
        self.settings.restore_point = enabled
        self._save()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_window_chrome()

    def _apply_window_chrome(self) -> None:
        """Barre de titre sombre ou claire, et Mica (Windows 10 20H1+ / Windows 11).

        Dark or light title bar, and Mica (Windows 10 20H1+ / Windows 11).
        """
        if not IS_WINDOWS or not self.isVisible():
            return
        try:
            hwnd = int(self.winId())
            for attribute in DWMWA_USE_IMMERSIVE_DARK_MODE:
                if core.set_window_attribute(hwnd, attribute, int(Theme.dark)):
                    break
            if self.backdrop:
                core.extend_frame(hwnd)
                if self.mica:
                    kind = DWMSBT_MAINWINDOW
                elif self.settings.transparency > 0:
                    kind = DWMSBT_TRANSIENTWINDOW
                else:
                    kind = DWMSBT_NONE
                core.set_window_attribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, kind)
        except (AttributeError, OSError, ctypes.ArgumentError):
            pass

    # -- notifications et journal / notifications and log --------------------------

    def notify(self, severity: str, title: str, message: str) -> None:
        self.info_host.setVisible(True)
        self.info.show_message(severity, title, message)

    def record(self, filename: str, text: str, level: int = logging.INFO) -> None:
        """Écrit dans launcher.log et ajoute la ligne à la page Journal.

        Writes to launcher.log and adds the line to the Log page.
        """
        message = f"{filename} : {text}"
        log.log(level, message)
        self.journal_page.add(Entry(datetime.now().replace(microsecond=0), core.classify(message), message))

    # -- lancement des scripts / running scripts -------------------------------------

    def launch_card(self, card: ScriptCard, restore: bool = False) -> None:
        self._start(card.script, card, restore)

    # -- favoris / favorites -----------------------------------------------------

    def add_favorite(self, filename: str) -> None:
        card = self.scripts_page.add_favorite(filename)
        if card is None:
            return
        self.settings.favorites.append(filename)
        self._save()
        self.notify(
            "success", tr("Favori ajouté"), tr("{filename} est dans la section Favoris.", filename=filename)
        )
        if not IS_WINDOWS:
            card.button.setEnabled(False)

    def remove_favorite(self, filename: str) -> None:
        if filename in self.running:
            # carte encore suivie : retrait possible à la fin du script
            # card still tracked: can be removed when the script ends
            return
        self.scripts_page.remove_favorite(filename)
        # Toutes les variantes de casse : sinon le favori reviendrait au prochain démarrage.
        # Every case variant: otherwise the favorite would come back at the next start.
        folded = filename.lower()
        self.settings.favorites = [name for name in self.settings.favorites if name.lower() != folded]
        self._save()
        self.notify(
            "info",
            tr("Favori retiré"),
            tr("{filename} reste dans le dossier des scripts.", filename=filename),
        )

    def launch_elevated(self, card: ScriptCard) -> None:
        """Favori lancé en administrateur, à la demande (menu « … »).

        Favorite run as administrator, on request ("…" menu).
        """
        self._start(replace(card.script, admin=True), card)

    def clean_restore_points(self) -> None:
        """Bouton « Nettoyer… » des Paramètres : lance le script de nettoyage, via sa carte.

        "Nettoyer…" (Clean up) button in Settings: runs the cleanup script, through its card.
        """
        card = self.scripts_page.script_cards.get(core.RESTORE_CLEANUP)
        if card is not None:
            self.launch_card(card)

    def toggle_arrows(self, card: ArrowsCard, hide: bool) -> None:
        script = card.on_script if hide else card.off_script
        if not self._start(script, card):
            # lancement refusé ou impossible : l'interrupteur revient
            # launch declined or impossible: the switch goes back
            card.set_state(not hide)

    def _start(self, script: Script, card: Card, restore: bool = False) -> bool:
        """Lance un script, précédé d'un point de restauration si demandé ou réglé.

        Runs a script, preceded by a restore point if requested or enabled.
        """
        if script.filename in self.running:
            return False
        path = self.scripts_dir / script.filename
        if not path.is_file():
            self.notify(
                "critical",
                tr("Script introuvable"),
                tr(
                    "{path} est absent. Garde les scripts dans le dossier « {folder} ».",
                    path=path,
                    folder=core.SCRIPTS_FOLDER,
                ),
            )
            return False
        if restore or (self.settings.restore_point and core.needs_restore_point(script)):
            return self._start_restore(script, card)
        return self._launch(script, card)

    def _launch(self, script: Script, card: Card) -> bool:
        path = self.scripts_dir / script.filename
        elevate = script.admin and not self.admin
        try:
            process = core.start_script(path, elevate)
        except OSError as exc:
            if core.is_cancelled(exc):
                self._refused(
                    script.filename,
                    tr("Demande administrateur annulée"),
                    tr("{title} n’a pas été lancé.", title=script.title),
                )
            else:
                self._failed(
                    script.filename,
                    tr("lancement impossible ({error})", error=exc),
                    tr("Impossible de lancer le script"),
                    str(exc),
                )
            return False
        self.record(
            script.filename, tr("lancé en administrateur") if (elevate or self.admin) else tr("lancé")
        )
        self.running[script.filename] = Job(process, card, script)
        card.set_running(True)
        self._poll_start()
        return True

    def _start_restore(self, script: Script | None, card: Card | None) -> bool:
        """Crée un point de restauration ; le script éventuel est lancé ensuite.

        Creates a restore point; the script, if any, runs afterwards.
        """
        label = tr(core.RESTORE_LABEL)
        if any(job.restore for job in self.running.values()):
            self.notify(
                "caution", tr("Point de restauration en cours"), tr("Attends la fin de la création en cours.")
            )
            return False
        not_launched = " " + tr("{title} n’a pas été lancé.", title=script.title) if script else ""
        if not (self.scripts_dir / core.RESTORE_SCRIPT).is_file():
            self.notify(
                "critical",
                tr("Script introuvable"),
                tr("{filename} est absent du dossier des scripts.", filename=core.RESTORE_SCRIPT)
                + not_launched,
            )
            return False
        target = tr("avant {filename}", filename=script.filename) if script else tr("point manuel")
        try:
            process = core.start_restore_point(self.scripts_dir, f"{APP_NAME} : {target}")
        except OSError as exc:
            if core.is_cancelled(exc):
                self._refused(
                    label, tr("Point de restauration annulé"), tr("Élévation refusée.") + not_launched
                )
            else:
                self._failed(
                    label,
                    tr("création impossible ({error})", error=exc),
                    tr("Point de restauration impossible"),
                    f"{exc}.{not_launched}",
                )
            return False
        self.record(label, tr("création lancée ({target})", target=target))
        key = script.filename if script else core.RESTORE_LABEL
        self.running[key] = Job(process, card, script, restore=True)
        if card is not None:
            card.set_running(True, tr("Point de restauration…"))
        self.settings_page.set_restore_busy(True)
        self._poll_start()
        return True

    def _refused(self, name: str, title: str, message: str) -> None:
        """Élévation refusée (UAC) : notée au journal, signalée sans alarme.

        Elevation declined (UAC): written to the log, reported without alarm.
        """
        self.record(name, tr("élévation refusée"))
        self.notify("caution", title, message)

    def _failed(self, name: str, text: str, title: str, message: str) -> None:
        self.record(name, text, logging.ERROR)
        self.notify("critical", title, message)

    def _poll_start(self) -> None:
        if not self._poll.isActive():
            self._poll.start()

    def _watch(self) -> None:
        for key, job in list(self.running.items()):
            code = job.process.poll()
            if code is None:
                continue
            del self.running[key]
            if job.restore:
                self._restore_done(job, code)
            else:
                self._script_done(key, job, code)
        if not any(job.restore for job in self.running.values()):
            self.settings_page.set_restore_busy(False)
        if not self.running:
            self._poll.stop()

    def _release(self, card: Card | None) -> bool:
        """La carte redevient disponible ; l'interrupteur suit le Registre réel.

        Renvoie l'état des flèches lu dans le Registre (False pour une autre carte).

        The card becomes available again; the switch follows the actual Registry.

        Returns the arrow state read from the Registry (False for another card).
        """
        if card is None:
            return False
        card.set_running(False)
        if not isinstance(card, ArrowsCard):
            return False
        hidden = core.arrows_hidden()
        card.set_state(hidden)
        return hidden

    def _restore_done(self, job: Job, code: int) -> None:
        severity, text = core.describe_restore(code)
        self.record(tr(core.RESTORE_LABEL), text, logging.WARNING if severity == "critical" else logging.INFO)
        script = job.script
        if script is None:
            titles = {
                "success": tr("Point de restauration créé"),
                "caution": tr("Point de restauration non créé"),
            }
            self.notify(
                severity,
                titles.get(severity, tr("Échec du point de restauration")),
                f"{sentence(text)}.",
            )
            return
        if not core.restore_allows_launch(code):
            self._release(job.card)
            self.notify(
                severity,
                tr("Script non lancé"),
                tr("Point de restauration : {text}.", text=text)
                + " "
                + tr("{title} n’a pas été lancé.", title=script.title),
            )
            return
        if job.card is None or not self._launch(script, job.card):
            self._release(job.card)
            return
        if code == core.RESTORE_CREATED:
            self.notify(
                "info", tr("Point de restauration créé"), tr("{title} est lancé.", title=script.title)
            )
        else:
            self.notify(
                "caution",
                tr("Point récent conservé"),
                f"{sentence(text)}. " + tr("{title} est lancé.", title=script.title),
            )

    def _script_done(self, filename: str, job: Job, code: int) -> None:
        card = job.card
        severity, text = core.describe_exit(code)
        level = logging.INFO if severity != "critical" else logging.WARNING
        self.record(filename, text, level)
        hidden = self._release(card)
        if isinstance(card, ArrowsCard):
            title = tr("Flèches masquées") if hidden else tr("Flèches visibles")
            if severity != "success":
                title = tr("Flèches des raccourcis inchangées") if severity == "caution" else tr("Échec")
            message = tr("{name} : {text}.", name=filename, text=text)
        else:
            title = {"success": tr("Terminé"), "caution": tr("Fenêtre fermée"), "critical": tr("Échec")}[
                severity
            ]
            name = job.script.title if job.script else filename
            message = tr("{name} : {text}.", name=name, text=text)
        self.notify(severity, title, message)

    def relaunch_as_admin(self) -> None:
        if self.running:
            self.notify(
                "caution",
                tr("Scripts en cours"),
                tr("Attends la fin des scripts en cours avant de relancer l’application."),
            )
            return
        try:
            core.relaunch_as_admin()
        except OSError as exc:
            if core.is_cancelled(exc):
                self.notify(
                    "caution",
                    tr("Demande administrateur annulée"),
                    tr("L’application reste en utilisateur standard."),
                )
            else:
                self.notify("critical", tr("Élévation impossible"), str(exc))
            return
        log.info(tr("Application relancée en administrateur"))
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Les consoles des scripts restent ouvertes : elles ne dépendent pas de l'application.
        # The script consoles stay open: they do not depend on the application.
        if self.running:
            log.info(tr("Fermeture avec %d script(s) encore en cours"), len(self.running))
        # Dernier réglage de transparence pas encore enregistré.
        # Last transparency setting not saved yet.
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save()
        super().closeEvent(event)


def make_app(argv: list[str]) -> QApplication:
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"])
    font.setPixelSize(14)
    app.setFont(font)
    return app


def load_qt_translations(app: QApplication, language: str) -> None:
    """Textes propres à Qt (menu contextuel des champs, boutons des boîtes de dialogue).

    Qt's own texts (field context menu, dialog box buttons).
    """
    if language == "en":
        return
    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(f"qtbase_{language}", folder):
        app.installTranslator(translator)


def main() -> int:
    if IS_WINDOWS:
        # Icône propre dans la barre des tâches (sinon celle de python.exe).
        # Proper taskbar icon (otherwise the python.exe one).
        with contextlib.suppress(AttributeError, OSError):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Bulls64.ScriptsWindows")
    app = make_app(sys.argv)
    data = core.data_dir()
    core.setup_logging(data)
    app_dir = core.find_app_dir()
    settings_path = data / "settings.json"
    settings = core.load_settings(settings_path)
    # La langue est fixée avant de lire scripts.json : titres et erreurs sont traduits.
    # The language is set before reading scripts.json: titles and errors are translated.
    i18n.set_language(settings.language)
    load_qt_translations(app, i18n.language())
    try:
        scripts = core.load_scripts(app_dir / MANIFEST_NAME)
    except core.ManifestError as exc:
        QMessageBox.critical(
            None,
            APP_NAME,
            tr("Impossible de charger {path} :\n{error}", path=app_dir / MANIFEST_NAME, error=exc),
        )
        return 1
    window = MainWindow(scripts, settings, settings_path, app_dir, data)
    window.show()
    return app.exec()
