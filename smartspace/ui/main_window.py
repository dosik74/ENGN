"""Главное окно SmartSpace «Моя волна»: сайдбар + сцена-плеер + страницы. Логика не менялась."""
from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
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
from .sidebar import Sidebar, avatar_pixmap
from .stage import StageWidget
from .theme import palette_for_group
from .widgets import CacheCard


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SmartSpace — менеджер дискового пространства")
        self.resize(1200, 760)
        self.setMinimumSize(1000, 650)

        self.scan_results: dict[str, RuleScanResult] = {}
        self.cards: dict[str, CacheCard] = {}
        self.rule_lookup: dict[str, CacheRule] = {r.id: r for r in RULES}
        self.scan_worker: ScanWorker | None = None
        self.analyzer_worker: AnalyzerWorker | None = None
        self.clean_worker: CleanWorker | None = None
        self.analyzer_result: AnalyzerResult | None = None
        self._focus_id: str = "windows_temp"
        self._log_visible = True

        self._build_chrome()
        self._build_home()
        self._build_search()
        self._build_recs()
        self._build_library()
        self._build_settings()
        self._refresh_recs()
        self._refresh_drives()
        self._refresh_dashboard()
        self.set_stage_focus(self._focus_id, initial=True)
        self.log("👋 SmartSpace готов. Жми play на сцене — это шаг 1 из трёх.")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_dashboard)
        self._timer.start(30_000)

    # ================================================================== каркас
    def _build_chrome(self) -> None:
        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.nav_requested.connect(self._navigate)
        self.sidebar.group_requested.connect(self._on_group_requested)
        main.addWidget(self.sidebar)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        main.addWidget(right, 1)

        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)

        # ---- Низ: прогресс + лог
        self._bottom = QFrame()
        self._bottom.setObjectName("card")
        bl = QVBoxLayout(self._bottom)
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
        self.log_view.setFixedHeight(110)
        self.log_view.setPlaceholderText("Лог выполнения…")
        bl.addWidget(self.log_view)
        rl.addWidget(self._bottom)

    def _navigate(self, key: str) -> None:
        mapping = {"home": 0, "search": 1, "recs": 2, "library": 3, "settings": 4}
        if key not in mapping:
            return
        self.stack.setCurrentIndex(mapping[key])
        self.sidebar.set_active(key)
        self.stage.set_section({"home": "Главная", "search": "Поиск", "recs": "Рекомендации",
                                "library": "Библиотека", "settings": "Настройки"}[key])

    def _on_group_requested(self, group: str) -> None:
        idx = self.group_filter.findText(group)
        if idx >= 0:
            self.group_filter.setCurrentIndex(idx)
        self._navigate("search")

    # ================================================================== дом (сцена)
    def _build_home(self) -> None:
        self.stage = StageWidget()
        self.stage.transport_pressed.connect(self._on_transport)
        self.stage.round_pressed.connect(self._on_round)
        self.stage.pill_pressed.connect(lambda: self._navigate("search"))
        self.stage.hint_closed.connect(self._toggle_log)
        self.stage.cloud_focused.connect(self._on_cloud)
        self.stack.addWidget(self.stage)

    def _on_transport(self, action: str) -> None:
        if action == "play":
            if self.scan_worker is not None and self.scan_worker.isRunning():
                self.stop_scan()
            else:
                self.start_scan()
        elif action == "repeat":
            self.start_scan()
        elif action == "shuffle":
            self._select_safe()
            self._navigate("search")
        elif action in ("prev", "next"):
            self._cycle_focus(-1 if action == "prev" else 1)

    def _on_round(self, action: str) -> None:
        if action == "open":
            self._open_rule_folder(self._focus_id)
        elif action == "safe":
            self._select_safe()
            self._navigate("search")
        elif action == "clear":
            self._select_none()
        elif action == "details":
            self._show_focus_details()
        elif action == "trash":
            self.start_clean(permanent=False)

    def _on_cloud(self, group: str) -> None:
        cands = [r for r in RULES if r.group == group]
        if not cands:
            return
        if self.scan_results:
            cands.sort(key=lambda r: self.scan_results.get(r.id).size_bytes if self.scan_results.get(r.id) else -1,
                       reverse=True)
        self.set_stage_focus(cands[0].id)

    def _cycle_focus(self, step: int) -> None:
        ids = [r.id for r in RULES
               if (self.scan_results.get(r.id) is None or self.scan_results[r.id].size_bytes > 0)]
        if not ids:
            ids = [r.id for r in RULES]
        try:
            i = ids.index(self._focus_id)
        except ValueError:
            i = 0
        self.set_stage_focus(ids[(i + step) % len(ids)])

    def set_stage_focus(self, rule_id: str, initial: bool = False) -> None:
        rule = self.rule_lookup.get(rule_id)
        if rule is None:
            return
        self._focus_id = rule_id
        res = self.scan_results.get(rule_id)
        self.stage.set_hero(rule.title)
        self.stage.set_cover_group(rule.group)
        if res is None:
            self.stage.set_pill("Нажми play — найдём мусор" if initial else f"{rule.title} • ещё не сканировано")
        elif res.size_bytes > 0:
            self.stage.set_pill(f"{rule.title} • {format_bytes(res.size_bytes)}")
        else:
            self.stage.set_pill(f"{rule.title} • чисто")
        self.stage.set_palette_key(palette_for_group(rule.group))

    def _show_focus_details(self) -> None:
        self._navigate("search")
        card = self.cards.get(self._focus_id)
        if card is None:
            return
        try:
            if not card._expanded:
                card.more_btn.click()
        except Exception:
            pass
        try:
            self._search_scroll.ensureWidgetVisible(card)
        except Exception:
            pass

    def _toggle_log(self) -> None:
        self._log_visible = not self._log_visible
        self._bottom.setVisible(self._log_visible)
        self.stage.close_link.setText("Закрыть" if self._log_visible else "Показать лог")

    # ================================================================== поиск (бывшая очистка)
    def _build_search(self) -> None:
        page = QWidget()
        page.setObjectName("page")
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 16, 18, 12)

        header = QHBoxLayout()
        t = QLabel("Поиск по кэшам")
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

        self.search_box = QLineEdit()
        self.search_box.setObjectName("search")
        self.search_box.setPlaceholderText("🔍  Поиск по кэшам: например, Telegram, npm, шейдеры…")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._apply_card_filter)
        lay.addWidget(self.search_box)

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

        self._search_scroll = QScrollArea()
        self._search_scroll.setWidgetResizable(True)
        self._search_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(2, 2, 2, 2)
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
        self._search_scroll.setWidget(self.cards_host)
        lay.addWidget(self._search_scroll, 1)

        bar = QFrame()
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

    # ================================================================== рекомендации
    def _build_recs(self) -> None:
        page = QWidget()
        page.setObjectName("page")
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 16, 18, 12)
        t = QLabel("Рекомендации")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        lay.addWidget(t)
        sub = QLabel("Только безопасные категории с ненулевым размером — то, что можно чистить не глядя.")
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        self.recs_list = QListWidget()
        self.recs_list.setAlternatingRowColors(True)
        lay.addWidget(self.recs_list, 1)
        row = QHBoxLayout()
        apply_btn = QPushButton("Выбрать эти в очистке")
        apply_btn.setObjectName("ghost")
        apply_btn.clicked.connect(self._apply_recs)
        row.addWidget(apply_btn)
        clean_btn = QPushButton("🧹 Очистить выбранное")
        clean_btn.setObjectName("primary")
        clean_btn.clicked.connect(lambda: self.start_clean(permanent=False))
        row.addWidget(clean_btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.stack.addWidget(page)
        self._rec_ids: list[str] = []

    def _refresh_recs(self) -> None:
        self.recs_list.clear()
        self._rec_ids = []
        cands = sorted(
            (r for r in self.scan_results.values() if r.risk == "Safe" and r.size_bytes > 0),
            key=lambda r: r.size_bytes, reverse=True,
        )[:10]
        if not cands:
            QListWidgetItem("Пока пусто — нажми play на Главной.", self.recs_list)
            return
        for r in cands:
            rule = self.rule_lookup.get(r.rule_id)
            why = f" — {rule.recommend}" if rule and rule.recommend else ""
            QListWidgetItem(f"{r.title} — {format_bytes(r.size_bytes)}{why}", self.recs_list)
            self._rec_ids.append(r.rule_id)

    def _apply_recs(self) -> None:
        if not self._rec_ids:
            return
        for rid, card in self.cards.items():
            card.set_checked(rid in self._rec_ids and card.size > 0)
        self._update_selected()
        self._navigate("search")

    # ================================================================== библиотека (анализ)
    def _build_library(self) -> None:
        page = QWidget()
        page.setObjectName("page")
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 16, 18, 12)

        header = QHBoxLayout()
        t = QLabel("Библиотека: тяжёлые файлы и папки")
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

        self.analyzer_summary = QLabel("Выберите диск и нажмите «Анализировать». Сотни тысяч файлов — 1–3 минуты.")
        self.analyzer_summary.setObjectName("muted")
        self.analyzer_summary.setWordWrap(True)
        lay.addWidget(self.analyzer_summary)

        from PySide6.QtWidgets import QTabWidget

        tabs = QTabWidget()
        self.top_files_table = QTableWidget(0, 3)
        self.top_files_table.setHorizontalHeaderLabels(["Размер", "Файл", "Путь"])
        self.top_files_table.setAlternatingRowColors(True)
        self.top_files_table.setSortingEnabled(True)
        self.top_files_table.doubleClicked.connect(lambda idx: self._reveal_from_table(self.top_files_table, idx.row(), col_path=2))
        tabs.addTab(self.top_files_table, "Топ-100 файлов")
        self.top_dirs_table = QTableWidget(0, 2)
        self.top_dirs_table.setHorizontalHeaderLabels(["Размер", "Папка"])
        self.top_dirs_table.setAlternatingRowColors(True)
        self.top_dirs_table.setSortingEnabled(True)
        self.top_dirs_table.doubleClicked.connect(lambda idx: self._reveal_from_table(self.top_dirs_table, idx.row(), col_path=1))
        tabs.addTab(self.top_dirs_table, "Топ-100 папок")
        self.ext_table = QTableWidget(0, 3)
        self.ext_table.setHorizontalHeaderLabels(["Расширение", "Размер", "Файлов"])
        self.ext_table.setAlternatingRowColors(True)
        self.ext_table.setSortingEnabled(True)
        tabs.addTab(self.ext_table, "По типам файлов")
        lay.addWidget(tabs, 1)
        hint = QLabel("Двойной клик — показать в Проводнике. Здесь ничего не удаляется автоматически.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.stack.addWidget(page)

    # ================================================================== настройки (система)
    def _build_settings(self) -> None:
        page = QWidget()
        page.setObjectName("page")
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 16, 18, 12)
        t = QLabel("Настройки системы: спецфайлы и команды")
        t.setStyleSheet("font-size: 20px; font-weight: 700;")
        lay.addWidget(t)
        info = QLabel("hiberfil.sys и pagefile.sys удалять как файлы НЕЛЬЗЯ — только штатными командами.")
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
        self.stack.addWidget(page)

    # ================================================================== данные
    def _refresh_drives(self) -> None:
        drives = list_drives()
        if hasattr(self, "analyzer_combo"):
            cur2 = self.analyzer_combo.currentText()
            self.analyzer_combo.clear()
            self.analyzer_combo.addItems(drives if drives else ["C:\\"])
            if cur2:
                self.analyzer_combo.setCurrentText(cur2)

    def _current_drive(self) -> str:
        return "C:\\"

    def _refresh_dashboard(self) -> None:
        drive = self._current_drive()
        info = get_disk_info(drive)
        if info is None:
            self.stage.set_status("Диск недоступен")
            return
        sel = sum(c.size for c in self.cards.values() if c.checked)
        self.stage.set_status(f"Свободно {format_bytes(info.free)} из {format_bytes(info.total)} • Выбрано {format_bytes(sel)}")
        try:
            self.stage.avatar.setPixmap(avatar_pixmap(drive[0].upper(), "#FF4A1C"))
        except Exception:
            pass
        try:
            hpath = os.path.join(os.path.abspath(drive)[:3], "hiberfil.sys")
            if os.path.exists(hpath):
                sz = os.path.getsize(hpath)
                if sz > 1024 ** 3:
                    self.stage.set_hint(f"Гибернация съедает {format_bytes(sz)} — отключи командой powercfg -h off (Настройки).")
        except Exception:
            pass
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
        for card in self.cards.values():
            card.set_scanning()
        self.progress.setRange(0, len(RULES))
        self.progress.setValue(0)
        self.status_lbl.setText("Сканирование…")
        self.stage.set_playing(True)
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
        for r in typed:
            card = self.cards.get(r.rule_id)
            if card is not None:
                card.set_scan(r.size_bytes, r.file_count, r.paths_found)
        self._update_selected()
        self._apply_card_filter()
        self.stage.set_playing(False)
        # Коллекции сайдбара
        stats: dict[str, tuple[int, int]] = {}
        for g in groups():
            items = [r for r in typed if r.group == g and r.paths_found]
            stats[g] = (len(items), sum(r.size_bytes for r in items))
        self.sidebar.set_collections(stats)
        self._refresh_recs()
        # Фокус на самую прожорливую
        big = [r for r in typed if r.size_bytes > 0]
        if big:
            big.sort(key=lambda r: r.size_bytes, reverse=True)
            self.set_stage_focus(big[0].rule_id)
        self._update_status()
        self.status_lbl.setText("Готов")
        self.progress.setValue(self.progress.maximum())
        self.log(f"📦 Итого: {format_bytes(total)} в {len(typed)} категориях.")
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

    def _update_status(self) -> None:
        info = get_disk_info(self._current_drive())
        sel = sum(c.size for c in self.cards.values() if c.checked)
        free = format_bytes(info.free) if info else "—"
        total = format_bytes(info.total) if info else "—"
        self.stage.set_status(f"Свободно {free} из {total} • Выбрано {format_bytes(sel)}")

    def _update_selected(self) -> None:
        total = sum(c.size for c in self.cards.values() if c.checked)
        n = sum(1 for c in self.cards.values() if c.checked)
        self.selected_lbl.setText(f"Выбрано: {format_bytes(total)} ({n} кат.)")
        if hasattr(self, "clean_trash_btn"):
            if total > 0:
                self.clean_trash_btn.setText(f"🧹 Освободить {format_bytes(total)} → в Корзину")
            else:
                self.clean_trash_btn.setText("🧹 Выбрать кэши выше ↑")
        self._update_status()

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
            box.setText(f"Вы выбрали {len(adv)} категории уровня «Осторожно». Продолжить?")
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

        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            w = item.widget()
            if w is None:
                continue
            grp = w.property("group")
            if grp is not None:
                w.setVisible(any(_matches(r) for r in RULES if r.group == grp))
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
            box.setText(f"Будет БЕЗВОЗВРАТНО удалено ≈ {format_bytes(est)} в {len(sel)} категориях.\n\nВосстановить будет нельзя. Продолжить?")
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
        self.clean_worker = CleanWorker(sel, permanent=permanent, parent=self)
        self.clean_worker.log_line.connect(self.log)
        self.clean_worker.finished_ok.connect(lambda st: self._on_clean_done(st, permanent))
        self.clean_worker.start()

    def _on_clean_done(self, stats: CleanStats, permanent: bool) -> None:
        self.clean_trash_btn.setEnabled(True)
        self.clean_perm_btn.setEnabled(True)
        self.clean_status.setText(f"Готово: ≈ {format_bytes(stats.freed_bytes_estimate)} • занятых пропущено: {stats.skipped_locked}")
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
        self.progress.setRange(0, 0)
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
        self.log(f"📊 {res.root}: топ — {res.top_files[0][0]} ({format_bytes(res.top_files[0][1])})" if res.top_files else "📊 Пусто.")
        self.analyzer_worker = None

    def _fill_table_files(self, res: AnalyzerResult) -> None:
        from PySide6.QtCore import Qt as _Qt

        t = self.top_files_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.top_files))
        for i, (path, size) in enumerate(res.top_files):
            it = QTableWidgetItem(format_bytes(size))
            it.setData(_Qt.UserRole, size)
            t.setItem(i, 0, it)
            name_item = QTableWidgetItem(os.path.basename(path))
            name_item.setToolTip(path)
            t.setItem(i, 1, name_item)
            p_item = QTableWidgetItem(path)
            p_item.setToolTip(path)
            t.setItem(i, 2, p_item)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(True)

    def _fill_table_dirs(self, res: AnalyzerResult) -> None:
        from PySide6.QtCore import Qt as _Qt

        t = self.top_dirs_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.top_dirs))
        for i, (path, size) in enumerate(res.top_dirs):
            it = QTableWidgetItem(format_bytes(size))
            it.setData(_Qt.UserRole, size)
            t.setItem(i, 0, it)
            p = QTableWidgetItem(path)
            p.setToolTip(path)
            t.setItem(i, 1, p)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        t.horizontalHeader().setStretchLastSection(True)

    def _fill_table_ext(self, res: AnalyzerResult) -> None:
        from PySide6.QtCore import Qt as _Qt

        t = self.ext_table
        t.setSortingEnabled(False)
        t.setRowCount(len(res.by_extension))
        for i, (ext, size, count) in enumerate(res.by_extension):
            t.setItem(i, 0, QTableWidgetItem(f".{ext}" if not ext.startswith("(") else ext))
            it = QTableWidgetItem(format_bytes(size))
            it.setData(_Qt.UserRole, size)
            t.setItem(i, 1, it)
            c = QTableWidgetItem(format_count(count))
            c.setData(_Qt.UserRole, count)
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
    from .fonts import load_fonts
    from .theme import build_qss

    load_fonts()
    app.setStyleSheet(build_qss())
    return app  # type: ignore[return-value]
