"""Домашняя сцена: строго и понятно, как у больших.

Один главный CTA с текстом (никаких загадок), степпер словами 1-2-3,
полоса фокуса «сейчас смотрим» и ряд групп с весом. Вся логика — в MainWindow.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal, QSize
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .sidebar import avatar_pixmap
from .theme import (
    GROUPS,
    HERO_MAX,
    HERO_MIN,
    PALETTES,
    STAGE_MS,
    group_color,
    group_icon,
)
from ..utils import format_bytes


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def _tile_pixmap(group: str, size: int, radius: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, size, size)
        base = QColor(group_color(group))
        g.setColorAt(0.0, base)
        g.setColorAt(1.0, QColor(
            max(0, int(base.red() * 0.35)),
            max(0, int(base.green() * 0.35)),
            max(0, int(base.blue() * 0.35)),
        ))
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, radius, radius)
        p.fillPath(path, QBrush(g))
        isz = int(size * 0.48)
        glyph = icons.pixmap(group_icon(group), isz, "#FFFFFF", 2.0)
        p.drawPixmap((size - isz) // 2, (size - isz) // 2, glyph)
    finally:
        p.end()
    return pm


class Stepper(QWidget):
    """Шаги словами. Кликабельны: 1 — сканировать, 2 — к выбору, 3 — очистить."""

    step_pressed = Signal(int)

    STEPS = [(1, "Найти"), (2, "Выбрать"), (3, "Освободить")]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._btns: list[QPushButton] = []
        for i, (num, text) in enumerate(self.STEPS):
            b = QPushButton(f"{num}  {text}")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=num: self.step_pressed.emit(n))
            lay.addWidget(b)
            self._btns.append(b)
            if i < len(self.STEPS) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 14px; background: transparent;")
                lay.addWidget(arrow)
        lay.addStretch(1)
        self.set_step(1)

    def set_step(self, n: int) -> None:
        for i, btn in enumerate(self._btns, start=1):
            if i < n:
                btn.setStyleSheet(
                    "background: rgba(255,204,0,0.14); color: #FFCC00; "
                    "border: 1px solid rgba(255,204,0,0.45); border-radius: 12px; "
                    "padding: 7px 16px; font-size: 13px; font-weight: 700;")
                if not btn.text().startswith("✓"):
                    btn.setText("✓ " + btn.text().lstrip("✓ "))
            elif i == n:
                t = btn.text().lstrip("✓ ")
                btn.setText(t)
                btn.setStyleSheet(
                    "background: #F5F7FA; color: #0B0D12; border: none; "
                    "border-radius: 12px; padding: 7px 16px; font-size: 13px; font-weight: 700;")
            else:
                t = btn.text().lstrip("✓ ")
                btn.setText(t)
                btn.setStyleSheet(
                    "background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.5); "
                    "border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; "
                    "padding: 7px 16px; font-size: 13px; font-weight: 500;")


class GroupCard(QPushButton):
    """Компактная группа: плитка, название, найденный вес. Клик — в Поиск с фильтром."""

    def __init__(self, group: str, parent=None) -> None:
        super().__init__(parent)
        self._group = group
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)  # QPushButton не умеет hint от вложенного layout — фиксируем
        self.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.10);"
            " border-radius: 14px; text-align: left; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10); }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)
        self.tile = QLabel()
        self.tile.setFixedSize(40, 40)
        self.tile.setPixmap(_tile_pixmap(group, 40, 12))
        lay.addWidget(self.tile)
        txt = QVBoxLayout()
        txt.setSpacing(1)
        name = QLabel(group)
        name.setStyleSheet("font-size: 13.5px; font-weight: 600; color: #FFFFFF; background: transparent; border: none;")
        name.setWordWrap(True)
        txt.addWidget(name)
        self.sub = QLabel("—")
        self.sub.setStyleSheet("font-size: 11.5px; color: #A7AEB8; background: transparent; border: none;")
        txt.addWidget(self.sub)
        lay.addLayout(txt, 1)

    def set_stats(self, count: int | None, size: int | None) -> None:
        if count is None:
            self.sub.setText("Сканирование покажет вес")
        elif size and size > 0:
            self.sub.setText(f"{count} кат. • {format_bytes(size)}")
        else:
            self.sub.setText("Чисто" if count else "Не найдено")


class FocusStrip(QFrame):
    """«Сейчас смотрим»: плитка, название, вес, листалки, действия словами."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        self.tile = QLabel()
        self.tile.setFixedSize(44, 44)
        lay.addWidget(self.tile)
        txt = QVBoxLayout()
        txt.setSpacing(1)
        self.title = QLabel("—")
        self.title.setObjectName("title")
        txt.addWidget(self.title)
        self.sub = QLabel("")
        self.sub.setObjectName("muted")
        txt.addWidget(self.sub)
        lay.addLayout(txt, 1)
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setObjectName("ghost")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setToolTip("Предыдущая категория")
        lay.addWidget(self.prev_btn)
        self.next_btn = QPushButton("›")
        self.next_btn.setObjectName("ghost")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setToolTip("Следующая категория")
        lay.addWidget(self.next_btn)
        self.details_btn = QPushButton("Подробнее")
        self.details_btn.setObjectName("ghost")
        self.details_btn.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.details_btn)
        self.open_btn = QPushButton("Открыть папку")
        self.open_btn.setObjectName("ghost")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        icons_btn = icons.icon("maximize", 15, "#FFFFFF")
        self.open_btn.setIcon(icons_btn)
        lay.addWidget(self.open_btn)

    def set_focus(self, title: str, sub: str, group: str) -> None:
        self.title.setText(title)
        self.sub.setText(sub)
        self.tile.setPixmap(_tile_pixmap(group, 44, 13))


