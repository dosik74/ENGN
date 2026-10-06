"""QThread-воркеры: сканирование, анализ диска, очистка без заморозки UI."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .analyzer import AnalyzerResult, DiskAnalyzer
from .config import RULES
from .scanner import RuleScanResult, ScannerEngine
from .trash import CleanStats, clean_paths, collect_clean_targets


class ScanWorker(QThread):
    progressed = Signal(int, int, str)  # done, total, title
    log_line = Signal(str)
    finished_ok = Signal(list)  # list[RuleScanResult]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.engine = ScannerEngine()
        self._rules = list(RULES)

    def set_rules(self, rules) -> None:
        self._rules = list(rules)

    def stop(self) -> None:
        self.engine.cancel()

    def run(self) -> None:  # noqa: D102
        def _cb(done: int, total: int, title: str) -> None:
            self.progressed.emit(done, total, title)

        self.log_line.emit("🔍 Сканирование запущено…")
        results: list[RuleScanResult] = self.engine.scan_all(self._rules, on_progress=_cb)
        self.log_line.emit(f"✅ Сканирование завершено: {len(results)} категорий.")
        self.finished_ok.emit(results)


class AnalyzerWorker(QThread):
    progressed = Signal(str)  # текущий путь
    log_line = Signal(str)
    finished_ok = Signal(object)  # AnalyzerResult

    def __init__(self, root: str, parent=None) -> None:
        super().__init__(parent)
        self.root = root
        self.analyzer = DiskAnalyzer()

    def stop(self) -> None:
        self.analyzer.cancel()

    def run(self) -> None:  # noqa: D102
        self.log_line.emit(f"📊 Анализ диска {self.root} … это может занять пару минут.")
        res: AnalyzerResult = self.analyzer.analyze(self.root, on_progress=lambda n, p: self.progressed.emit(p))
        self.log_line.emit(
            f"✅ Анализ готов: файлов {res.total_files}, папок {res.total_dirs}."
        )
        self.finished_ok.emit(res)


class CleanWorker(QThread):
    log_line = Signal(str)
    finished_ok = Signal(object)  # CleanStats

    def __init__(self, rule_paths: dict[str, list[str]], permanent: bool = False, parent=None) -> None:
        """rule_paths: {rule_id: [раскрытые пути]}."""
        super().__init__(parent)
        self.rule_paths = rule_paths
        self.permanent = permanent

    def run(self) -> None:  # noqa: D102
        from .utils import format_bytes

        mode = "БЕЗВОЗВРАТНОЕ удаление" if self.permanent else "Перемещение в Корзину"
        self.log_line.emit(f"🧹 Очистка запущена ({mode})…")
        aggregate = CleanStats()
        for rule_id, dirs in self.rule_paths.items():
            targets = collect_clean_targets(dirs, include_root=False)
            if not targets:
                self.log_line.emit(f"— {rule_id}: нечего удалять (пусто).")
                continue
            self.log_line.emit(f"— {rule_id}: целей {len(targets)} …")
            st = clean_paths(targets, permanent=self.permanent)
            aggregate.attempted += st.attempted
            aggregate.trashed += st.trashed
            aggregate.deleted_permanent += st.deleted_permanent
            aggregate.skipped_locked += st.skipped_locked
            aggregate.freed_bytes_estimate += st.freed_bytes_estimate
            aggregate.errors.extend(st.errors)
            self.log_line.emit(
                f"  ✓ {rule_id}: в корзину {st.trashed}, навсегда {st.deleted_permanent}, пропущено занятых {st.skipped_locked}."
            )
        self.log_line.emit(
            f"🏁 Готово. Освобождено ≈ {format_bytes(aggregate.freed_bytes_estimate)}. "
            f"Занятых пропущено: {aggregate.skipped_locked}."
        )
        if aggregate.errors:
            for e in aggregate.errors[:10]:
                self.log_line.emit(f"⚠ {e}")
            if len(aggregate.errors) > 10:
                self.log_line.emit(f"… и ещё {len(aggregate.errors) - 10} предупреждений.")
        self.finished_ok.emit(aggregate)
