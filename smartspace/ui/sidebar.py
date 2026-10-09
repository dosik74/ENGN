"""Сайдбар в духе плеера: жёлтый логотип, линейные иконки, плавный hover, коллекции."""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons
from ..utils import format_bytes
from .theme import AVATAR, GROUPS, SIDEBAR_W, TEXT_DIM, TEXT_MAIN, YELLOW, HOVER_MS


def avatar_pixmap(letter: str, color: str, size: int = AVATAR) -> QPixmap:
    """Круглая градиентная аватарка 36px с буквой."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0.0, QColor(color))
        base = QColor(color)
        dark = QColor(
            max(0, int(base.red() * 0.45)),
            max(0, int(base.green() * 0.45)),
            max(0, int(base.blue() * 0.45)),
        )
        g.setColorAt(1.0, dark)
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, size, size)
        p.setPen(QColor("#FFFFFF"))
        f = QFont("Inter", max(8, int(size * 0.42)), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, letter[:1].upper())
    finally:
        p.end()
    return pm


class NavButton(QAbstractButton):
    """Пункт меню: иконка + текст, hover затухает за 180 мс, активный — белый и с полосой."""

    def __init__(self, key: str, icon_name: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self._key = key
        self._icon_name = icon_name
        self._text = text
        self._hover_t = 0.0
        self._active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self._anim = QPropertyAnimation(self, b"hoverT", self)
        self._anim.setDuration(HOVER_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        # Два цвета иконки: серая и белая — кросcфейд при наведении
        self._pm_dim = icons.pixmap(icon_name, 20, TEXT_DIM)
        self._pm_on = icons.pixmap(icon_name, 20, TEXT_MAIN)

    # -- анимационное свойство
    def _get_hover_t(self) -> float:
        return self._hover_t

    def _set_hover_t(self, v: float) -> None:
        self._hover_t = float(v)
        self.update()

    hoverT = Property(float, _get_hover_t, _set_hover_t)

    def set_active(self, v: bool) -> None:
        self._active = v
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_t)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._hover_t)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = max(self._hover_t, 1.0 if self._active else 0.0)
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            r = self.rect().adjusted(4, 3, -4, -3)
            if t > 0.01:
                p.setBrush(QBrush(QColor(255, 255, 255, int(22 * t))))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(r, 10, 10)
            if self._active:
                p.setBrush(QBrush(QColor(YELLOW)))
                p.drawRoundedRect(0, 10, 3, self.height() - 20, 1.5, 1.5)
            # иконка: серая → белая
            ix, iy = 16, (self.height() - 20) // 2
            p.setOpacity(1.0)
            p.drawPixmap(ix, iy, self._pm_dim)
            p.setOpacity(t)
            p.drawPixmap(ix, iy, self._pm_on)
            p.setOpacity(1.0)
            # текст: серый → белый
            c_dim, c_on = QColor(TEXT_DIM), QColor(TEXT_MAIN)
            c = QColor(
                int(c_dim.red() + (c_on.red() - c_dim.red()) * t),
                int(c_dim.green() + (c_on.green() - c_dim.green()) * t),
                int(c_dim.blue() + (c_on.blue() - c_dim.blue()) * t),
            )
            p.setPen(c)
            f = QFont("Inter", 13.5, QFont.Weight.Bold if self._active else QFont.Weight.Medium)
            p.setFont(f)
            p.drawText(self.rect().adjusted(ix + 30, 0, -8, 0),
                       Qt.AlignLeft | Qt.AlignVCenter, self._text)
        finally:
            p.end()


class Sidebar(QWidget):
    nav_requested = Signal(str)
    group_requested = Signal(str)

    MENU = [
        ("search", "search", "Поиск"),
        ("home", "home", "Главная"),
        ("recs", "sparkles", "Рекомендации"),
        ("library", "layers", "Библиотека"),
        ("settings", "sliders", "Настройки"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 18, 12, 14)
        lay.setSpacing(2)

        logo = QLabel("SmartSpace")
        logo.setObjectName("logo")
        lay.addWidget(logo)

        self._buttons: dict[str, NavButton] = {}
        for key, icon_name, text in self.MENU:
            b = NavButton(key, icon_name, text)
            b.clicked.connect(lambda _=False, k=key: self.nav_requested.emit(k))
            lay.addWidget(b)
            self._buttons[key] = b
        self._buttons["home"].set_active(True)

        lay.addSpacing(10)
        cap = QLabel("Коллекции")
        cap.setObjectName("sideCap")
        lay.addWidget(cap)

        self._coll_rows: dict[str, tuple[QLabel, QLabel]] = {}
        for group, meta in GROUPS.items():
            row = QPushButton()
            row.setFlat(True)
            row.setCursor(Qt.PointingHandCursor)
            row.setFixedHeight(50)  # QPushButton не умеет hint от вложенного layout — фиксируем
            row.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 10px; text-align: left; }"
                "QPushButton:hover { background: rgba(255,255,255,0.07); }"
            )
            hl = QHBoxLayout(row)
            hl.setContentsMargins(8, 6, 8, 6)
            hl.setSpacing(10)
            ava = QLabel()
            ava.setFixedSize(AVATAR, AVATAR)
            ava.setPixmap(avatar_pixmap(group[:1], meta["color"]))
            hl.addWidget(ava)
            txt = QVBoxLayout()
            txt.setSpacing(0)
            name = QLabel(group)
            name.setObjectName("collName")
            name.setWordWrap(True)
            sub = QLabel("—")
            sub.setObjectName("collSub")
            txt.addWidget(name)
            txt.addWidget(sub)
            hl.addLayout(txt, 1)
            row.clicked.connect(lambda _=False, g=group: self.group_requested.emit(g))
            lay.addWidget(row)
            self._coll_rows[group] = (name, sub)

        lay.addStretch(1)
        foot = QLabel("В Корзину по умолчанию.\nБез галочки не трогаем.")
        foot.setObjectName("collSub")
        foot.setWordWrap(True)
        lay.addWidget(foot)

    def set_active(self, key: str) -> None:
        for k, b in self._buttons.items():
            b.set_active(k == key)

    def set_collections(self, stats: dict[str, tuple[int, int]]) -> None:
        """stats: {group: (категорий_найдено, байт)}."""
        for group, (_name, sub) in self._coll_rows.items():
            if group in stats:
                _n, size = stats[group]
                sub.setText(f"{format_bytes(size)}")
            else:
                sub.setText("—")