class StageWidget(QWidget):
    """Домашняя сцена без загадок: CTA, степпер, фокус, группы."""

    primary_pressed = Signal()
    safe_pressed = Signal()
    step_pressed = Signal(int)
    focus_prev = Signal()
    focus_next = Signal()
    focus_open = Signal()
    focus_details = Signal()
    group_chosen = Signal(str)
    hint_closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._from = {k: QColor(v) for k, v in PALETTES["ember"].items()}
        self._to = {k: QColor(v) for k, v in PALETTES["ember"].items()}
        self._mix = 1.0
        self._pal_key = "ember"
        self._anim = QPropertyAnimation(self, b"mix", self)
        self._anim.setDuration(STAGE_MS)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._build()

    # -- анимация палитры
    def _get_mix(self) -> float:
        return self._mix

    def _set_mix(self, v: float) -> None:
        self._mix = float(v)
        self.update()

    mix = Property(float, _get_mix, _set_mix)

    def _cur(self, key: str) -> QColor:
        a, b = self._from[key], self._to[key]
        t = self._mix
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t))

    def set_palette_key(self, key: str) -> None:
        if key == self._pal_key or key not in PALETTES:
            return
        self._from = {k: self._cur(k) for k in ("left", "mid", "right", "glow")}
        self._to = {k: QColor(v) for k, v in PALETTES[key].items()}
        self._pal_key = key
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            r = self.rect()
            g = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
            g.setColorAt(0.0, self._cur("left"))
            g.setColorAt(0.55, self._cur("mid"))
            g.setColorAt(1.0, self._cur("right"))
            p.fillRect(r, QBrush(g))
            glow = self._cur("glow")
            rg = QRadialGradient(r.center(), max(r.width(), r.height()) * 0.45)
            rg.setColorAt(0.0, QColor(glow.red(), glow.green(), glow.blue(), 90))
            rg.setColorAt(1.0, QColor(glow.red(), glow.green(), glow.blue(), 0))
            p.fillRect(r, QBrush(rg))
        finally:
            p.end()

    # -- построение
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 14, 28, 14)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.addStretch(1)
        self.section_title = QLabel("Главная")
        self.section_title.setObjectName("sectionTitle")
        top.addWidget(self.section_title)
        top.addStretch(1)
        self.avatar = QLabel()
        self.avatar.setFixedSize(36, 36)
        self.avatar.setPixmap(avatar_pixmap("C", "#FF4A1C"))
        top.addWidget(self.avatar)
        self.status_text = QLabel("…")
        self.status_text.setObjectName("statusText")
        top.addWidget(self.status_text)
        root.addLayout(top)

        self.kicker = QLabel("ШАГ 1 ИЗ 3")
        self.kicker.setObjectName("kicker")
        root.addWidget(self.kicker)

        self.hero = QLabel("Найди, что съедает диск")
        self.hero.setWordWrap(True)
        root.addWidget(self.hero)

        self.sub = QLabel("")
        self.sub.setObjectName("heroSub")
        self.sub.setWordWrap(True)
        root.addWidget(self.sub)

        crow = QHBoxLayout()
        crow.setSpacing(10)
        self.primary = QPushButton("Найти мусор")
        self.primary.setObjectName("primary")
        self.primary.setMinimumHeight(52)
        self.primary.setMinimumWidth(280)
        self.primary.setCursor(Qt.PointingHandCursor)
        self.primary.setIconSize(QSize(20, 20))
        self.primary.clicked.connect(self.primary_pressed.emit)
        crow.addWidget(self.primary)
        self.safe_btn = QPushButton("Выбрать только безопасные")
        self.safe_btn.setObjectName("ghost")
        self.safe_btn.setCursor(Qt.PointingHandCursor)
        self.safe_btn.clicked.connect(self.safe_pressed.emit)
        crow.addWidget(self.safe_btn)
        crow.addStretch(1)
        root.addLayout(crow)

        self.stepper = Stepper()
        self.stepper.step_pressed.connect(self.step_pressed.emit)
        root.addWidget(self.stepper)

        self.focus = FocusStrip()
        self.focus.prev_btn.clicked.connect(self.focus_prev.emit)
        self.focus.next_btn.clicked.connect(self.focus_next.emit)
        self.focus.open_btn.clicked.connect(self.focus_open.emit)
        self.focus.details_btn.clicked.connect(self.focus_details.emit)
        root.addWidget(self.focus)

        grow = QHBoxLayout()
        grow.setSpacing(10)
        self._group_cards: dict[str, GroupCard] = {}
        for group in GROUPS:
            card = GroupCard(group)
            card.clicked.connect(lambda _=False, g=group: self.group_chosen.emit(g))
            grow.addWidget(card, 1)
            self._group_cards[group] = card
        root.addLayout(grow)
        root.addStretch(1)

        hint_row = QHBoxLayout()
        hint_row.setSpacing(8)
        spark = QLabel()
        spark.setPixmap(icons.pixmap("sparkles", 14, "#FFCC00"))
        hint_row.addWidget(spark)
        self.hint = QLabel("Сканирование ничего не удаляет — всё уходит в Корзину.")
        self.hint.setObjectName("hint")
        hint_row.addWidget(self.hint, 1)
        self.close_link = QPushButton("Закрыть")
        self.close_link.setObjectName("linkBtn")
        self.close_link.setCursor(Qt.PointingHandCursor)
        self.close_link.clicked.connect(self.hint_closed.emit)
        hint_row.addWidget(self.close_link)
        root.addLayout(hint_row)

    # -- публичное API
    def set_section(self, title: str) -> None:
        self.section_title.setText(title)

    def set_status(self, text: str) -> None:
        self.status_text.setText(text)

    def set_kicker(self, text: str) -> None:
        self.kicker.setText(text)

    def set_hero(self, title: str, subtitle: str = "") -> None:
        size = HERO_MAX
        probe = QFont("Inter", size, QFont.Weight.ExtraBold)
        avail = max(280, self.width() - 120)
        while size > HERO_MIN:
            if QFontMetrics(probe).horizontalAdvance(title) <= avail:
                break
            size -= 4
            probe = QFont("Inter", size, QFont.Weight.ExtraBold)
        self.hero.setFont(probe)
        self.hero.setStyleSheet("font-weight: 800; color: #FFFFFF;")
        self.hero.setText(title)
        self.sub.setText(subtitle)

    def set_primary(self, text: str, icon_name: str | None = None, enabled: bool = True) -> None:
        self.primary.setText(text)
        self.primary.setEnabled(enabled)
        if icon_name:
            try:
                self.primary.setIcon(icons.icon(icon_name, 20, "#111111" if enabled else "#8A8A8A"))
            except Exception:
                self.primary.setIcon(QIcon())
        else:
            self.primary.setIcon(QIcon())

    def set_step(self, n: int) -> None:
        self.stepper.set_step(n)

    def set_focus(self, title: str, sub: str, group: str) -> None:
        self.focus.set_focus(title, sub, group)

    def set_groups(self, stats: dict[str, tuple[int | None, int | None]]) -> None:
        for group, card in self._group_cards.items():
            if group in stats:
                count, size = stats[group]
                card.set_stats(count, size)
            else:
                card.set_stats(None, None)

    def set_hint(self, text: str) -> None:
        self.hint.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.hero.text():
            self.set_hero(self.hero.text(), self.sub.text())
