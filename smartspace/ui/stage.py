"""Сцена в духе «Моя волна»: градиент, hero-заголовок, транспорт, pill, облако категорий.

Маппинг плеера на чистильщик (вся логика — в MainWindow, здесь только сигналы):
  shuffle → автовыбор только безопасных      prev/next → фокус соседней категории
  play/pause → старт/стоп сканирования       repeat → пересканировать
  maximize → открыть папку категории         shield → только Safe
  x → снять выбор                            info → подробности (панель)
  trash → очистить выбранное (с подтверждением)
"""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QGraphicsBlurEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .sidebar import avatar_pixmap
from .theme import (
    COVER,
    COVER_RADIUS,
    CLOUD_ICON,
    GROUPS,
    HERO_MAX,
    HERO_MIN,
    HOVER_MS,
    PALETTES,
    ROUND_BTN,
    STAGE_MS,
    TEXT_MAIN,
    TRANSPORT_MAIN,
    TRANSPORT_SIDE,
    YELLOW,
    ZOOM,
    group_color,
    group_icon,
)


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


class CircleButton(QAbstractButton):
    """Круглая кнопка с иконкой: hover 180 мс, рост ×1.05, виды ghost/solid."""

    def __init__(self, icon_name: str, d: int = ROUND_BTN, kind: str = "ghost", parent=None) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._d = d
        self._kind = kind
        self._t = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(d + 12, d + 12)
        self._anim = QPropertyAnimation(self, b"hoverT", self)
        self._anim.setDuration(HOVER_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._rebuild()

    def _rebuild(self) -> None:
        isz = int(self._d * 0.46)
        if self._kind == "solid":
            self._pm = icons.pixmap(self._icon_name, isz, "#111111", 2.2)
        else:
            self._pm = icons.pixmap(self._icon_name, isz, TEXT_MAIN, 2.0)

    def set_icon(self, name: str) -> None:
        self._icon_name = name
        self._rebuild()
        self.update()

    def _get_t(self) -> float:
        return self._t

    def _set_t(self, v: float) -> None:
        self._t = float(v)
        self.update()

    hoverT = Property(float, _get_t, _set_t)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._anim.stop()
        self._anim.setStartValue(self._t)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        s = 1.0 + (ZOOM - 1.0) * self._t
        d = self._d * s
        cx, cy = self.width() / 2, self.height() / 2
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            if self._kind == "solid":
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.setPen(Qt.NoPen)
            else:
                p.setBrush(QBrush(QColor(255, 255, 255, int(20 + 26 * self._t))))
                p.setPen(QColor(255, 255, 255, int(40 + 40 * self._t)))
            p.drawEllipse(int(cx - d / 2), int(cy - d / 2), int(d), int(d))
            iw = self._pm.width() * s
            p.drawPixmap(int(cx - iw / 2), int(cy - iw / 2), int(iw), int(iw), self._pm)
        finally:
            p.end()


class CoverTile(QLabel):
    """Квадратная «обложка» категории 64px: градиент группы + белая иконка."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(COVER, COVER)
        self.set_group("Windows и обновления")

    def set_group(self, group: str) -> None:
        pm = QPixmap(COVER, COVER)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            g = QLinearGradient(0, 0, COVER, COVER)
            base = QColor(group_color(group))
            g.setColorAt(0.0, base)
            g.setColorAt(1.0, QColor(
                max(0, int(base.red() * 0.35)),
                max(0, int(base.green() * 0.35)),
                max(0, int(base.blue() * 0.35)),
            ))
            path = QPainterPath()
            path.addRoundedRect(0, 0, COVER, COVER, COVER_RADIUS, COVER_RADIUS)
            p.fillPath(path, QBrush(g))
            glyph = icons.pixmap(group_icon(group), 30, "#FFFFFF", 2.0)
            p.drawPixmap((COVER - 30) // 2, (COVER - 30) // 2, glyph)
        finally:
            p.end()
        self.setPixmap(pm)


class CloudItem(QPushButton):
    """Строка облака категорий: цветной значок 56px + белое название, отступ-каскад."""

    def __init__(self, group: str, indent: int = 0, opacity: float = 1.0, blur: float = 0.0, parent=None) -> None:
        super().__init__(parent)
        self._group = group
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)  # QPushButton не умеет hint от вложенного layout — фиксируем
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 14px; text-align: left; }"
            "QPushButton:hover { background: rgba(255,255,255,0.07); }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(indent, 4, 8, 4)
        lay.setSpacing(14)
        meta = GROUPS[group]
        badge = QLabel()
        badge.setFixedSize(CLOUD_ICON, CLOUD_ICON)
        pm = QPixmap(CLOUD_ICON, CLOUD_ICON)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            g = QLinearGradient(0, 0, CLOUD_ICON, CLOUD_ICON)
            base = QColor(meta["color"])
            g.setColorAt(0.0, base)
            g.setColorAt(1.0, QColor(
                max(0, int(base.red() * 0.4)),
                max(0, int(base.green() * 0.4)),
                max(0, int(base.blue() * 0.4)),
            ))
            path = QPainterPath()
            path.addRoundedRect(0, 0, CLOUD_ICON, CLOUD_ICON, 18, 18)
            p.fillPath(path, QBrush(g))
            glyph = icons.pixmap(meta["icon"], 28, "#FFFFFF", 2.0)
            p.drawPixmap((CLOUD_ICON - 28) // 2, (CLOUD_ICON - 28) // 2, glyph)
        finally:
            p.end()
        badge.setPixmap(pm)
        if blur > 0.1:
            eff = QGraphicsBlurEffect(badge)
            eff.setBlurRadius(blur)
            badge.setGraphicsEffect(eff)
        lay.addWidget(badge)
        name = QLabel(group)
        name.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF; background: transparent; border: none;")
        name.setWordWrap(True)
        lay.addWidget(name, 1)
        op = QGraphicsOpacityEffect(self)
        op.setOpacity(opacity)
        self.setGraphicsEffect(op)


class StageWidget(QWidget):
    """Центральная сцена-плеер с анимированным градиентом."""

    transport_pressed = Signal(str)  # shuffle|prev|play|next|repeat
    round_pressed = Signal(str)      # open|safe|clear|details|trash
    pill_pressed = Signal()
    hint_closed = Signal()
    cloud_focused = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._from = {k: QColor(v) for k, v in PALETTES["ember"].items()}
        self._to = {k: QColor(v) for k, v in PALETTES["ember"].items()}
        self._mix = 1.0
        self._pal_key = "ember"
        self._anim = QPropertyAnimation(self, b"mix", self)
        self._anim.setDuration(STAGE_MS)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._playing = False
        self._build()

    # -- анимация палитры
    def _get_mix(self) -> float:
        return self._mix

    def _set_mix(self, v: float) -> None:
        self._mix = float(v)
        self.update()

    mix = Property(float, _get_mix, _set_mix)

    def _cur(self, key: str) -> QColor:
        return _lerp(self._from[key], self._to[key], self._mix)

    def set_palette_key(self, key: str) -> None:
        if key == self._pal_key or key not in PALETTES:
            return
        snap = {k: self._cur(k) for k in ("left", "mid", "right", "glow")}
        self._from = snap
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
            c0 = QColor(glow.red(), glow.green(), glow.blue(), 110)
            c1 = QColor(glow.red(), glow.green(), glow.blue(), 0)
            rg.setColorAt(0.0, c0)
            rg.setColorAt(1.0, c1)
            p.fillRect(r, QBrush(rg))
        finally:
            p.end()

    # -- построение
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 14, 28, 16)
        root.setSpacing(8)

        # Верх: [stretch][заголовок][stretch][аватар+статус]
        top = QHBoxLayout()
        top.addStretch(1)
        self.section_title = QLabel("Главная")
        self.section_title.setObjectName("sectionTitle")
        top.addWidget(self.section_title)
        top.addStretch(1)
        self.avatar = QLabel()
        self.avatar.setFixedSize(36, 36)
        self.avatar.setPixmap(avatar_pixmap("S", "#FF4A1C"))
        top.addWidget(self.avatar)
        self.status_text = QLabel("…")
        self.status_text.setObjectName("statusText")
        top.addWidget(self.status_text)
        root.addLayout(top)

        # Середина: [облако][центр]
        mid = QHBoxLayout()
        mid.setSpacing(10)

        cloud = QVBoxLayout()
        cloud.setSpacing(6)
        cloud.addStretch(1)
        indents = [0, 24, 48, 24]
        opacities = [0.55, 0.85, 1.0, 0.7]
        blurs = [0.0, 0.0, 0.0, 0.0]
        self._cloud_items: list[CloudItem] = []
        for i, group in enumerate(GROUPS):
            item = CloudItem(group, indent=indents[i], opacity=opacities[i], blur=blurs[i])
            item.clicked.connect(lambda _=False, g=group: self.cloud_focused.emit(g))
            cloud.addWidget(item)
            self._cloud_items.append(item)
        cloud.addStretch(1)
        cloud_box = QWidget()
        cloud_box.setFixedWidth(320)
        cloud_box.setLayout(cloud)
        mid.addWidget(cloud_box, 0)

        center = QVBoxLayout()
        center.setSpacing(12)
        center.addStretch(1)

        self.hero = QLabel("SmartSpace")
        self.hero.setAlignment(Qt.AlignCenter)
        self.hero.setWordWrap(True)
        center.addWidget(self.hero)

        cover_row = QHBoxLayout()
        cover_row.setSpacing(16)
        cover_row.addStretch(1)
        self.cover = CoverTile()
        cover_row.addWidget(self.cover)
        self.btn_shuffle = CircleButton("shuffle", TRANSPORT_SIDE)
        self.btn_prev = CircleButton("skip-back", TRANSPORT_SIDE)
        self.btn_play = CircleButton("play", TRANSPORT_MAIN, kind="solid")
        self.btn_next = CircleButton("skip-forward", TRANSPORT_SIDE)
        self.btn_repeat = CircleButton("repeat", TRANSPORT_SIDE)
        for b, act in [
            (self.btn_shuffle, "shuffle"), (self.btn_prev, "prev"), (self.btn_play, "play"),
            (self.btn_next, "next"), (self.btn_repeat, "repeat"),
        ]:
            b.clicked.connect(lambda _=False, a=act: self.transport_pressed.emit(a))
            cover_row.addWidget(b, 0, Qt.AlignVCenter)
        cover_row.addStretch(1)
        center.addLayout(cover_row)

        pill_row = QHBoxLayout()
        pill_row.addStretch(1)
        self.pill = QPushButton("Выберите категорию")
        self.pill.setObjectName("pillBtn")
        self.pill.setCursor(Qt.PointingHandCursor)
        self.pill.clicked.connect(self.pill_pressed.emit)
        pill_row.addWidget(self.pill)
        pill_row.addStretch(1)
        center.addLayout(pill_row)

        rounds = QHBoxLayout()
        rounds.setSpacing(12)
        rounds.addStretch(1)
        self._round_btns: dict[str, CircleButton] = {}
        for icon_name, act in [
            ("maximize", "open"), ("shield", "safe"), ("x", "clear"),
            ("info", "details"), ("trash", "trash"),
        ]:
            b = CircleButton(icon_name, 40)
            b.setToolTip({"open": "Открыть папку", "safe": "Только безопасные",
                          "clear": "Снять выбор", "details": "Подробнее",
                          "trash": "В Корзину"}[act])
            b.clicked.connect(lambda _=False, a=act: self.round_pressed.emit(a))
            rounds.addWidget(b)
            self._round_btns[act] = b
        rounds.addStretch(1)
        center.addLayout(rounds)
        center.addStretch(1)
        mid.addLayout(center, 1)
        root.addLayout(mid, 1)

        # Низ: подсказка + «Закрыть»
        hint_row = QHBoxLayout()
        hint_row.setSpacing(8)
        spark = QLabel()
        spark.setPixmap(icons.pixmap("sparkles", 14, YELLOW))
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

    def set_hero(self, text: str) -> None:
        """Очень крупный заголовок с автоуменьшением до HERO_MIN."""
        size = HERO_MAX
        probe = QFont("Inter", size, QFont.Weight.ExtraBold)
        avail = max(200, self.width() - 420)
        while size > HERO_MIN:
            if QFontMetrics(probe).horizontalAdvance(text) <= avail:
                break
            size -= 4
            probe = QFont("Inter", size, QFont.Weight.ExtraBold)
        self.hero.setFont(probe)
        self.hero.setStyleSheet("font-weight: 800; color: #FFFFFF;")
        self.hero.setText(text)

    def set_cover_group(self, group: str) -> None:
        self.cover.set_group(group)

    def set_pill(self, text: str) -> None:
        self.pill.setText(text)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self.btn_play.set_icon("pause" if playing else "play")

    def set_hint(self, text: str) -> None:
        self.hint.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Пересчитать размер hero под новую ширину
        if self.hero.text():
            self.set_hero(self.hero.text())
