"""Главное окно SmartSpace: навигация, дашборд, очистка, анализатор, система, лог."""
from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..analyzer import AnalyzerResult
from ..config import RULES, CacheRule, groups
from ..scanner import RuleScanResult
from ..system_info import get_disk_info, list_drives, special_files_report
from ..trash import CleanStats
from ..utils import copy_to_clipboard, format_bytes, format_count, open_in_explorer
from ..workers import AnalyzerWorker, CleanWorker, ScanWorker
from .fonts import load_fonts
from .wallpaper import frosted, wallpaper_pixmap
from .widgets import CacheCard, DonutChart, StepBar


class _WallpaperCentral(QWidget):
    """Фон + настоящий frosted glass: размытие рисуется под прозрачными панелями.

    Стеклянные виджеты регистрируются через register_glass(); их собственный
    фон в QSS — transparent, а размытие, тонировка и верхний блик рисуются здесь.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("centralRoot")
        self._base = None
        self._frost = None
        self._glass: list[tuple] = []  # (widget, alpha, radius)

    def register_glass(self, widget: QWidget, alpha: float = 0.52, radius: int = 18) -> None:
        self._glass.append((widget, alpha, radius))
        self.update()

    def set_wallpaper(self, base, frost) -> None:
        self._base = base
        self._frost = frost
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._base is None or self._base.isNull():
            return
        p = QPainter(self)
        try:
            p.drawPixmap(self.rect(), self._base)
            if self._frost is None or self._frost.isNull():
                return
            p.setRenderHint(QPainter.Antialiasing)
            for w, alpha, radius in list(self._glass):
                try:
                    if not w.isVisible():
                        continue
                    pos = w.mapTo(self, QPoint(0, 0))
                    r = QRect(pos.x(), pos.y(), w.width(), w.height())
                    if r.width() < 8 or r.height() < 8 or not r.intersects(self.rect()):
                        continue
                    path = QPainterPath()
                    if radius > 0:
                        path.addRoundedRect(r, radius, radius)
                    else:
                        path.addRect(r)
                    p.save()
                    p.setClipPath(path)
                    p.drawPixmap(r, self._frost, r)
                    p.fillRect(r, QColor(7, 11, 17, int(alpha * 255)))
                    # тонкое внутреннее свечение верхней грани
                    p.setPen(QColor(255, 255, 255, 30))
                    p.drawLine(r.left() + radius, r.top() + 1, r.right() - radius, r.top() + 1)
                    p.restore()
                except Exception:
                    try:
                        p.restore()
                    except Exception:
                        pass
        finally:
            p.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SmartSpace — менеджер дискового пространства")
        self.resize(1240, 860)
        self.setMinimumSize(1020, 700)

        self.scan_results: dict[str, RuleScanResult] = {}
        self.cards: dict[str, CacheCard] = {}
        self.rule_lookup: dict[str, CacheRule] = {r.id: r for r in RULES}
        self.scan_worker: ScanWorker | None = None
        self.analyzer_worker: AnalyzerWorker | None = None
        self.clean_worker: CleanWorker | None = None
        self.analyzer_result: AnalyzerResult | None = None

        self._build_chrome()
        self._build_dashboard()
        self._build_cleanup()
        self._build_analyzer()
        self._build_system_page()
        self._refresh_drives()
        self._refresh_dashboard()
        self._register_glass_and_glow()
        self._apply_wallpaper()
        self.log("👋 SmartSpace готов. Жмите «Найти мусор» — это шаг 1 из трёх.")

        # Автообновление дашборда раз в 30 сек (место могло измениться)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_dashboard)
        self._timer.start(30_000)

    # ================================================================== каркас
    def _build_chrome(self) -> None:
        central = _WallpaperCentral()
        self._central = central
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ---- Sidebar
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(224)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(12, 16, 12, 16)
        sl.setSpacing(6)

        logo = QLabel("◈ SmartSpace")
        logo.setObjectName("logo")
        sl.addWidget(logo)
        ver = QLabel("v1.0 • Windows • прозрачно и безопасно")
        ver.setObjectName("muted")
        ver.setWordWrap(True)
        ver.setStyleSheet("padding: 0 8px 8px 8px;")
        sl.addWidget(ver)

        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in [
            ("dash", "📊  Дашборд"),
            ("clean", "🧹  Очистка кэшей"),
            ("analyzer", "📁  Анализ диска"),
            ("system", "⚙️  Система"),
        ]:
            b = QPushButton(label)
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._navigate(k))
            sl.addWidget(b)
            self.nav_buttons[key] = b
        self.nav_buttons["dash"].setChecked(True)
        sl.addStretch(1)
        hint = QLabel("Удаление по умолчанию — в Корзину. Ничего не трогаем без галочки.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        sl.addWidget(hint)
        main.addWidget(side)
        self._sidebar = side

        # ---- Правая часть
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 16, 18, 12)
        rl.setSpacing(10)
        main.addWidget(right, 1)

        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)

        # ---- Низ: прогресс + лог
        bottom = QFrame()
        bottom.setObjectName("card")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(6)
        prow = QHBoxLayout()
        self.status_lbl = QLabel("Готов")
        self.status_lbl.setObjectName("muted")
        prow.addWidget(self.status_lbl, 1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(320)
        self.progress.setValue(0)
        prow.addWidget(self.progress)
        bl.addLayout(prow)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(130)
        self.log_view.setPlaceholderText("Лог выполнения…")
        bl.addWidget(self.log_view)
        rl.addWidget(bottom)

    def _navigate(self, key: str) -> None:
        mapping = {"dash": 0, "clean": 1, "analyzer": 2, "system": 3}
        self.stack.setCurrentIndex(mapping[key])
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)

    # ================================================================== дашборд
    def _build_dashboard(self) -> None:
        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(12)

        header = QHBoxLayout()
        t = QLabel("Состояние дисков")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        header.addWidget(t)
        header.addStretch(1)
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(140)
        self.drive_combo.currentTextChanged.connect(lambda _: self._refresh_dashboard())
        header.addWidget(QLabel("Диск:"))
        header.addWidget(self.drive_combo)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("ghost")
        refresh_btn.clicked.connect(self._refresh_dashboard)
        header.addWidget(refresh_btn)
        lay.addLayout(header)

        # Hero: человек сразу понимает, куда жать
        self._hero = hero = QFrame()
        hero.setObjectName("card")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(10)
        ht = QLabel("Освободите место за 3 шага")
        ht.setObjectName("heroTitle")
        hl.addWidget(ht)
        hs = QLabel("Сканирование ничего не удаляет. Вы отмечаете галочками нужное — мы аккуратно уносим это в Корзину. Каждый пункт объяснён на русском.")
        hs.setObjectName("heroSub")
        hs.setWordWrap(True)
        hl.addWidget(hs)
        self.step_bar_dash = StepBar()
        hl.addWidget(self.step_bar_dash)
        hrow = QHBoxLayout()
        hrow.setSpacing(10)
        self.hero_scan_btn = QPushButton("🔍  Найти мусор")
        self.hero_scan_btn.setObjectName("primary")
        self.hero_scan_btn.setCursor(Qt.PointingHandCursor)
        self.hero_scan_btn.clicked.connect(self.start_scan)
        hrow.addWidget(self.hero_scan_btn)
        hero_clean = QPushButton("Выбрать для очистки →")
        hero_clean.setObjectName("ghost")
        hero_clean.setCursor(Qt.PointingHandCursor)
        hero_clean.clicked.connect(lambda: self._navigate("clean"))
        hrow.addWidget(hero_clean)
        hero_analyzer = QPushButton("Тяжёлые файлы →")
        hero_analyzer.setObjectName("ghost")
        hero_analyzer.clicked.connect(lambda: self._navigate("analyzer"))
        hrow.addWidget(hero_analyzer)
        hrow.addStretch(1)
        hl.addLayout(hrow)
        lay.addWidget(hero)

        mid = QHBoxLayout()
        mid.setSpacing(12)

        donut_card = QFrame()
        donut_card.setObjectName("card")
        dl = QVBoxLayout(donut_card)
        dl.setContentsMargins(16, 16, 16, 16)
        self.donut = DonutChart()
        dl.addWidget(self.donut, 0, Qt.AlignCenter)
        self.donut_sub = QLabel("")
        self.donut_sub.setObjectName("muted")
        self.donut_sub.setAlignment(Qt.AlignCenter)
        dl.addWidget(self.donut_sub)
        mid.addWidget(donut_card, 0)

        stats_col = QVBoxLayout()
        stats_col.setSpacing(12)
        self.stat_cards: dict[str, QLabel] = {}
        for key, title in [("total", "Всего"), ("used", "Занято"), ("free", "Свободно")]:
            c = QFrame()
            c.setObjectName("card")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 12, 16, 12)
            lbl = QLabel(title)
            lbl.setObjectName("muted")
            cl.addWidget(lbl)
            big = QLabel("—")
            big.setObjectName("bigNumber")
            cl.addWidget(big)
            self.stat_cards[key] = big
            stats_col.addWidget(c)
        mid.addLayout(stats_col, 1)

        # Карточка потенциала очистки
        pot = QFrame()
        pot.setObjectName("card")
        pl = QVBoxLayout(pot)
        pl.setContentsMargins(16, 12, 16, 12)
        pl.addWidget(QLabel("Потенциал очистки (по последнему сканированию)"))
        self.potential_lbl = QLabel("Сканирование ещё не выполнялось")
        self.potential_lbl.setObjectName("bigNumber")
        self.potential_lbl.setWordWrap(True)
        pl.addWidget(self.potential_lbl)
        self.potential_detail = QLabel("")
        self.potential_detail.setObjectName("muted")
        self.potential_detail.setWordWrap(True)
        pl.addWidget(self.potential_detail)
        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("↻  Пересканировать")
        self.scan_btn.setObjectName("primary")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self.start_scan)
        btn_row.addWidget(self.scan_btn)
        self.stop_scan_btn = QPushButton("Остановить")
        self.stop_scan_btn.setObjectName("ghost")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        btn_row.addWidget(self.stop_scan_btn)
        go_clean = QPushButton("Перейти к очистке →")
        go_clean.setObjectName("ghost")
        go_clean.clicked.connect(lambda: self._navigate("clean"))
        btn_row.addWidget(go_clean)
        btn_row.addStretch(1)
        pl.addLayout(btn_row)
        stats_col.addWidget(pot)

        lay.addLayout(mid)

        # Подсказка про гибернацию
        self.hiber_hint = QLabel("")
        self.hiber_hint.setObjectName("muted")
        self.hiber_hint.setWordWrap(True)
        lay.addWidget(self.hiber_hint)
        lay.addStretch(1)
        scroll.setWidget(inner)
        page_lay.addWidget(scroll)
        self.stack.addWidget(page)

    # ================================================================== очистка
    def _build_cleanup(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        header = QHBoxLayout()
        t = QLabel("Найденные кэши и временные файлы")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        header.addWidget(t)
        header.addStretch(1)
        self.risk_filter = QComboBox()
        self.risk_filter.addItems(["Все уровни риска", "Безопасно", "Умеренно", "Осторожно"])
        self.risk_filter.currentIndexChanged.connect(self._apply_card_filter)
        header.addWidget(self.risk_filter)
        self.group_filter = QComboBox()
        self.group_filter.addItem("Все группы")
        for g in groups():
            self.group_filter.addItem(g)
        self.group_filter.currentIndexChanged.connect(self._apply_card_filter)
        header.addWidget(self.group_filter)
        lay.addLayout(header)

        # Поиск как на референсе + шаги
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("🔍  Поиск по кэшам: например, Telegram, npm, шейдеры…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._apply_card_filter)
        lay.addWidget(self.search_box)
        self.step_bar_clean = StepBar()
        lay.addWidget(self.step_bar_clean)

        toolbar = QHBoxLayout()
        rescan = QPushButton("↻ Пересканировать")
        rescan.setObjectName("ghost")
        rescan.clicked.connect(self.start_scan)
        toolbar.addWidget(rescan)
        sel_safe = QPushButton("Выбрать только безопасные")
        sel_safe.setObjectName("ghost")
        sel_safe.clicked.connect(self._select_safe)
        toolbar.addWidget(sel_safe)
        sel_all = QPushButton("Выбрать всё")
        sel_all.setObjectName("ghost")
        sel_all.clicked.connect(self._select_all)
        toolbar.addWidget(sel_all)
        sel_none = QPushButton("Снять выбор")
        sel_none.setObjectName("ghost")
        sel_none.clicked.connect(self._select_none)
        toolbar.addWidget(sel_none)
        toolbar.addStretch(1)
        self.selected_lbl = QLabel("Выбрано: 0 Б")
        self.selected_lbl.setObjectName("muted")
        toolbar.addWidget(self.selected_lbl)
        lay.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(2, 2, 2, 2)
        # Группировка по смыслу: заголовок + карточки
        for grp in groups():
            gh = QLabel(grp.upper())
            gh.setObjectName("muted")
            gh.setProperty("group", grp)
            self.cards_layout.addWidget(gh)
            for rule in [r for r in RULES if r.group == grp]:
                card = CacheCard(rule)
                card.toggled.connect(lambda _c, _r=rule.id: self._update_selected())
                card.open_requested.connect(self._open_rule_folder)
                card.set_scanning()
                self.cards[rule.id] = card
                self.cards_layout.addWidget(card)
        self.cards_layout.addStretch(1)
        scroll.setWidget(self.cards_host)
        lay.addWidget(scroll, 1)

        self._actionbar = bar = QFrame()
        bar.setObjectName("actionbar")
        actions = QHBoxLayout(bar)
        actions.setContentsMargins(14, 12, 14, 12)
        actions.setSpacing(10)
        self.clean_trash_btn = QPushButton("🧹 Выбрать кэши выше ↑")
        self.clean_trash_btn.setObjectName("primary")
        self.clean_trash_btn.setCursor(Qt.PointingHandCursor)
        self.clean_trash_btn.clicked.connect(lambda: self.start_clean(permanent=False))
        actions.addWidget(self.clean_trash_btn)
        self.clean_perm_btn = QPushButton("Удалить навсегда")
        self.clean_perm_btn.setObjectName("danger")
        self.clean_perm_btn.setCursor(Qt.PointingHandCursor)
        self.clean_perm_btn.clicked.connect(lambda: self.start_clean(permanent=True))
        actions.addWidget(self.clean_perm_btn)
        actions.addStretch(1)
        self.clean_status = QLabel("")
        self.clean_status.setObjectName("muted")
        actions.addWidget(self.clean_status)
        lay.addWidget(bar)

        self.stack.addWidget(page)

    # ================================================================== анализ
    def _build_analyzer(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        header = QHBoxLayout()
        t = QLabel("Анализ диска: топ тяжёлых файлов и папок")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        header.addWidget(t)
        header.addStretch(1)
        header.addWidget(QLabel("Диск/папка:"))
        self.analyzer_combo = QComboBox()
        self.analyzer_combo.setEditable(True)
        self.analyzer_combo.setMinimumWidth(220)
        header.addWidget(self.analyzer_combo)
        self.analyzer_start = QPushButton("▶ Анализировать")
        self.analyzer_start.setObjectName("primary")
        self.analyzer_start.clicked.connect(self.start_analysis)
        header.addWidget(self.analyzer_start)
        self.analyzer_stop = QPushButton("Стоп")
        self.analyzer_stop.setObjectName("ghost")
        self.analyzer_stop.clicked.connect(self.stop_analysis)
        self.analyzer_stop.setEnabled(False)
        header.addWidget(self.analyzer_stop)
        lay.addLayout(header)

        self.analyzer_summary = QLabel("Выберите диск и нажмите «Анализировать». Сканирование сотни тысяч файлов занимает 1–3 минуты.")
        self.analyzer_summary.setObjectName("muted")
        self.analyzer_summary.setWordWrap(True)
        lay.addWidget(self.analyzer_summary)

        from PySide6.QtWidgets import QTabWidget

        tabs = QTabWidget()
        # Топ файлов
        self.top_files_table = QTableWidget(0, 3)
        self.top_files_table.setHorizontalHeaderLabels(["Размер", "Файл", "Путь"])
        self.top_files_table.setAlternatingRowColors(True)
        self.top_files_table.setSortingEnabled(True)
        self.top_files_table.setWordWrap(False)
        self.top_files_table.doubleClicked.connect(lambda idx: self._reveal_from_table(self.top_files_table, idx.row(), col_path=2))
        tabs.addTab(self.top_files_table, "Топ-100 файлов")
        # Топ папок
        self.top_dirs_table = QTableWidget(0, 2)
        self.top_dirs_table.setHorizontalHeaderLabels(["Размер", "Папка"])
        self.top_dirs_table.setAlternatingRowColors(True)
        self.top_dirs_table.setSortingEnabled(True)
        self.top_dirs_table.doubleClicked.connect(lambda idx: self._reveal_from_table(self.top_dirs_table, idx.row(), col_path=1))
        tabs.addTab(self.top_dirs_table, "Топ-100 папок")
        # По расширениям
        self.ext_table = QTableWidget(0, 3)
        self.ext_table.setHorizontalHeaderLabels(["Расширение", "Размер", "Файлов"])
        self.ext_table.setAlternatingRowColors(True)
        self.ext_table.setSortingEnabled(True)
        tabs.addTab(self.ext_table, "По типам файлов")
        lay.addWidget(tabs, 1)
        hint = QLabel("Двойной клик по строке — показать в Проводнике. Файлы здесь НЕ удаляются автоматически: удаляйте осознанно через Проводник или Корзину.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.stack.addWidget(page)

    # ================================================================== система
    def _build_system_page(self) -> None:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        t = QLabel("Система: спецфайлы и команды")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        lay.addWidget(t)
        info = QLabel(
            "hiberfil.sys и pagefile.sys удалять как файлы НЕЛЬЗЯ — только штатными командами. "
            "Ниже — живой отчёт по диску C: и безопасные действия."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        hl = QVBoxLayout(host)
        hl.setSpacing(10)
        self.sys_cards: list[tuple[dict, QLabel]] = []
        for item in special_files_report("C:\\"):
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            title = QLabel(f"{item['title']}")
            title.setObjectName("title")
            cl.addWidget(title)
            path = QLabel(item["path"])
            path.setObjectName("mono")
            path.setTextInteractionFlags(Qt.TextSelectableByMouse)
            cl.addWidget(path)
            size_lbl = QLabel("")
            size_lbl.setObjectName("subtitle")
            cl.addWidget(size_lbl)
            det = QLabel(item["detail"])
            det.setObjectName("subtitle")
            det.setWordWrap(True)
            cl.addWidget(det)
            hl.addWidget(card)
            self.sys_cards.append((item, size_lbl))
        hl.addStretch(1)
        scroll.setWidget(host)
        lay.addWidget(scroll, 1)

        row = QHBoxLayout()
        copy_hiber = QPushButton("📋 Скопировать: powercfg -h off")
        copy_hiber.setObjectName("ghost")
        copy_hiber.clicked.connect(lambda: self._copy_cmd("powercfg -h off"))
        row.addWidget(copy_hiber)
        copy_hiber_on = QPushButton("📋 Скопировать: powercfg -h on")
        copy_hiber_on.setObjectName("ghost")
        copy_hiber_on.clicked.connect(lambda: self._copy_cmd("powercfg -h on"))
        row.addWidget(copy_hiber_on)
        cleanmgr = QPushButton("🧰 Открыть «Очистку диска» Windows")
        cleanmgr.setObjectName("ghost")
        cleanmgr.clicked.connect(self._open_cleanmgr)
        row.addWidget(cleanmgr)
        row.addStretch(1)
        lay.addLayout(row)
        warn = QLabel("Команды powercfg выполняйте в Терминале от имени администратора. Отключение гибернации удалит hiberfil.sys и отключит быстрый запуск гибернации (сон останется).")
        warn.setObjectName("muted")
        warn.setWordWrap(True)
        lay.addWidget(warn)
        self.stack.addWidget(page)

    # ================================================================== данные
    def _refresh_drives(self) -> None:
        drives = list_drives()
        cur1 = self.drive_combo.currentText() if hasattr(self, "drive_combo") else ""
        self.drive_combo.blockSignals(True)
        self.drive_combo.clear()
        self.drive_combo.addItems(drives if drives else ["C:\\"])
        if cur1 in drives:
            self.drive_combo.setCurrentText(cur1)
        self.drive_combo.blockSignals(False)
        if hasattr(self, "analyzer_combo"):
            cur2 = self.analyzer_combo.currentText()
            self.analyzer_combo.clear()
            self.analyzer_combo.addItems(drives if drives else ["C:\\"])
            if cur2:
                self.analyzer_combo.setCurrentText(cur2)

    def _current_drive(self) -> str:
        t = self.drive_combo.currentText().strip() if hasattr(self, "drive_combo") else "C:\\"
        return t or "C:\\"

    def _refresh_dashboard(self) -> None:
        drive = self._current_drive()
        info = get_disk_info(drive)
        if info is None:
            self.status_lbl.setText(f"Не удалось прочитать диск {drive}")
            return
        self.donut.set_values(info.used, info.total, format_bytes(info.free), "свободно")
        self.donut_sub.setText(f"{info.mountpoint} • {info.fstype or '—'} • {info.device or ''}")
        self.stat_cards["total"].setText(format_bytes(info.total))
        self.stat_cards["used"].setText(format_bytes(info.used))
        self.stat_cards["free"].setText(format_bytes(info.free))
        # hiber hint
        try:
            hpath = os.path.join(os.path.abspath(drive)[:3], "hiberfil.sys")
            if os.path.exists(hpath):
                sz = os.path.getsize(hpath)
                self.hiber_hint.setText(
                    f"💡 На {drive} активна гибернация ({format_bytes(sz)} в hiberfil.sys). "
                    f"Если не пользуетесь гибернацией — отключите командой powercfg -h off (вкладка «Система»)."
                )
            else:
                self.hiber_hint.setText("💡 Файл гибернации не найден — гибернация уже отключена. Так держать.")
        except Exception:
            pass
        # Системные карточки
        if hasattr(self, "sys_cards"):
            for item, lbl in self.sys_cards:
                if item["exists"]:
                    sz = item.get("size", 0)
                    txt = format_bytes(sz) if isinstance(sz, int) and sz >= 0 else "доступ запрещён"
                    lbl.setText(f"Найден • размер: {txt}")
                else:
                    lbl.setText("Не найден — всё чисто.")

    # ================================================================== лог
    def log(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {text}")
        sb = self.log_view.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())

    # ================================================================== скан
    def start_scan(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        self._navigate("clean")
        for card in self.cards.values():
            card.set_scanning()
        self.scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.progress.setRange(0, len(RULES))
        self.progress.setValue(0)
        self.status_lbl.setText("Сканирование…")
        self.step_bar_dash.set_step(1)
        self.step_bar_clean.set_step(1)
        self.scan_worker = ScanWorker(self)
        self.scan_worker.progressed.connect(self._on_scan_progress)
        self.scan_worker.log_line.connect(self.log)
        self.scan_worker.finished_ok.connect(self._on_scan_done)
        self.scan_worker.start()

    def stop_scan(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.log("⏹ Остановка сканирования…")

    def _on_scan_progress(self, done: int, total: int, title: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.status_lbl.setText(f"Сканирование {done}/{total}: {title}")

    def _on_scan_done(self, results: list) -> None:
        typed: list[RuleScanResult] = list(results)
        self.scan_results = {r.rule_id: r for r in typed}
        total = sum(r.size_bytes for r in typed)
        safe_total = sum(r.size_bytes for r in typed if r.risk == "Safe")
        self.potential_lbl.setText(f"≈ {format_bytes(total)} всего • {format_bytes(safe_total)} безопасно")
        top = sorted(typed, key=lambda r: r.size_bytes, reverse=True)[:3]
        det = "; ".join(f"{r.title} — {format_bytes(r.size_bytes)}" for r in top if r.size_bytes > 0)
        self.potential_detail.setText(f"Крупнейшее: {det}" if det else "Кэши не найдены — система чистая. Проверьте вкладку «Анализ диска».")
        for r in typed:
            card = self.cards.get(r.rule_id)
            if card is not None:
                card.set_scan(r.size_bytes, r.file_count, r.paths_found)
        self._update_selected()
        self._apply_card_filter()
        self.step_bar_dash.set_step(2)
        self.step_bar_clean.set_step(2)
        self.scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.status_lbl.setText("Готов")
        self.progress.setValue(self.progress.maximum())
        self.log(f"📦 Итого найдено: {format_bytes(total)} в {len(typed)} категориях (файлов: {format_count(sum(r.file_count for r in typed))}).")
        self.scan_worker = None

    # ================================================================== выбор
    def _selected_rules(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for rid, card in self.cards.items():
            if card.checked and card.size > 0:
                res = self.scan_results.get(rid)
                if res and res.paths_found:
                    out[rid] = list(res.paths_found)
        return out

    def _update_selected(self) -> None:
        total = sum(c.size for c in self.cards.values() if c.checked)
        n = sum(1 for c in self.cards.values() if c.checked)
        self.selected_lbl.setText(f"Выбрано: {format_bytes(total)} ({n} кат.)")
        if hasattr(self, "clean_trash_btn"):
            if total > 0:
                self.clean_trash_btn.setText(f"🧹 Освободить {format_bytes(total)} → в Корзину")
            else:
                self.clean_trash_btn.setText("🧹 Выбрать кэши выше ↑")

    def _select_safe(self) -> None:
        for rid, card in self.cards.items():
            card.set_checked(card.rule.risk == "Safe" and card.size > 0)
        self._update_selected()

    def _select_all(self) -> None:
        adv = [c for c in self.cards.values() if c.rule.risk == "Advanced" and c.size > 0]
        if adv:
            box = QMessageBox(self)
            box.setWindowTitle("Подтверждение")
            box.setIcon(QMessageBox.Warning)
            box.setText(f"Вы выбрали {len(adv)} категории уровня «Осторожно» (Docker/WSL, Windows.old, гибернация). Продолжить выбор всех?")
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Yes:
                return
        for card in self.cards.values():
            card.set_checked(card.size > 0)
        self._update_selected()

    def _select_none(self) -> None:
        for card in self.cards.values():
            card.set_checked(False)
        self._update_selected()

    def _apply_card_filter(self) -> None:
        risk_txt = self.risk_filter.currentText()
        grp_txt = self.group_filter.currentText()
        risk_map = {"Безопасно": "Safe", "Умеренно": "Moderate", "Осторожно": "Advanced"}
        want_risk = risk_map.get(risk_txt)
        q = self.search_box.text().strip().lower() if hasattr(self, "search_box") else ""

        def _matches(rule) -> bool:
            if want_risk is not None and rule.risk != want_risk:
                return False
            if grp_txt != "Все группы" and rule.group != grp_txt:
                return False
            if q and q not in f"{rule.title} {rule.group} {rule.what}".lower():
                return False
            return True

        # Проходим по layout: заголовки групп имеют свойство group
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            w = item.widget()
            if w is None:
                continue
            grp = w.property("group")
            if grp is not None:  # заголовок группы
                # показать заголовок только если есть видимые карточки группы
                visible = any(_matches(r) for r in RULES if r.group == grp)
                w.setVisible(visible)
            elif isinstance(w, CacheCard):
                w.setVisible(_matches(w.rule))

    def _open_rule_folder(self, rule_id: str) -> None:
        res = self.scan_results.get(rule_id)
        paths = res.paths_found if res else []
        if not paths:
            rule = self.rule_lookup.get(rule_id)
            from ..utils import resolve_many

            paths = resolve_many(rule.paths) if rule else []
        if paths:
            open_in_explorer(paths[0])
        else:
            QMessageBox.information(self, "Папка не найдена", "Ни один из путей этой категории не существует в системе.")

    # ================================================================== очистка
    def start_clean(self, permanent: bool) -> None:
        if self.clean_worker is not None and self.clean_worker.isRunning():
            return
        sel = self._selected_rules()
        if not sel:
            QMessageBox.information(self, "Нечего чистить", "Отметьте галочками хотя бы одну категорию с ненулевым размером.")
            return
        est = sum(self.scan_results[r].size_bytes for r in sel if r in self.scan_results)
        if permanent:
            box = QMessageBox(self)
            box.setWindowTitle("Удалить навсегда?")
            box.setIcon(QMessageBox.Warning)
            box.setText(
                f"Будет БЕЗВОЗВРАТНО удалено ≈ {format_bytes(est)} в {len(sel)} категориях.\n\n"
                "Восстановить будет нельзя. Продолжить?"
            )
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Yes:
                return
        else:
            box = QMessageBox(self)
            box.setWindowTitle("Переместить в Корзину?")
            box.setIcon(QMessageBox.Question)
            box.setText(f"Будет перемещено в Корзину ≈ {format_bytes(est)} в {len(sel)} категориях.\nПродолжить?")
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Yes)
            if box.exec() != QMessageBox.Yes:
                return
        self.clean_trash_btn.setEnabled(False)
        self.clean_perm_btn.setEnabled(False)
        self.clean_status.setText("Очистка выполняется…")
        self.step_bar_clean.set_step(3)
        self.clean_worker = CleanWorker(sel, permanent=permanent, parent=self)
        self.clean_worker.log_line.connect(self.log)
        self.clean_worker.finished_ok.connect(lambda st: self._on_clean_done(st, permanent))
        self.clean_worker.start()

    def _on_clean_done(self, stats: CleanStats, permanent: bool) -> None:
        self.clean_trash_btn.setEnabled(True)
        self.clean_perm_btn.setEnabled(True)
        self.clean_status.setText(
            f"Готово: ≈ {format_bytes(stats.freed_bytes_estimate)} • пропущено занятых: {stats.skipped_locked}"
        )
        # Пересканировать молча для обновления цифр
        self.log("🔄 Обновляю цифры после очистки…")
        self.start_scan()
        self.clean_worker = None

    # ================================================================== анализ
    def start_analysis(self) -> None:
        if self.analyzer_worker is not None and self.analyzer_worker.isRunning():
            return
        root = self.analyzer_combo.currentText().strip() or "C:\\"
        if not os.path.isdir(root):
            QMessageBox.warning(self, "Нет папки", f"Путь не существует: {root}")
            return
        self.analyzer_start.setEnabled(False)
        self.analyzer_stop.setEnabled(True)
        self.progress.setRange(0, 0)  # indeterminate
        self.status_lbl.setText(f"Анализ {root} …")
        self.analyzer_summary.setText(f"Сканирую {root} …")
        self.analyzer_worker = AnalyzerWorker(root, self)
        self.analyzer_worker.progressed.connect(lambda p: self.status_lbl.setText(f"… {p[:90]}"))
        self.analyzer_worker.log_line.connect(self.log)
        self.analyzer_worker.finished_ok.connect(self._on_analysis_done)
        self.analyzer_worker.start()

    def stop_analysis(self) -> None:
        if self.analyzer_worker is not None and self.analyzer_worker.isRunning():
            self.analyzer_worker.stop()
            self.log("⏹ Остановка анализа…")

    def _on_analysis_done(self, res: AnalyzerResult) -> None:
        self.analyzer_result = res
        self.analyzer_start.setEnabled(True)
        self.analyzer_stop.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.status_lbl.setText("Готов")
        self.analyzer_summary.setText(
            f"Готово: {res.root} • {format_bytes(res.total_size)} в {format_count(res.total_files)} файлах, "
            f"{format_count(res.total_dirs)} папок. Пропущено из-за доступа: {res.skipped_errors}."
        )
        self._fill_table_files(res)
        self._fill_table_dirs(res)
        self._fill_table_ext(res)
        self.log(f"📊 {res.root}: топ-файл — {res.top_files[0][0]} ({format_bytes(res.top_files[0][1])})" if res.top_files else "📊 Пусто.")
        self.analyzer_worker = None

    def _fill_table_files(self, res: AnalyzerResult) -> None:
        t = self.top_files_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.top_files))
        for i, (path, size) in enumerate(res.top_files):
            t.setItem(i, 0, QTableWidgetItem(size))
            name_item = QTableWidgetItem(os.path.basename(path))
            name_item.setToolTip(path)
            t.setItem(i, 1, name_item)
            p_item = QTableWidgetItem(path)
            p_item.setToolTip(path)
            t.setItem(i, 2, p_item)
            # Числовая сортировка: храним размер в UserRole
            t.item(i, 0).setData(Qt.UserRole, size)
            t.item(i, 0).setText(format_bytes(size))
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(True)

    def _fill_table_dirs(self, res: AnalyzerResult) -> None:
        t = self.top_dirs_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.top_dirs))
        for i, (path, size) in enumerate(res.top_dirs):
            it = QTableWidgetItem(format_bytes(size))
            it.setData(Qt.UserRole, size)
            t.setItem(i, 0, it)
            p = QTableWidgetItem(path)
            p.setToolTip(path)
            t.setItem(i, 1, p)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(True)

    def _fill_table_ext(self, res: AnalyzerResult) -> None:
        t = self.ext_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.by_extension))
        for i, (ext, size, count) in enumerate(res.by_extension):
            t.setItem(i, 0, QTableWidgetItem(f".{ext}" if not ext.startswith("(") else ext))
            it = QTableWidgetItem(format_bytes(size))
            it.setData(Qt.UserRole, size)
            t.setItem(i, 1, it)
            c = QTableWidgetItem(format_count(count))
            c.setData(Qt.UserRole, count)
            t.setItem(i, 2, c)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()

    def _reveal_from_table(self, table: QTableWidget, row: int, col_path: int) -> None:
        item = table.item(row, col_path)
        if item is not None:
            open_in_explorer(item.text())

    # ================================================================== система
    def _copy_cmd(self, cmd: str) -> None:
        ok = copy_to_clipboard(cmd)
        # Fallback через Qt
        if not ok:
            QApplication.clipboard().setText(cmd)
            ok = True
        self.log(f"📋 Команда скопирована: {cmd}" if ok else "⚠ Не удалось скопировать.")
        QMessageBox.information(
            self, "Скопировано",
            f"Команда скопирована:\n\n{cmd}\n\nВыполните её в Терминале (Администратор):\nWin+X → Терминал (Администратор).",
        )

    def _open_cleanmgr(self) -> None:
        import subprocess

        try:
            subprocess.Popen(["cleanmgr.exe"])
            self.log("🧰 Запущена штатная «Очистка диска» Windows.")
        except Exception as e:
            QMessageBox.warning(self, "Не запустилось", f"Не удалось запустить cleanmgr.exe: {e}")

    # ================================================================== фон
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_wallpaper()

    def _apply_wallpaper(self) -> None:
        try:
            w, h = self._central.width(), self._central.height()
            if w < 10 or h < 10:
                return
            self._central.set_wallpaper(wallpaper_pixmap(w, h), frosted(w, h))
        except Exception:
            pass

    # ================================================================== стекло и свечение
    @staticmethod
    def _add_glow(widget: QWidget, r: int, g: int, b: int, a: int = 70, blur: int = 32) -> None:
        try:
            eff = QGraphicsDropShadowEffect(widget)
            eff.setColor(QColor(r, g, b, a))
            eff.setBlurRadius(blur)
            eff.setOffset(0)
            widget.setGraphicsEffect(eff)
        except Exception:
            pass

    def _register_glass_and_glow(self) -> None:
        for f in self._central.findChildren(QFrame):
            name = f.objectName()
            if name == "card":
                self._central.register_glass(f, 0.42, 18)
            elif name == "actionbar":
                self._central.register_glass(f, 0.50, 16)
        self._central.register_glass(self._sidebar, 0.42, 0)
        # Свечение акцентов сквозь стекло
        self._add_glow(self._hero, 125, 211, 252, 55, 48)
        self._add_glow(self.hero_scan_btn, 255, 255, 255, 55, 26)
        self._add_glow(self.clean_trash_btn, 255, 255, 255, 45, 24)
        self._add_glow(self.donut, 125, 211, 252, 50, 30)
        self._add_glow(self._actionbar, 0, 0, 0, 170, 40)

    # ================================================================== выход
    def closeEvent(self, event) -> None:  # noqa: N802
        for w in (self.scan_worker, self.analyzer_worker, self.clean_worker):
            try:
                if w is not None and w.isRunning():
                    if hasattr(w, "stop"):
                        w.stop()
                    w.wait(1500)
            except Exception:
                pass
        super().closeEvent(event)


def create_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SmartSpace")
    app.setOrganizationName("SmartSpace")
    load_fonts()
    from .styles import GLASS_QSS

    app.setStyleSheet(GLASS_QSS)
    return app  # type: ignore[return-value]
