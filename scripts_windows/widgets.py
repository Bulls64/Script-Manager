"""Contrôles Fluent dessinés à la main : interrupteur, barre de progression,
notification, volet de navigation, bandeau d'accueil…

Hand-painted Fluent controls: switch, progress bar,
notification, navigation pane, home banner…
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .icons import AA, paint_icon
from .theme import tok


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


class IconView(QWidget):
    def __init__(self, name: str, size: int = 20, color: str = "text") -> None:
        super().__init__()
        self.name, self.color = name, color
        self.setFixedSize(size, size)

    def paintEvent(self, _event: object) -> None:
        paint_icon(QPainter(self), self.name, QRectF(self.rect()), tok(self.color))


class IconTile(QWidget):
    """Icône sur une tuile teintée de la couleur d'accentuation.

    Icon on a tile tinted with the accent color.
    """

    def __init__(self, name: str, size: int = 40) -> None:
        super().__init__()
        self.name = name
        self.setFixedSize(size, size)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tok("tile"))
        p.drawRoundedRect(QRectF(self.rect()), 8, 8)
        inset = self.width() * 0.25
        paint_icon(p, self.name, QRectF(self.rect()).adjusted(inset, inset, -inset, -inset), tok("accent"))


class IconButton(QAbstractButton):
    """Bouton discret (fond au survol), comme les boutons « subtle » de WinUI.

    Subtle button (background on hover), like WinUI "subtle" buttons.
    """

    def __init__(self, name: str, tooltip: str = "", size: QSize | None = None) -> None:
        super().__init__()
        self.name = name
        self.setFixedSize(size or QSize(32, 32))
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        if self.isDown() or self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tok("subtle2" if self.isDown() else "subtle"))
            p.drawRoundedRect(QRectF(self.rect()), 4, 4)
        r = QRectF(self.rect())
        paint_icon(p, self.name, QRectF(r.center().x() - 8, r.center().y() - 8, 16, 16), tok("text2"))


class ToggleSwitch(QAbstractButton):
    """Interrupteur WinUI : piste arrondie, curseur animé qui grossit au survol.

    WinUI switch: rounded track, animated thumb that grows on hover.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, value: float) -> None:
        self._pos = value
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def set_checked_silently(self, checked: bool) -> None:
        self.blockSignals(True)
        self.setChecked(checked)
        self.blockSignals(False)
        self._set_knob(1.0 if checked else 0.0)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        track = QRectF(2, 2, 40, 20)
        on = self.isChecked()
        enabled = self.isEnabled()
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tok("accent") if enabled else tok("accent_disabled"))
        else:
            p.setPen(QPen(tok("text2") if enabled else tok("text3"), 1))
            p.setBrush(tok("subtle") if self.underMouse() else Qt.GlobalColor.transparent)
        p.drawRoundedRect(track.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        radius = 7.0 if (self.underMouse() and enabled) else 6.0
        x = 12 + self._pos * 20
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tok("on_accent") if on else (tok("text2") if enabled else tok("text3")))
        p.drawEllipse(QPointF(x, 12), radius, radius)


