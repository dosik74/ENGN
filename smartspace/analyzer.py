"""Анализатор диска: топ файлов, топ папок, группировка по расширениям."""
from __future__ import annotations

import heapq
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class AnalyzerResult:
    root: str
    total_size: int = 0
    total_files: int = 0
    total_dirs: int = 0
    top_files: list[tuple[str, int]] = field(default_factory=list)  # (path, size)
    top_dirs: list[tuple[str, int]] = field(default_factory=list)  # (path, size)
    by_extension: list[tuple[str, int, int]] = field(default_factory=list)  # (ext, size, count)
    skipped_errors: int = 0


class DiskAnalyzer:
    """Рекурсивный обход с подсчётом размеров каталогов снизу вверх."""

    def __init__(self) -> None:
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def analyze(self, root: str, on_progress=None, top_n: int = 100) -> AnalyzerResult:
        res = AnalyzerResult(root=root)
        dir_sizes: dict[str, int] = defaultdict(int)
        ext_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # ext -> [size, count]
        # min-heap для топ файлов: (size, path)
        top_heap: list[tuple[int, str]] = []
        scanned_files = 0

        # Стек каталогов для DFS
        try:
            root = os.path.abspath(root)
        except Exception:
            pass

        stack = [root]
        # Чтобы посчитать размеры папок, копим (dir -> прямой размер файлов) и дерево
        parent_map: dict[str, str] = {}
        order: list[str] = []  # порядок обхода для bottom-up агрегации
        direct_size: dict[str, int] = defaultdict(int)

        while stack:
            if self._cancel.is_set():
                break
            current = stack.pop()
            order.append(current)
            try:
                with os.scandir(current) as it:
                    entries = list(it)
            except OSError:
                res.skipped_errors += 1
                continue
            res.total_dirs += 1
            for entry in entries:
                if self._cancel.is_set():
                    break
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        parent_map[entry.path] = current
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            sz = entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            try:
                                sz = os.path.getsize(entry.path)
                            except OSError:
                                res.skipped_errors += 1
                                continue
                        res.total_size += sz
                        res.total_files += 1
                        scanned_files += 1
                        direct_size[current] += sz
                        # топ файлов
                        if len(top_heap) < top_n:
                            heapq.heappush(top_heap, (sz, entry.path))
                        elif sz > top_heap[0][0]:
                            heapq.heapreplace(top_heap, (sz, entry.path))
                        # расширения
                        _, ext = os.path.splitext(entry.name)
                        ext = ext.lower().lstrip(".") or "(без расширения)"
                        if len(ext) > 12:
                            ext = ext[:12]
                        st = ext_stats[ext]
                        st[0] += sz
                        st[1] += 1
                        if on_progress and (scanned_files % 5000 == 0):
                            try:
                                on_progress(scanned_files, entry.path)
                            except Exception:
                                pass
                except OSError:
                    res.skipped_errors += 1
                    continue
            if on_progress and (res.total_dirs % 2000 == 0):
                try:
                    on_progress(scanned_files, current)
                except Exception:
                    pass

        # Агрегация размеров каталогов снизу вверх
        agg: dict[str, int] = dict(direct_size)
        for d in reversed(order):
            parent = parent_map.get(d)
            if parent is not None:
                agg[parent] = agg.get(parent, 0) + agg.get(d, 0)
        # Топ папок: исключить сам корень, взять крупнейшие
        dir_items = [(p, s) for p, s in agg.items() if os.path.normcase(p) != os.path.normcase(root)]
        dir_items.sort(key=lambda x: x[1], reverse=True)
        res.top_dirs = [(p, s) for p, s in dir_items[:top_n]]

        top_sorted = sorted(top_heap, key=lambda x: x[0], reverse=True)
        res.top_files = [(p, s) for s, p in top_sorted]

        ext_items = sorted(((e, v[0], v[1]) for e, v in ext_stats.items()), key=lambda x: x[1], reverse=True)
        res.by_extension = ext_items[:40]
        return res
