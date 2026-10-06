"""Безопасное удаление: по умолчанию — в Корзину через send2trash."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field


@dataclass
class CleanStats:
    attempted: int = 0
    trashed: int = 0
    deleted_permanent: int = 0
    skipped_locked: int = 0
    errors: list[str] = field(default_factory=list)
    freed_bytes_estimate: int = 0


def _estimate_size(path: str) -> int:
    try:
        if os.path.isfile(path) or os.path.islink(path):
            return os.path.getsize(path)
        total = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for fn in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fn))
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def _send_one_to_trash(path: str) -> tuple[bool, str]:
    """Вернуть (ok, reason). reason: ok|locked|missing|error:..."""
    if not os.path.lexists(path):
        return False, "missing"
    try:
        from send2trash import send2trash

        send2trash(path)
        return True, "ok"
    except PermissionError:
        return False, "locked"
    except FileNotFoundError:
        return False, "missing"
    except Exception as e:
        return False, f"error: {e}"


def clean_paths(paths: list[str], permanent: bool = False) -> CleanStats:
    """Отправить пути в корзину (или удалить навсегда). Возвращает статистику.

    paths — конкретные файлы/каталоги (уже раскрытые).
    Каталоги чистятся *по содержимому*? Нет: здесь удаляем как есть,
    а решение «чистить содержимое, а не папку» принимает вызывающий код
    через collect_clean_targets().
    """
    stats = CleanStats()
    for p in paths:
        stats.attempted += 1
        est = _estimate_size(p)
        if permanent:
            try:
                if os.path.isfile(p) or os.path.islink(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=False)
                else:
                    continue
                stats.deleted_permanent += 1
                stats.freed_bytes_estimate += est
            except PermissionError:
                stats.skipped_locked += 1
                stats.errors.append(f"Занят другим процессом (пропущен): {p}")
            except FileNotFoundError:
                pass
            except Exception as e:
                stats.errors.append(f"{p}: {e}")
        else:
            ok, reason = _send_one_to_trash(p)
            if ok:
                stats.trashed += 1
                stats.freed_bytes_estimate += est
            elif reason == "locked":
                stats.skipped_locked += 1
                stats.errors.append(f"Занят другим процессом (пропущен): {p}")
            elif reason == "missing":
                pass
            else:
                stats.errors.append(f"{p}: {reason}")
    return stats


def collect_clean_targets(directories: list[str], include_root: bool = False) -> list[str]:
    """Построить список целей для очистки.

    По умолчанию (include_root=False) удаляется *содержимое* кэш-папок,
    а сами папки сохраняются — так приложения корректно пересоздадут кэш.
    Для одиночных файлов (MEMORY.DMP, thumbcache_*.db) возвращается сам файл.
    """
    targets: list[str] = []
    for d in directories:
        try:
            if os.path.isfile(d):
                targets.append(d)
            elif os.path.isdir(d):
                if include_root:
                    targets.append(d)
                else:
                    try:
                        with os.scandir(d) as it:
                            for entry in it:
                                targets.append(entry.path)
                    except OSError as e:
                        # Нет доступа к листингу — пробуем удалить целиком
                        targets.append(d)
        except OSError:
            continue
    # Убрать дубли и несуществующие
    seen: set[str] = set()
    out: list[str] = []
    for t in targets:
        key = os.path.normcase(os.path.abspath(t))
        if key not in seen and os.path.lexists(t):
            seen.add(key)
            out.append(t)
    return out
