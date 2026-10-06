"""Движок сканирования кэшей: быстрый, параллельный, с отменой и прогрессом."""
from __future__ import annotations

import concurrent.futures
import os
import threading
from dataclasses import dataclass, field

from .config import RULES, CacheRule
from .utils import dir_size_fast, resolve_many


@dataclass
class RuleScanResult:
    rule_id: str
    title: str
    group: str
    risk: str
    size_bytes: int = 0
    file_count: int = 0
    paths_found: list[str] = field(default_factory=list)
    paths_missing: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return len(self.paths_found) > 0


def scan_single_rule(rule: CacheRule) -> RuleScanResult:
    """Сканировать одно правило синхронно (вызывается из пула потоков)."""
    res = RuleScanResult(rule_id=rule.id, title=rule.title, group=rule.group, risk=rule.risk)
    found = resolve_many(rule.paths)
    res.paths_missing = max(0, len(rule.paths) - len(found))
    # Особый случай: шаблоны с wildcard могут раскрываться во много путей,
    # а paths_missing тогда некорректен — не критично, это лишь статистика.
    total_size = 0
    total_files = 0
    abs_found: list[str] = []
    for p in found:
        try:
            if os.path.isfile(p):
                try:
                    total_size += os.path.getsize(p)
                    total_files += 1
                except OSError as e:
                    res.errors.append(f"{p}: {e}")
                abs_found.append(p)
            elif os.path.isdir(p):
                errs: list[str] = []

                def _on_err(path: str, exc: Exception) -> None:
                    if len(errs) < 5:
                        errs.append(f"{path}: {exc}")

                size, count = dir_size_fast(p, on_error=_on_err)
                total_size += size
                total_files += count
                res.errors.extend(errs)
                abs_found.append(p)
        except OSError as e:
            res.errors.append(f"{p}: {e}")
    res.size_bytes = total_size
    res.file_count = total_files
    res.paths_found = abs_found
    return res


class ScannerEngine:
    """Параллельное сканирование всех правил."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._cancel = threading.Event()
        self.max_workers = max_workers or min(12, (os.cpu_count() or 4) * 2)

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def scan_all(self, rules: list[CacheRule] | None = None, on_progress=None) -> list[RuleScanResult]:
        """Сканировать правила. on_progress(done:int, total:int, title:str)."""
        target = rules if rules is not None else list(RULES)
        total = len(target)
        results: list[RuleScanResult | None] = [None] * total
        done = 0
        if on_progress:
            on_progress(0, total, "Старт сканирования…")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_to_idx = {pool.submit(scan_single_rule, rule): i for i, rule in enumerate(target)}
            for fut in concurrent.futures.as_completed(future_to_idx):
                if self._cancel.is_set():
                    for f in future_to_idx:
                        f.cancel()
                    break
                i = future_to_idx[fut]
                try:
                    results[i] = fut.result()
                except Exception as e:  # не роняем всё сканирование из-за одного правила
                    r = target[i]
                    results[i] = RuleScanResult(
                        rule_id=r.id, title=r.title, group=r.group, risk=r.risk,
                        errors=[f"Внутренняя ошибка: {e}"],
                    )
                done += 1
                if on_progress:
                    try:
                        on_progress(done, total, target[i].title)
                    except Exception:
                        pass
        # Отфильтровать None при отмене
        return [r for r in results if r is not None]
