"""Тонкие линейные иконки в духе Lucide: один контур, толщина 2, круглые концы.

Рисуются кодом (24x24, stroke=currentColor) и растрируются через QtSvg —
чёткие на любом размере, перекрашиваются под тему без ассетов.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Каждый элемент: (тег, атрибуты). fill по умолчанию none.
_ICONS: dict[str, list[tuple[str, dict[str, str]]]] = {
    "search": [
        ("circle", {"cx": "11", "cy": "11", "r": "7"}),
        ("line", {"x1": "21", "y1": "21", "x2": "16.65", "y2": "16.65"}),
    ],
    "home": [
        ("path", {"d": "m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"}),
        ("polyline", {"points": "9 22 9 12 15 12 15 22"}),
    ],
    "sparkles": [
        ("path", {"d": "m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"}),
        ("path", {"d": "M19 3v4M17 5h4"}),
    ],
    "layers": [
        ("path", {"d": "m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"}),
        ("path", {"d": "m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"}),
        ("path", {"d": "m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"}),
    ],
    "sliders": [
        ("line", {"x1": "21", "y1": "4", "x2": "14", "y2": "4"}),
        ("line", {"x1": "10", "y1": "4", "x2": "3", "y2": "4"}),
        ("line", {"x1": "21", "y1": "12", "x2": "12", "y2": "12"}),
        ("line", {"x1": "8", "y1": "12", "x2": "3", "y2": "12"}),
        ("line", {"x1": "21", "y1": "20", "x2": "16", "y2": "20"}),
        ("line", {"x1": "12", "y1": "20", "x2": "3", "y2": "20"}),
        ("line", {"x1": "14", "y1": "2", "x2": "14", "y2": "6"}),
        ("line", {"x1": "8", "y1": "10", "x2": "8", "y2": "14"}),
        ("line", {"x1": "16", "y1": "18", "x2": "16", "y2": "22"}),
    ],
    "shuffle": [
        ("path", {"d": "M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.8-1.1 2-1.7 3.3-1.7H22"}),
        ("path", {"d": "m18 2 4 4-4 4"}),
        ("path", {"d": "M2 6h1.9c1.5 0 2.9.9 3.6 2.2"}),
        ("path", {"d": "M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"}),
        ("path", {"d": "m18 14 4 4-4 4"}),
    ],
    "skip-back": [
        ("polygon", {"points": "19 20 9 12 19 4 19 20"}),
        ("line", {"x1": "5", "y1": "19", "x2": "5", "y2": "5"}),
    ],
    "skip-forward": [
        ("polygon", {"points": "5 4 15 12 5 20 5 4"}),
        ("line", {"x1": "19", "y1": "5", "x2": "19", "y2": "19"}),
    ],
    "play": [("polygon", {"points": "7 4.5 19 12 7 19.5 7 4.5"})],
    "pause": [
        ("rect", {"x": "6.5", "y": "4.5", "width": "4", "height": "15", "rx": "1.2", "fill": "currentColor", "stroke": "none"}),
        ("rect", {"x": "13.5", "y": "4.5", "width": "4", "height": "15", "rx": "1.2", "fill": "currentColor", "stroke": "none"}),
    ],
    "repeat": [
        ("path", {"d": "m17 2 4 4-4 4"}),
        ("path", {"d": "M3 11v-1a4 4 0 0 1 4-4h14"}),
        ("path", {"d": "m7 22-4-4 4-4"}),
        ("path", {"d": "M21 13v1a4 4 0 0 1-4 4H3"}),
    ],
    "maximize": [
        ("path", {"d": "M8 3H5a2 2 0 0 0-2 2v3"}),
        ("path", {"d": "M21 8V5a2 2 0 0 0-2-2h-3"}),
        ("path", {"d": "M3 16v3a2 2 0 0 0 2 2h3"}),
        ("path", {"d": "M16 21h3a2 2 0 0 0 2-2v-3"}),
    ],
    "heart": [
        ("path", {"d": "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"}),
    ],
    "x": [("path", {"d": "M18 6 6 18M6 6l12 12"})],
    "check": [("path", {"d": "M20 6 9 17l-5-5"})],
    "info": [
        ("circle", {"cx": "12", "cy": "12", "r": "9"}),
        ("path", {"d": "M12 16v-4"}),
        ("path", {"d": "M12 8h.01"}),
    ],
    "more": [
        ("circle", {"cx": "5", "cy": "12", "r": "1", "fill": "currentColor", "stroke": "none"}),
        ("circle", {"cx": "12", "cy": "12", "r": "1", "fill": "currentColor", "stroke": "none"}),
        ("circle", {"cx": "19", "cy": "12", "r": "1", "fill": "currentColor", "stroke": "none"}),
    ],
    "trash": [
        ("path", {"d": "M3 6h18"}),
        ("path", {"d": "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"}),
        ("path", {"d": "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"}),
    ],
    "shield": [
        ("path", {"d": "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1 1 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"}),
        ("path", {"d": "m9 12 2 2 4-4"}),
    ],
    "zap": [
        ("path", {"d": "M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"}),
    ],
    "code": [
        ("path", {"d": "m16 18 6-6-6-6"}),
        ("path", {"d": "m8 6-6 6 6 6"}),
    ],
    "message": [
        ("path", {"d": "M7.9 20A9 9 0 1 0 4 16.1L2 22Z"}),
    ],
    "folder": [
        ("path", {"d": "M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"}),
    ],
    "chevron-down": [("path", {"d": "m6 9 6 6 6-6"})],
}

_cache: dict[tuple, QPixmap] = {}


def _svg_source(name: str, color: str, stroke: float) -> bytes:
    parts = []
    for tag, attrs in _ICONS[name]:
        a = dict(attrs)  # копия: глобальные данные иконок мутировать нельзя
        fill = a.pop("fill", "none")
        stroke_attr = a.pop("stroke", None)
        s = " ".join(f'{k}="{v}"' for k, v in a.items())
        if stroke_attr == "none":
            parts.append(f"<{tag} {s} fill=\"{color}\" stroke=\"none\"/>")
        else:
            parts.append(f"<{tag} {s} fill=\"{fill}\" stroke=\"{color}\" stroke-width=\"{stroke}\"/>")
    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"'
        f' fill="none" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


def pixmap(name: str, size: int = 24, color: str = "#FFFFFF", stroke: float = 2.0) -> QPixmap:
    """Растр иконки. Цвет — hex, толщина — как в Lucide (2.0)."""
    if name not in _ICONS:
        name = "info"
    key = (name, size, color, stroke)
    hit = _cache.get(key)
    if hit is not None and not hit.isNull():
        return hit
    data = _svg_source(name, QColor(color).name(), stroke)
    ren = QSvgRenderer(data)
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    try:
        ren.render(p)
    finally:
        p.end()
    pm = QPixmap.fromImage(img)
    if len(_cache) > 256:
        _cache.clear()
    _cache[key] = pm
    return pm


def icon(name: str, size: int = 24, color: str = "#FFFFFF", stroke: float = 2.0) -> QIcon:
    return QIcon(pixmap(name, size, color, stroke))


def available() -> list[str]:
    return sorted(_ICONS)
