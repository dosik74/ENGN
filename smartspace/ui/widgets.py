"""Переиспользуемые виджеты: донат-диаграмма, бейдж риска, карточка кэша."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import CacheRule
from ..utils import format_bytes, format_count
from .styles import ACCENT, ACCENT_DIM, TEXT_DIM


class DonutChart(QWidget):
    """Кольцевая диаграмма занято/свободно с текстом в центре."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._used = 0
        self._total = 1
        self._center_top = ""
        self._center_bottom = ""
        self.setMinimumSize(190, 190)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_values(self, used: int, total: int, center_top: str = "", center_bottom: str = "") -> None:
        self._used = max(0, used)
        self._total = max(1, total)
        self._center_top = center_top
        self._center_bottom = center_bottom
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        side = min(self.width(), self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        try:
            rect = self.rect()
            cx, cy = rect.center().x(), rect.center().y()
            radius = side / 2 - 12
            pen_bg = QPen(QColor("#333336"), 18)
            pen_bg.setCapStyle(Qt.RoundCap)
            p.setPen(pen_bg)
            p.drawArc(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2), 0, 360 * 16)

            frac = min(1.0, self._used / self._total) if self._total else 0.0
            color = QColor(ACCENT_DIM)
            if frac > 0.9:
                color = QColor("#E81123")
            elif frac > 0.75:
                color = QColor("#E8A800")
            pen_fg = QPen(color, 18)
            pen_fg.setCapStyle(Qt.RoundCap)
            p.setPen(pen_fg)
            start_angle = 90 * 16
            span = int(-frac * 360 * 16)
            p.drawArc(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2), start_angle, span)

            p.setPen(QColor("#F3F3F3"))
            f1 = QFont("Segoe UI", 16, QFont.Bold)
            p.setFont(f1)
            p.drawText(rect.adjusted(0, -14, 0, -14), Qt.AlignCenter, self._center_top)
            p.setPen(QColor(TEXT_DIM))
            f2 = QFont("Segoe UI", 10)
            p.setFont(f2)
            p.drawText(rect.adjusted(0, 16, 0, 16), Qt.AlignCenter, self._center_bottom)
            # процент под центром
            p.setPen(QColor(TEXT_DIM))
            f3 = QFont("Segoe UI", 9)
            p.setFont(f3)
            p.drawText(rect.adjusted(0, 44, 0, 44), Qt.AlignCenter, f"{frac * 100:.1f}% занято")
        finally:
            p.end()


class RiskBadge(QLabel):
    # Мягкие стеклянные пилюли: полупрозрачный фон + светлая рамка
    STYLES = {
        "Safe": ("Безопасно", "rgba(46, 160, 67, 0.22)", "#B7F0C0", "rgba(120, 220, 140, 0.45)"),
        "Moderate": ("Умеренно", "rgba(200, 150, 20, 0.22)", "#FFE9A8", "rgba(240, 200, 90, 0.45)"),
        "Advanced": ("Осторожно", "rgba(200, 60, 50, 0.25)", "#FFC9C4", "rgba(255, 130, 120, 0.45)"),
    }

    def __init__(self, risk: str = "Safe", parent=None) -> None:
        super().__init__(parent)
        self.set_risk(risk)

    def set_risk(self, risk: str) -> None:
        label, bg, fg, border = self.STYLES.get(risk, (risk, "#444", "#fff", "#888"))
        self.setText(f"● {label}")
        self.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {border}; "
            "border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: 600;"
        )


