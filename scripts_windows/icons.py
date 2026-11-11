"""Icônes vectorielles au trait, style Fluent, dessinées dans une boîte de 20 x 20.

Dessinées par QPainter : elles s'affichent même sans les polices Segoe Fluent Icons.

Line-art vector icons, Fluent style, drawn in a 20 x 20 box.

Drawn with QPainter: they show up even without the Segoe Fluent Icons font.
"""

from __future__ import annotations

import functools
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

AA = QPainter.RenderHint.Antialiasing


@functools.cache
def _icon_paths(name: str) -> tuple[QPainterPath, QPainterPath | None]:
    """Tracés d'une icône, construits une seule fois puis réutilisés (lecture seule).

    Paths of an icon, built once and then reused (read-only).
    """
    s, f = QPainterPath(), QPainterPath()
    if name == "home":
        s.moveTo(2.5, 9.5)
        s.lineTo(10, 3)
        s.lineTo(17.5, 9.5)
        s.moveTo(4.5, 8)
        s.lineTo(4.5, 17)
        s.lineTo(15.5, 17)
        s.lineTo(15.5, 8)
        s.moveTo(8.25, 17)
        s.lineTo(8.25, 12.5)
        s.lineTo(11.75, 12.5)
        s.lineTo(11.75, 17)
    elif name == "desktop":
        s.addRoundedRect(2.5, 3.5, 15, 10, 1.5, 1.5)
        s.moveTo(10, 13.5)
        s.lineTo(10, 16.5)
        s.moveTo(6.5, 16.5)
        s.lineTo(13.5, 16.5)
    elif name == "key":
        s.addEllipse(QPointF(6.5, 13.5), 3.5, 3.5)
        s.moveTo(9, 11)
        s.lineTo(16.5, 3.5)
        s.moveTo(14, 6)
        s.lineTo(16, 8)
        s.moveTo(11.75, 8.25)
        s.lineTo(13.25, 9.75)
    elif name == "globe":
        s.addEllipse(QPointF(10, 10), 7.5, 7.5)
        s.addEllipse(QPointF(10, 10), 3.2, 7.5)
        s.moveTo(2.5, 10)
        s.lineTo(17.5, 10)
    elif name == "power":
        rect = QRectF(3.5, 4.5, 13, 13)
        s.arcMoveTo(rect, 120)
        s.arcTo(rect, 120, 300)
        s.moveTo(10, 2.5)
        s.lineTo(10, 9.5)
    elif name == "folder":
        s.moveTo(2.5, 15.5)
        s.lineTo(2.5, 4.5)
        s.lineTo(7.5, 4.5)
        s.lineTo(9.5, 6.5)
        s.lineTo(17.5, 6.5)
        s.lineTo(17.5, 15.5)
        s.closeSubpath()
    elif name == "history":
        rect = QRectF(2.5, 2.5, 15, 15)
        s.arcMoveTo(rect, 160)
        s.arcTo(rect, 160, -320)
        s.moveTo(2.2, 6.2)
        s.lineTo(3.2, 9.1)
        s.lineTo(6, 8)
        s.moveTo(10, 6)
        s.lineTo(10, 10)
        s.lineTo(12.8, 11.8)
    elif name == "settings":
        pts = []
        for i in range(32):
            angle = i / 32 * 2 * math.pi
            radius = 7.6 if (i % 4) in (0, 1) else 5.9
            pts.append(QPointF(10 + radius * math.cos(angle + 0.2), 10 + radius * math.sin(angle + 0.2)))
        s.moveTo(pts[0])
        for point in pts[1:]:
            s.lineTo(point)
        s.closeSubpath()
        s.addEllipse(QPointF(10, 10), 2.4, 2.4)
    elif name == "search":
        s.addEllipse(QPointF(8.5, 8.5), 5.2, 5.2)
        s.moveTo(12.3, 12.3)
        s.lineTo(17, 17)
    elif name == "play":
        f.moveTo(6, 4)
        f.lineTo(16, 10)
        f.lineTo(6, 16)
        f.closeSubpath()
    elif name == "check":
        s.moveTo(4, 10.5)
        s.lineTo(8, 14.5)
        s.lineTo(16, 5.5)
    elif name == "close":
        s.moveTo(5.5, 5.5)
        s.lineTo(14.5, 14.5)
        s.moveTo(14.5, 5.5)
        s.lineTo(5.5, 14.5)
    elif name == "more":
        for x in (4.5, 10, 15.5):
            f.addEllipse(QPointF(x, 10), 1.3, 1.3)
    elif name == "menu":
        for y in (5.5, 10, 14.5):
            s.moveTo(3, y)
            s.lineTo(17, y)
    elif name == "moon":
        a = QPainterPath()
        a.addEllipse(QPointF(10, 10), 7, 7)
        b = QPainterPath()
        b.addEllipse(QPointF(14.5, 6.5), 6, 6)
        s = a.subtracted(b)
    elif name == "sun":
        s.addEllipse(QPointF(10, 10), 3.5, 3.5)
        for i in range(8):
            angle = i / 8 * 2 * math.pi
            s.moveTo(10 + 6 * math.cos(angle), 10 + 6 * math.sin(angle))
            s.lineTo(10 + 8 * math.cos(angle), 10 + 8 * math.sin(angle))
    elif name == "sparkle":
        star = [
            (10.0, 2.0),
            (11.8, 8.2),
            (18.0, 10.0),
            (11.8, 11.8),
            (10.0, 18.0),
            (8.2, 11.8),
            (2.0, 10.0),
            (8.2, 8.2),
        ]
        s.moveTo(*star[0])
        for x, y in star[1:]:
            s.lineTo(x, y)
        s.closeSubpath()
    elif name == "shield":
        s.moveTo(10, 2.5)
        s.lineTo(16.5, 5)
        s.lineTo(16.5, 10)
        s.cubicTo(16.5, 14, 13.5, 16.5, 10, 17.5)
        s.cubicTo(6.5, 16.5, 3.5, 14, 3.5, 10)
        s.lineTo(3.5, 5)
        s.closeSubpath()
    elif name == "undo":
        s.moveTo(7, 4)
        s.lineTo(3.5, 7.5)
        s.lineTo(7, 11)
        s.moveTo(3.5, 7.5)
        s.lineTo(12, 7.5)
        s.cubicTo(15, 7.5, 17, 9.5, 17, 12)
        s.cubicTo(17, 14.5, 15, 16.5, 12, 16.5)
        s.lineTo(8, 16.5)
    elif name == "grid":
        for x, y in ((3, 3), (11, 3), (3, 11), (11, 11)):
            s.addRoundedRect(x, y, 6, 6, 1.5, 1.5)
    elif name == "toolbox":
        s.addRoundedRect(2.5, 7, 15, 9.5, 1.5, 1.5)
        s.moveTo(7.5, 7)
        s.lineTo(7.5, 4.5)
        s.lineTo(12.5, 4.5)
        s.lineTo(12.5, 7)
        s.moveTo(2.5, 11)
        s.lineTo(17.5, 11)
    elif name == "copy":
        s.addRoundedRect(6.5, 6.5, 10, 10, 2, 2)
        s.moveTo(3.5, 13)
        s.lineTo(3.5, 5)
        s.quadTo(3.5, 3.5, 5, 3.5)
        s.lineTo(13, 3.5)
    elif name == "chevron":
        s.moveTo(6, 8)
        s.lineTo(10, 12)
        s.lineTo(14, 8)
    elif name == "palette":
        s.moveTo(10, 2.5)
        s.cubicTo(5.5, 2.5, 2.5, 6, 2.5, 10)
        s.cubicTo(2.5, 14.5, 6, 17.5, 9.5, 17.5)
        s.cubicTo(11.5, 17.5, 11.5, 15.5, 10.5, 14.5)
        s.cubicTo(9.5, 13, 10.5, 12, 12, 12)
        s.lineTo(14, 12)
        s.cubicTo(16, 12, 17.5, 10.5, 17.5, 8.5)
        s.cubicTo(17.5, 5, 14.5, 2.5, 10, 2.5)
        for x, y in ((6.5, 9), (9, 6), (13, 6.5)):
            f.addEllipse(QPointF(x, y), 1.1, 1.1)
    elif name == "window":
        s.addRoundedRect(2.5, 3.5, 15, 13, 2, 2)
        s.moveTo(2.5, 7)
        s.lineTo(17.5, 7)
    elif name == "terminal":
        s.addRoundedRect(2.5, 3.5, 15, 13, 2, 2)
        s.moveTo(6, 8)
        s.lineTo(8.5, 10.25)
        s.lineTo(6, 12.5)
        s.moveTo(10.5, 12.5)
        s.lineTo(14, 12.5)
    elif name == "delete":
        s.moveTo(3, 5.5)
        s.lineTo(17, 5.5)
        s.moveTo(7.5, 5.5)
        s.lineTo(7.5, 3.5)
        s.lineTo(12.5, 3.5)
        s.lineTo(12.5, 5.5)
        s.moveTo(4.75, 5.5)
        s.lineTo(5.75, 16.5)
        s.lineTo(14.25, 16.5)
        s.lineTo(15.25, 5.5)
        s.moveTo(8.5, 8.5)
        s.lineTo(8.5, 13.5)
        s.moveTo(11.5, 8.5)
        s.lineTo(11.5, 13.5)
    elif name == "star":
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = 7.6 if i % 2 == 0 else 3.4
            points.append(QPointF(10 + radius * math.cos(angle), 10.6 + radius * math.sin(angle)))
        s.moveTo(points[0])
        for point in points[1:]:
            s.lineTo(point)
        s.closeSubpath()
    elif name == "add":
        s.moveTo(10, 4)
        s.lineTo(10, 16)
        s.moveTo(4, 10)
        s.lineTo(16, 10)
    elif name == "opacity":
        # Cercle à moitié plein : opaque d'un côté, transparent de l'autre.
        # Half-filled circle: opaque on one side, transparent on the other.
        s.addEllipse(QPointF(10, 10), 7.5, 7.5)
        f.moveTo(10, 2.5)
        f.arcTo(QRectF(2.5, 2.5, 15, 15), 90, 180)
        f.closeSubpath()
    elif name == "info":
        s.addEllipse(QPointF(10, 10), 7.5, 7.5)
        s.moveTo(10, 9)
        s.lineTo(10, 14)
        f.addEllipse(QPointF(10, 6.4), 1, 1)
    return s, (f if not f.isEmpty() else None)


def paint_icon(p: QPainter, name: str, rect: QRectF, color: QColor, stroke: float = 1.4) -> None:
    stroke_path, fill_path = _icon_paths(name)
    scale = min(rect.width(), rect.height()) / 20
    p.save()
    p.setRenderHint(AA)
    p.translate(rect.topLeft())
    p.scale(scale, scale)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(stroke_path)
    if fill_path is not None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(fill_path)
    p.restore()