class ProgressLine(QWidget):
    """Barre de progression indéterminée, fine, comme ProgressBar de WinUI.

    Thin indeterminate progress bar, like the WinUI ProgressBar.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(3)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        # Place gardée une fois masquée : la carte ne change pas de hauteur.
        # Space kept once hidden: the card does not change height.
        policy = self.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(policy)
        self.hide()

    def start(self) -> None:
        self._phase = 0.0
        self.show()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.012) % 1.0
        self.update()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        w = self.width()
        t = self._phase
        eased = t * t * (3 - 2 * t)
        seg = w * 0.38
        x = -seg + eased * (w + seg)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tok("accent"))
        p.drawRoundedRect(QRectF(max(0.0, x), 0.5, min(seg, w - max(0.0, x)), 2.5), 1.25, 1.25)


class FluentCombo(QComboBox):
    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)  # type: ignore[arg-type]
        p = QPainter(self)
        paint_icon(p, "chevron", QRectF(self.width() - 26, self.height() / 2 - 7, 14, 14), tok("text2"))


class SearchBox(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setPlaceholderText(tr("Rechercher un script"))
        self.setClearButtonEnabled(True)
        self.setFixedWidth(300)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)  # type: ignore[arg-type]
        p = QPainter(self)
        paint_icon(p, "search", QRectF(11, self.height() / 2 - 8, 16, 16), tok("text2"))


class InfoBar(QFrame):
    """Notification en ligne (InfoBar WinUI) : succès, info, attention, erreur.

    Inline notification (WinUI InfoBar): success, info, caution, error.
    """

    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.severity = "info"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 6, 6)
        layout.setSpacing(12)
        self._glyph = SeverityGlyph()
        self._title = label("", "strong")
        self._message = label("", "", wrap=True)
        for text in (self._title, self._message):
            text.setMinimumHeight(32)
            text.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        close = IconButton("close", tr("Fermer"))
        close.clicked.connect(self.dismiss)
        layout.addWidget(self._glyph, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._message, 1, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        self.hide()

    def show_message(self, severity: str, title: str, message: str, timeout: int = 7000) -> None:
        self.severity = severity
        self._glyph.severity = severity
        self._title.setText(title)
        self._message.setText(message)
        self.show()
        self.update()
        if timeout:
            self._timer.start(timeout)

    def dismiss(self) -> None:
        self._timer.stop()
        self.hide()
        self.closed.emit()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        background = "card" if self.severity == "info" else f"{self.severity}_bg"
        p.setPen(QPen(tok("card_stroke"), 1))
        p.setBrush(tok(background))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)


class SeverityGlyph(QWidget):
    """Pastille de gravité de l'InfoBar : coche, croix, point d'exclamation ou « i ».

    InfoBar severity badge: check mark, cross, exclamation mark or "i".
    """

    def __init__(self) -> None:
        super().__init__()
        self.severity = "info"
        self.setFixedSize(20, 32)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        p.translate(0, 6)
        color = tok(self.severity if self.severity != "info" else "accent")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawEllipse(QRectF(2, 2, 16, 16))
        inner = tok("on_accent") if self.severity == "info" else tok(f"{self.severity}_bg")
        pen = QPen(inner, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        if self.severity == "success":
            path = QPainterPath(QPointF(6.5, 10.2))
            path.lineTo(9, 12.6)
            path.lineTo(13.6, 7.6)
            p.drawPath(path)
        elif self.severity == "critical":
            p.drawLine(QPointF(7.5, 7.5), QPointF(12.5, 12.5))
            p.drawLine(QPointF(12.5, 7.5), QPointF(7.5, 12.5))
        else:
            top, bottom = (6.5, 10.8) if self.severity == "caution" else (9.2, 13.5)
            p.drawLine(QPointF(10, top), QPointF(10, bottom))
            dot = 13.4 if self.severity == "caution" else 6.6
            p.drawPoint(QPointF(10, dot))


class NavItem(QAbstractButton):
    """Élément du volet de navigation : pilule d'accent à gauche quand sélectionné.

    Navigation pane item: accent pill on the left when selected.
    """

    def __init__(self, icon: str, text: str, checkable: bool = True, strong: bool = False) -> None:
        super().__init__()
        self.icon_name = icon
        self.setText(text)
        self.strong = strong
        self.compact = False
        self.setCheckable(checkable)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._make_fonts()

    def _make_fonts(self) -> None:
        # Polices préparées une fois (et à chaque changement de police), pas à chaque dessin.
        # Fonts prepared once (and on each font change), not on every paint.
        self._text_font = QFont(self.font())
        self._text_font.setPixelSize(14)
        self._text_font.setWeight(QFont.Weight.DemiBold if self.strong else QFont.Weight.Normal)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.FontChange:
            self._make_fonts()
        super().changeEvent(event)

    def set_compact(self, compact: bool) -> None:
        self.compact = compact
        self.setToolTip(self.text() if compact else "")
        self.update()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect()).adjusted(4, 2, -4, -2)
        if self.isChecked() or self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tok("subtle2" if self.isDown() else "subtle"))
            p.drawRoundedRect(r, 4, 4)
        if self.isChecked():
            p.setBrush(tok("accent"))
            p.drawRoundedRect(QRectF(r.left(), r.center().y() - 8, 3, 16), 1.5, 1.5)
        paint_icon(p, self.icon_name, QRectF(r.left() + 15, r.center().y() - 9, 18, 18), tok("text"))
        if self.compact or not self.text():
            return
        p.setFont(self._text_font)
        p.setPen(tok("text"))
        available = int(r.width() - 52)
        text = p.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, available)
        text_rect = QRectF(r.left() + 48, r.top(), available, r.height())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class Hero(QWidget):
    """Bandeau d'accueil : dégradé d'accent, halos lumineux et pastilles « verre ».

    Home banner: accent gradient, light halos and "glass" chips.
    """

    def __init__(self, stats: list[tuple[str, str]]) -> None:
        super().__init__()
        self.setFixedHeight(214)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(6)
        title = QLabel("Script Manager")
        title.setStyleSheet("color: white; font-size: 34px; font-weight: 600;")
        subtitle = QLabel(tr("Raccourcis, Registre et outils Windows, réunis au même endroit."))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 15px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        chips = QHBoxLayout()
        chips.setSpacing(10)
        for icon, text in stats:
            chips.addWidget(GlassChip(icon, text))
        chips.addStretch(1)
        layout.addLayout(chips)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.setClipPath(clip)
        gradient = QLinearGradient(r.topLeft(), r.bottomRight())
        gradient.setColorAt(0, tok("hero_a"))
        gradient.setColorAt(1, tok("hero_b"))
        p.fillRect(r, gradient)
        for cx, cy, rad, alpha in ((0.82, 0.15, 0.42, 70), (0.98, 0.95, 0.30, 55), (0.55, 1.15, 0.28, 40)):
            center = QPointF(r.width() * cx, r.height() * cy)
            radius = r.width() * rad
            glow = QRadialGradient(center, radius)
            glow.setColorAt(0, QColor(255, 255, 255, alpha))
            glow.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(center, radius, radius)
        size = r.height() * 0.95
        paint_icon(
            p,
            "sparkle",
            QRectF(r.right() - size - 28, r.center().y() - size / 2, size, size),
            QColor(255, 255, 255, 46),
            stroke=0.6,
        )
        small = r.height() * 0.32
        paint_icon(
            p,
            "sparkle",
            QRectF(r.right() - size - 70, r.top() + 22, small, small),
            QColor(255, 255, 255, 70),
            0.9,
        )


class GlassChip(QWidget):
    def __init__(self, icon: str, text: str) -> None:
        super().__init__()
        self.icon, self.text = icon, text
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)
        self.setFixedHeight(34)
        self.setFixedWidth(self.fontMetrics().horizontalAdvance(text) + 52)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(AA)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.setBrush(QColor(255, 255, 255, 38))
        p.drawRoundedRect(r, 17, 17)
        paint_icon(p, self.icon, QRectF(12, 9, 16, 16), QColor("white"))
        p.setPen(QColor("white"))
        p.drawText(QRectF(36, 0, r.width() - 40, r.height()), Qt.AlignmentFlag.AlignVCenter, self.text)