class CacheCard(QFrame):
    """Карточка одного правила: чекбокс, бейдж, размер, раскрывающееся объяснение."""

    toggled = Signal(str, bool)  # rule_id, checked
    open_requested = Signal(str)  # rule_id

    def __init__(self, rule: CacheRule, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.rule = rule
        self._size = 0
        self._count = 0
        self._expanded = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.check = QCheckBox()
        self.check.setToolTip("Включить в очистку")
        self.check.toggled.connect(lambda c: self.toggled.emit(self.rule.id, bool(c)))
        top.addWidget(self.check, 0, Qt.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.title_lbl = QLabel(rule.title)
        self.title_lbl.setObjectName("title")
        self.title_lbl.setWordWrap(True)
        title_box.addWidget(self.title_lbl)
        self.group_lbl = QLabel(rule.group)
        self.group_lbl.setObjectName("muted")
        title_box.addWidget(self.group_lbl)
        top.addLayout(title_box, 1)

        self.badge = RiskBadge(rule.risk)
        top.addWidget(self.badge, 0, Qt.AlignTop)

        self.size_lbl = QLabel("—")
        self.size_lbl.setObjectName("bigNumber")
        self.size_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.size_lbl.setMinimumWidth(120)
        top.addWidget(self.size_lbl, 0, Qt.AlignTop)

        root.addLayout(top)

        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("muted")
        root.addWidget(self.count_lbl)

        # Краткое описание всегда видно
        self.short_lbl = QLabel(rule.what)
        self.short_lbl.setObjectName("subtitle")
        self.short_lbl.setWordWrap(True)
        root.addWidget(self.short_lbl)

        # Развёрнутая часть
        self.detail_box = QWidget()
        dl = QVBoxLayout(self.detail_box)
        dl.setContentsMargins(0, 4, 0, 4)
        dl.setSpacing(4)
        self.why_lbl = QLabel(f"<b>Почему копится:</b> {rule.why}")
        self.why_lbl.setWordWrap(True)
        self.why_lbl.setObjectName("subtitle")
        self.safe_lbl = QLabel(f"<b>Безопасность:</b> {rule.safety}")
        self.safe_lbl.setWordWrap(True)
        self.safe_lbl.setObjectName("subtitle")
        self.rec_lbl = QLabel(f"<b>Рекомендация:</b> {rule.recommend}")
        self.rec_lbl.setWordWrap(True)
        self.rec_lbl.setObjectName("subtitle")
        self.path_lbl = QLabel("")
        self.path_lbl.setObjectName("mono")
        self.path_lbl.setWordWrap(True)
        self.path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dl.addWidget(self.why_lbl)
        dl.addWidget(self.safe_lbl)
        dl.addWidget(self.rec_lbl)
        dl.addWidget(self.path_lbl)
        self.detail_box.setVisible(False)
        root.addWidget(self.detail_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.more_btn = QPushButton("Подробнее ▾")
        self.more_btn.setObjectName("ghost")
        self.more_btn.setCursor(Qt.PointingHandCursor)
        self.more_btn.clicked.connect(self._toggle_detail)
        btn_row.addWidget(self.more_btn)
        self.open_btn = QPushButton("Открыть папку")
        self.open_btn.setObjectName("ghost")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(lambda: self.open_requested.emit(self.rule.id))
        btn_row.addWidget(self.open_btn)
        root.addLayout(btn_row)

    def _toggle_detail(self) -> None:
        self._expanded = not self._expanded
        self.detail_box.setVisible(self._expanded)
        self.more_btn.setText("Скрыть ▴" if self._expanded else "Подробнее ▾")

    def set_scan(self, size: int, count: int, paths_found: list[str]) -> None:
        self._size = size
        self._count = count
        self.size_lbl.setText(format_bytes(size))
        # Подсветка размера
        if size >= 1024 ** 3:
            self.size_lbl.setStyleSheet("color: #FF9D8A;")
        elif size >= 100 * 1024 ** 2:
            self.size_lbl.setStyleSheet("color: #FFD58A;")
        else:
            self.size_lbl.setStyleSheet("")
        if paths_found:
            shown = "<br>".join(paths_found[:4])
            extra = f"<br>… и ещё {len(paths_found) - 4}" if len(paths_found) > 4 else ""
            self.path_lbl.setText(f"📁 Найдено ({len(paths_found)}):<br>{shown}{extra}")
        else:
            self.path_lbl.setText("📁 Пути не найдены в этой системе — занимаемое место 0.")
        self.count_lbl.setText(f"Файлов: {format_count(count)}")
        # По умолчанию включаем только Safe с ненулевым размером
        should = self.rule.risk == "Safe" and size > 0
        self.check.blockSignals(True)
        self.check.setChecked(should)
        self.check.blockSignals(False)
        # Визуальное затухание пустых
        self.setStyleSheet("" if size > 0 else "QFrame#card { opacity: 1; }")
        self.setEnabled(True)

    def set_scanning(self) -> None:
        self.size_lbl.setText("…")
        self.count_lbl.setText("Сканирование…")

    @property
    def checked(self) -> bool:
        return self.check.isChecked()

    @property
    def size(self) -> int:
        return self._size

    def set_checked(self, v: bool) -> None:
        self.check.setChecked(v)


class StepBar(QWidget):
    """Индикатор «куда жать»: 1 Найти → 2 Выбрать → 3 Освободить."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._pills: list[QLabel] = []
        steps = [("1", "Найти мусор"), ("2", "Выбрать"), ("3", "Освободить")]
        for i, (num, text) in enumerate(steps):
            pill = QLabel(f"{num}  {text}")
            pill.setAlignment(Qt.AlignCenter)
            lay.addWidget(pill)
            self._pills.append(pill)
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 14px;")
                lay.addWidget(arrow)
        lay.addStretch(1)
        self.set_step(1)

    def set_step(self, n: int) -> None:
        """Подсветить текущий шаг (1..3), предыдущие — выполненные."""
        for i, pill in enumerate(self._pills, start=1):
            if i < n:
                pill.setStyleSheet(
                    "background: rgba(56,189,248,0.18); color: #7DD3FC; "
                    "border: 1px solid rgba(125,211,252,0.5); border-radius: 12px; "
                    "padding: 7px 16px; font-size: 13px; font-weight: 700;"
                )
                t = pill.text().replace("✓ ", "")
                pill.setText(f"✓ {t}" if not t.startswith("✓") else t)
            elif i == n:
                pill.setStyleSheet(
                    "background: #F5F7FA; color: #0B0D12; border: none; "
                    "border-radius: 12px; padding: 7px 16px; font-size: 13px; font-weight: 700;"
                )
            else:
                pill.setStyleSheet(
                    "background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.45); "
                    "border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; "
                    "padding: 7px 16px; font-size: 13px; font-weight: 500;"
                )
