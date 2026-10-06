"""Процедурные обои: глубокий градиент + аврора-пятна + зерно + виньетка.

Дают тот самый «фото-фон» из референса без бинарных ассетов:
окно выглядит как матовое стекло поверх ночного пейзажа.
"""
from __future__ import annotations

import random

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap, QPolygon, QRadialGradient

_BASE_W, _BASE_H = 1600, 1000
_cache: QPixmap | None = None
_frost_cache: dict[tuple[int, int], QPixmap] = {}


def _paint_base() -> QPixmap:
    pm = QPixmap(_BASE_W, _BASE_H)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        # Вертикальный базовый градиент: почти чёрный верх → графит с теплом внизу
        g = QLinearGradient(0, 0, 0, _BASE_H)
        g.setColorAt(0.0, QColor("#07090D"))
        g.setColorAt(0.55, QColor("#0D1219"))
        g.setColorAt(1.0, QColor("#171512"))
        p.fillRect(pm.rect(), QBrush(g))

        # Аврора-пятна (как свет над океаном на референсе)
        blobs = [
            (0.78, 0.30, 420, "#1E5F6E", 150),   # бирюза справа
            (0.15, 0.75, 460, "#26355E", 140),   # индиго слева внизу
            (0.55, 0.95, 520, "#4A3F30", 100),    # тёплый песок снизу
            (0.30, 0.10, 380, "#12303A", 120),    # глубина сверху
        ]
        for fx, fy, rad, color, alpha in blobs:
            cx, cy = int(_BASE_W * fx), int(_BASE_H * fy)
            rg = QRadialGradient(cx, cy, rad)
            c = QColor(color)
            c.setAlpha(alpha)
            rg.setColorAt(0.0, c)
            c2 = QColor(color)
            c2.setAlpha(0)
            rg.setColorAt(1.0, c2)
            p.setBrush(QBrush(rg))
            p.setPen(Qt.NoPen)
            p.drawEllipse(cx - rad, cy - rad, rad * 2, rad * 2)

        # --- Стилизованное пасмурное побережье (приглушено: фон для стекла) ---
        horizon = int(_BASE_H * 0.60)
        # туманные полосы над водой
        for fy, fh, fa in [(0.40, 60, 16), (0.50, 90, 20), (0.565, 55, 24)]:
            y0 = int(_BASE_H * fy)
            fg = QLinearGradient(0, y0, 0, y0 + fh)
            fog0 = QColor(178, 193, 204, 0)
            fog1 = QColor(178, 193, 204, fa)
            fg.setColorAt(0.0, fog0)
            fg.setColorAt(0.5, fog1)
            fg.setColorAt(1.0, fog0)
            p.fillRect(0, y0, _BASE_W, fh, QBrush(fg))
        # дальние скалы-силуэты
        p.setBrush(QBrush(QColor(10, 14, 18, 225)))
        p.setPen(Qt.NoPen)
        for x1, y1, x2, y2, x3, y3 in [
            (0.50, 0.60, 0.60, 0.60, 0.555, 0.540),
            (0.60, 0.60, 0.71, 0.60, 0.665, 0.548),
            (0.86, 0.60, 1.01, 0.60, 0.955, 0.560),
        ]:
            p.drawPolygon(QPolygon([
                QPoint(int(_BASE_W * x1), int(_BASE_H * y1)),
                QPoint(int(_BASE_W * x2), int(_BASE_H * y2)),
                QPoint(int(_BASE_W * x3), int(_BASE_H * y3)),
            ]))
        # море: тёмная масса + блики волн
        sea = QLinearGradient(0, horizon, 0, _BASE_H)
        sea.setColorAt(0.0, QColor(17, 25, 31, 215))
        sea.setColorAt(1.0, QColor(6, 9, 12, 230))
        p.fillRect(0, horizon, _BASE_W, _BASE_H - horizon, QBrush(sea))
        rnd2 = random.Random(7)
        for _ in range(240):
            x = rnd2.randrange(_BASE_W)
            y = rnd2.randrange(horizon + 6, _BASE_H - 4)
            ln = rnd2.randrange(8, 64)
            p.setPen(QColor(190, 210, 220, rnd2.randrange(10, 30)))
            p.drawLine(x, y, x + ln, y)
        p.setPen(Qt.NoPen)
        # одинокий дом у воды: силуэт + тёплые окна + отражение
        hx, hy, hw, hh = int(_BASE_W * 0.74), horizon - 46, 92, 46
        p.setBrush(QBrush(QColor(8, 10, 13, 235)))
        p.drawRect(hx, hy, hw, hh)
        p.drawRect(hx + 19, hy - 14, 54, 14)
        p.setBrush(QBrush(QColor(255, 170, 90, 205)))
        p.drawRect(hx + 10, hy + 13, 16, 12)
        p.drawRect(hx + 66, hy + 13, 16, 12)
        p.drawRect(hx + 35, hy - 10, 22, 8)
        p.setBrush(QBrush(QColor(255, 170, 90, 42)))
        p.drawRect(hx + 10, hy + hh + 6, 16, 26)
        p.drawRect(hx + 66, hy + hh + 6, 16, 26)
        # сосны слева
        p.setBrush(QBrush(QColor(6, 10, 8, 240)))
        for tx, th in [(60, 200), (112, 265), (172, 185), (228, 300)]:
            base_y = _BASE_H - 40
            for k in range(3):
                ww = 48 - k * 12
                yy = base_y - th + k * (th // 3)
                p.drawPolygon(QPolygon([
                    QPoint(tx - ww // 2, yy), QPoint(tx + ww // 2, yy), QPoint(tx, yy - 72),
                ]))
            p.drawRect(tx - 3, base_y - th, 6, th)
        # передние камни в воде
        p.setBrush(QBrush(QColor(5, 7, 9, 245)))
        for cf, cw, ch in [(0.08, 230, 90), (0.33, 310, 62), (0.90, 270, 115)]:
            p.drawEllipse(int(_BASE_W * cf), _BASE_H - ch, cw, ch * 2)

        # Тонкая светлая линия горизонта
        p.setPen(QColor(255, 255, 255, 14))
        p.drawLine(0, horizon, _BASE_W, horizon)

        # Зерно плёнки
        rnd = random.Random(42)
        p.setPen(Qt.NoPen)
        for _ in range(5200):
            x = rnd.randrange(_BASE_W)
            y = rnd.randrange(_BASE_H)
            v = rnd.randrange(140, 255)
            c = QColor(v, v, v, 5)
            p.setPen(c)
            p.drawPoint(x, y)
        p.setPen(Qt.NoPen)

        # Виньетка: затемнение краёв для читаемости стекла
        vg = QRadialGradient(_BASE_W // 2, _BASE_H // 2, int(_BASE_W * 0.62))
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(1.0, QColor(0, 0, 0, 95))
        p.fillRect(pm.rect(), QBrush(vg))

        # Диагональный блик на «стекле»: светлая вуаль слева сверху
        sheen = QLinearGradient(0, 0, int(_BASE_W * 0.5), int(_BASE_H * 0.85))
        sheen.setColorAt(0.0, QColor(255, 255, 255, 30))
        sheen.setColorAt(0.35, QColor(255, 255, 255, 7))
        sheen.setColorAt(0.62, QColor(255, 255, 255, 0))
        p.fillRect(pm.rect(), QBrush(sheen))
    finally:
        p.end()
    return pm


def wallpaper_pixmap(w: int, h: int) -> QPixmap:
    """Фон, масштабированный под размер окна (cover)."""
    global _cache
    if _cache is None:
        _cache = _paint_base()
    if w <= 0 or h <= 0:
        return _cache
    target_ratio = w / h
    base_ratio = _BASE_W / _BASE_H
    if target_ratio > base_ratio:
        sw, sh = w, int(w / base_ratio)
    else:
        sw, sh = int(h * base_ratio), h
    scaled = _cache.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    return scaled.copy(x, y, w, h)


def frosted(w: int, h: int) -> QPixmap:
    """Сильно размытая версия фона — подложка frosted-стекла.

    Дешёвое размытие через даунскейл: уменьшаем в ~12 раз и тянем обратно
    с билинейной фильтрацией. Выглядит как матовое стекло.
    """
    key = (max(1, w), max(1, h))
    pm = _frost_cache.get(key)
    if pm is not None and not pm.isNull():
        return pm
    base = wallpaper_pixmap(w, h)
    small = base.scaled(max(1, w // 12), max(1, h // 12), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    pm = small.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if len(_frost_cache) > 3:
        _frost_cache.clear()
    _frost_cache[key] = pm
    return pm
