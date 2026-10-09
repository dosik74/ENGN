"""pywebview-мост SmartSpace: готовый движок + HTML-интерфейс.

Используются только проверенные модули (config/scanner/analyzer/trash/system_info/utils),
ничего из PySide. Модель потоков — опрос (polling): фоновые потоки пишут состояние
под замком, JS забирает его раз в 300–700 мс. evaluate_js из потоков не вызывается —
это главный источник гонок и падений в pywebview.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime

from smartspace.analyzer import DiskAnalyzer
from smartspace.config import RULES, groups
from smartspace.scanner import ScannerEngine
from smartspace.system_info import get_disk_info, list_drives, special_files_report
from smartspace.trash import clean_paths, collect_clean_targets
from smartspace.utils import copy_to_clipboard, format_bytes, open_in_explorer


def _rule_meta(rule) -> dict:
    return {
        "id": rule.id,
        "group": rule.group,
        "title": rule.title,
        "risk": rule.risk,
        "what": rule.what,
        "why": rule.why,
        "safety": rule.safety,
        "recommend": rule.recommend,
    }


class WebApi:
    """Методы вызываются из JS как pywebview.api.<name>. Всё JSON-сериализуемо."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._logs: list[dict] = []
        self._log_seq = 0
        self._scan = {"running": False, "done": 0, "total": 0, "current": "",
                      "results": [], "finished": False, "error": ""}
        self._scan_engine: ScannerEngine | None = None
        self._last_paths: dict[str, list[str]] = {}
        self._clean = {"running": False, "status": "", "result": None}
        self._an = {"running": False, "current": "", "result": None, "error": ""}
        self._analyzer: DiskAnalyzer | None = None
        self._stamp("SmartSpace web готов. Нажми play — найдём мусор.")

    # ------------------------------------------------------------- лог
    def _stamp(self, text: str) -> None:
        with self._lock:
            self._log_seq += 1
            self._logs.append({"id": self._log_seq,
                               "t": datetime.now().strftime("%H:%M:%S"),
                               "text": text})
            if len(self._logs) > 500:
                self._logs = self._logs[-500:]

    def log_poll(self, since: int) -> dict:
        try:
            since = int(since)
        except (TypeError, ValueError):
            since = 0
        with self._lock:
            lines = [l for l in self._logs if l["id"] > since]
            nxt = self._log_seq
        return {"lines": lines, "next": nxt}

    # ------------------------------------------------------------- статика
    def get_rules(self) -> list[dict]:
        return [_rule_meta(r) for r in RULES]

    def get_groups(self) -> list[str]:
        return groups()

    def get_drives(self) -> list[str]:
        try:
            return list_drives()
        except Exception:
            return ["C:\\"]

    def disk_info(self) -> dict:
        try:
            info = get_disk_info("C:\\")
            if info is None:
                return {"ok": False}
            return {"ok": True, "total": info.total, "used": info.used,
                    "free": info.free, "percent": info.percent,
                    "fstype": info.fstype, "device": info.device}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def system_info(self) -> list[dict]:
        out = []
        try:
            for item in special_files_report("C:\\"):
                out.append({"title": item["title"], "path": item["path"],
                            "exists": bool(item["exists"]),
                            "size": int(item["size"]) if isinstance(item["size"], int) else -1,
                            "detail": item["detail"]})
        except Exception as e:
            self._stamp(f"⚠ system_info: {e}")
        return out

    def open_path(self, path: str) -> bool:
        try:
            open_in_explorer(str(path))
            return True
        except Exception:
            return False

    def copy_text(self, text: str) -> bool:
        try:
            if copy_to_clipboard(str(text)):
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------- скан
    def scan_start(self) -> dict:
        with self._lock:
            if self._scan["running"]:
                return {"ok": False, "error": "already running"}
            self._scan = {"running": True, "done": 0, "total": len(RULES),
                          "current": "", "results": [], "finished": False, "error": ""}
        self._scan_engine = ScannerEngine()
        th = threading.Thread(target=self._scan_run, daemon=True)
        th.start()
        self._stamp("🔍 Сканирование запущено…")
        return {"ok": True}

    def _scan_progress(self, done: int, total: int, title: str) -> None:
        with self._lock:
            self._scan["done"] = done
            self._scan["total"] = total
            self._scan["current"] = title

    def _scan_run(self) -> None:
        try:
            assert self._scan_engine is not None
            results = self._scan_engine.scan_all(None, on_progress=self._scan_progress)
            serial = []
            paths: dict[str, list[str]] = {}
            for r in results:
                serial.append({
                    "rule_id": r.rule_id, "title": r.title, "group": r.group,
                    "risk": r.risk, "size_bytes": int(r.size_bytes),
                    "file_count": int(r.file_count),
                    "paths_found": list(r.paths_found[:10]),
                    "paths_total": len(r.paths_found),
                    "errors": list(r.errors[:3]),
                })
                paths[r.rule_id] = list(r.paths_found)
            total = sum(r.size_bytes for r in results)
            with self._lock:
                self._scan["results"] = serial
                self._scan["done"] = self._scan["total"]
            self._last_paths = paths
            self._stamp(f"📦 Итого: {format_bytes(total)} в {len(results)} категориях.")
        except Exception as e:
            with self._lock:
                self._scan["error"] = str(e)
            self._stamp(f"⚠ Ошибка сканирования: {e}")
        finally:
            with self._lock:
                self._scan["running"] = False
                self._scan["finished"] = True

    def scan_stop(self) -> dict:
        if self._scan_engine is not None:
            self._scan_engine.cancel()
            self._stamp("⏹ Остановка сканирования…")
            return {"ok": True}
        return {"ok": False}

    def scan_state(self) -> dict:
        with self._lock:
            return {"running": self._scan["running"], "done": self._scan["done"],
                    "total": self._scan["total"], "current": self._scan["current"],
                    "results": list(self._scan["results"]),
                    "finished": self._scan["finished"], "error": self._scan["error"]}

    # ------------------------------------------------------------- очистка
    def clean_start(self, rule_ids, permanent: bool = False) -> dict:
        if not isinstance(rule_ids, list) or not rule_ids:
            return {"ok": False, "error": "empty selection"}
        with self._lock:
            if self._clean["running"]:
                return {"ok": False, "error": "already running"}
            if not self._last_paths:
                return {"ok": False, "error": "no scan yet"}
            # Только известные id из последнего скана — защита от инъекции путей
            snapshot = {rid: self._last_paths[rid] for rid in rule_ids if rid in self._last_paths}
            if not snapshot:
                return {"ok": False, "error": "nothing to clean"}
            self._clean = {"running": True, "status": "Очистка…", "result": None}
        mode = "БЕЗВОЗВРАТНО" if permanent else "в Корзину"
        self._stamp(f"🧹 Очистка запущена ({mode}): {len(snapshot)} кат.")
        th = threading.Thread(target=self._clean_run, args=(snapshot, bool(permanent)), daemon=True)
        th.start()
        return {"ok": True}

    def _clean_run(self, snapshot: dict[str, list[str]], permanent: bool) -> None:
        try:
            trashed = perm = skipped = 0
            freed = 0
            errors: list[str] = []
            for rid, dirs in snapshot.items():
                targets = collect_clean_targets([d for d in dirs if os.path.lexists(d)])
                if not targets:
                    continue
                st = clean_paths(targets, permanent=permanent)
                trashed += st.trashed
                perm += st.deleted_permanent
                skipped += st.skipped_locked
                freed += st.freed_bytes_estimate
                errors.extend(st.errors)
            with self._lock:
                self._clean["result"] = {
                    "trashed": trashed, "permanent": perm, "skipped": skipped,
                    "freed": freed, "errors_total": len(errors), "errors": errors[:8],
                }
                self._clean["status"] = "Готово"
            self._stamp(f"🏁 Готово: ≈ {format_bytes(freed)}, занятых пропущено: {skipped}.")
        except Exception as e:
            with self._lock:
                self._clean["result"] = {"error": str(e)}
            self._stamp(f"⚠ Ошибка очистки: {e}")
        finally:
            with self._lock:
                self._clean["running"] = False

    def clean_state(self) -> dict:
        with self._lock:
            return {"running": self._clean["running"], "status": self._clean["status"],
                    "result": self._clean["result"]}

    # ------------------------------------------------------------- анализ диска
    def analyze_start(self, path: str) -> dict:
        root = (path or "C:\\").strip() or "C:\\"
        if not os.path.isdir(root):
            return {"ok": False, "error": f"no such dir: {root}"}
        with self._lock:
            if self._an["running"]:
                return {"ok": False, "error": "already running"}
            self._an = {"running": True, "current": "", "result": None, "error": ""}
        self._analyzer = DiskAnalyzer()
        self._stamp(f"📊 Анализ {root} …")
        th = threading.Thread(target=self._an_run, args=(root,), daemon=True)
        th.start()
        return {"ok": True}

    def _an_run(self, root: str) -> None:
        try:
            assert self._analyzer is not None

            def _cb(n: int, p: str) -> None:
                with self._lock:
                    self._an["current"] = p

            res = self._analyzer.analyze(root, on_progress=_cb)
            with self._lock:
                self._an["result"] = {
                    "root": res.root, "total_size": res.total_size,
                    "total_files": res.total_files, "total_dirs": res.total_dirs,
                    "skipped": res.skipped_errors,
                    "top_files": [{"path": p, "size": s} for p, s in res.top_files],
                    "top_dirs": [{"path": p, "size": s} for p, s in res.top_dirs],
                    "by_extension": [{"ext": e, "size": s, "count": c}
                                     for e, s, c in res.by_extension],
                }
            self._stamp(f"📊 Готово: {format_bytes(res.total_size)} в {res.total_files} файлах.")
        except Exception as e:
            with self._lock:
                self._an["error"] = str(e)
            self._stamp(f"⚠ Ошибка анализа: {e}")
        finally:
            with self._lock:
                self._an["running"] = False

    def analyze_stop(self) -> dict:
        if self._analyzer is not None:
            self._analyzer.cancel()
            return {"ok": True}
        return {"ok": False}

    def analyze_state(self) -> dict:
        with self._lock:
            return {"running": self._an["running"], "current": self._an["current"],
                    "result": self._an["result"], "error": self._an["error"]}
