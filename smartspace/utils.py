"""Утилиты: форматирование, пути, обход ФС."""
from __future__ import annotations

import ctypes
import glob as glob_module
import os
import subprocess
from pathlib import Path


def format_bytes(num: int) -> str:
    """Человекочитаемый размер. 1536 -> '1.5 КБ'."""
    if num is None:
        return "—"
    n = float(num)
    if n < 0:
        n = 0.0
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ"]
    idx = 0
    while n >= 1024.0 and idx < len(units) - 1:
        n /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(n)} {units[idx]}"
    if n >= 100:
        return f"{n:.0f} {units[idx]}"
    if n >= 10:
        return f"{n:.1f} {units[idx]}"
    return f"{n:.2f} {units[idx]}"


def format_count(n: int) -> str:
    if n is None:
        return "—"
    return f"{n:,}".replace(",", " ")


def expand_pattern(pattern: str) -> str:
    """Раскрыть переменные окружения и ~ в шаблоне пути."""
    if not pattern:
        return pattern
    p = os.path.expandvars(os.path.expanduser(pattern.strip().strip('"')))
    return os.path.normpath(p)


def resolve_pattern(pattern: str) -> list[str]:
    """Вернуть список существующих путей по шаблону (поддерживает * и ?).

    Возвращает только существующие файлы/каталоги.
    """
    expanded = expand_pattern(pattern)
    # Быстрый путь без wildcard
    if "*" not in expanded and "?" not in expanded and "[" not in expanded:
        if os.path.exists(expanded):
            return [expanded]
        return []
    try:
        found = glob_module.glob(expanded, recursive=True)
        return [f for f in found if os.path.exists(f)]
    except Exception:
        return []


def resolve_many(patterns: list[str]) -> list[str]:
    """Раскрыть список шаблонов в плоский список существующих путей без дублей."""
    seen: set[str] = set()
    out: list[str] = []
    for pat in patterns:
        for p in resolve_pattern(pat):
            key = os.path.normcase(os.path.abspath(p))
            if key not in seen:
                seen.add(key)
                out.append(p)
    return out


def is_reparse_point(path: str) -> bool:
    """True если это junction/symlink (чтобы не уходить в бесконечную рекурсию)."""
    try:
        return os.path.islink(path) or (os.path.isdir(path) and bool(os.lstat(path).st_file_attributes & 0x400) if os.name == "nt" else False)
    except Exception:
        return False


def iter_files_fast(root: str):
    """Итератор (dirpath, filename, fullpath) с подавлением ошибок доступа."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            yield current, entry.name, entry.path
                    except OSError:
                        continue
        except OSError:
            continue


def dir_size_fast(root: str, on_error=None) -> tuple[int, int]:
    """Быстро посчитать (размер_байт, кол-во_файлов) каталога. Не бросает исключений."""
    total = 0
    count = 0
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            try:
                                total += entry.stat(follow_symlinks=False).st_size
                            except OSError:
                                # Fallback через lstat
                                try:
                                    total += os.path.getsize(entry.path)
                                except OSError as e:
                                    if on_error:
                                        on_error(entry.path, e)
                                    continue
                            count += 1
                    except OSError as e:
                        if on_error:
                            on_error(entry.path, e)
                        continue
        except OSError as e:
            if on_error:
                on_error(current, e)
            continue
    return total, count


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def copy_to_clipboard(text: str) -> bool:
    try:
        import subprocess as _sp

        p = _sp.Popen(["clip"], stdin=_sp.PIPE, text=True)
        p.communicate(text)
        return p.returncode == 0
    except Exception:
        return False


def open_in_explorer(path: str) -> None:
    try:
        p = os.path.abspath(path)
        if os.path.isfile(p):
            subprocess.Popen(["explorer", "/select,", p])
        elif os.path.isdir(p):
            os.startfile(p)  # type: ignore[attr-defined]
        else:
            parent = os.path.dirname(p)
            if os.path.isdir(parent):
                os.startfile(parent)  # type: ignore[attr-defined]
    except Exception:
        pass


def local_app_data() -> str:
    return os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))


def app_data() -> str:
    return os.environ.get("APPDATA", os.path.expanduser(r"~\AppData\Roaming"))


def windows_dir() -> str:
    return os.environ.get("WINDIR", r"C:\Windows")
