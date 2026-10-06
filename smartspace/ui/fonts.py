"""Загрузка шрифтов: сначала папка srift (пользовательские), затем assets-fallback."""
from __future__ import annotations

import os
import sys

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

# Тело — Inter (полная кириллица, все начертания без синтеза).
FONT_STACK = '"Inter", "Segoe UI Variable", "Segoe UI", sans-serif'
# Заголовки/цифры — Soyuz Grotesk пользователя (кириллица, только Bold).
HEAD_STACK = '"Soyuz Grotesk", "Manrope", "Inter", "Segoe UI", sans-serif'
# Логотип — CrovAS (латиница), дальше откат.
LOGO_STACK = '"Crovas-Demo", "Soyuz Grotesk", "Inter", sans-serif'
MONO_STACK = '"JetBrains Mono", Consolas, "Cascadia Code", monospace'

_loaded = False


def _project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    here = os.path.abspath(__file__)  # .../smartspace/ui/fonts.py
    return os.path.dirname(os.path.dirname(os.path.dirname(here)))


def _font_files() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    cands: list[str] = []
    if getattr(sys, "frozen", False):
        cands.append(os.path.join(getattr(sys, "_MEIPASS", ""), "srift"))
    cands.append(os.path.join(_project_root(), "srift"))
    cands.append(FONT_DIR)
    for d in cands:
        if not d or not os.path.isdir(d):
            continue
        for root, _dn, fns in os.walk(d):
            for fn in sorted(fns):
                if fn.lower().endswith((".ttf", ".otf")):
                    full = os.path.realpath(os.path.join(root, fn))
                    if full not in seen:
                        seen.add(full)
                        out.append(full)
    return out


def load_fonts() -> list[str]:
    """Регистрирует все шрифты из srift. Возвращает список семейств."""
    global _loaded
    families: list[str] = []
    if _loaded:
        return families
    _loaded = True
    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        return families
    for path in _font_files():
        try:
            fid = QFontDatabase.addApplicationFont(path)
            if fid != -1:
                families.extend(QFontDatabase.applicationFontFamilies(fid))
        except Exception:
            continue
    return families
