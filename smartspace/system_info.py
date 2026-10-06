"""Системная информация: диски, спецфайлы Windows."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

try:
    import psutil
except ImportError:  # graceful fallback без psutil
    psutil = None  # type: ignore[assignment]


@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float
    label: str = ""


def list_drives() -> list[str]:
    """Список корней для анализа: C drive, D drive ..."""
    drives: list[str] = []
    if psutil is not None:
        try:
            for part in psutil.disk_partitions(all=False):
                mp = part.mountpoint
                if os.path.isdir(mp) and mp not in drives:
                    drives.append(mp)
        except Exception:
            pass
    if not drives:
        # Fallback: проверить буквы A..Z
        import string

        for letter in string.ascii_uppercase:
            p = f"{letter}:\\"
            if os.path.isdir(p):
                drives.append(p)
    # C первым
    drives.sort(key=lambda d: (os.path.normcase(d) != os.path.normcase("C:\\"), d))
    return drives


def get_disk_info(path: str) -> DiskInfo | None:
    try:
        if psutil is not None:
            u = psutil.disk_usage(path)
            total, used, free, percent = u.total, u.used, u.free, float(u.percent)
        else:
            du = shutil.disk_usage(path)
            total, used, free = du.total, du.used, du.free
            percent = round(used / total * 100, 1) if total else 0.0
        # device/fstype
        device, fstype = "", ""
        if psutil is not None:
            try:
                for part in psutil.disk_partitions(all=False):
                    if os.path.normcase(part.mountpoint) == os.path.normcase(os.path.abspath(path)[:3]) or part.mountpoint in os.path.abspath(path):
                        device, fstype = part.device, part.fstype
                        break
            except Exception:
                pass
        return DiskInfo(device=device, mountpoint=path, fstype=fstype, total=total, used=used, free=free, percent=percent)
    except Exception:
        return None


def special_files_report(drive: str = "C:\\") -> list[dict]:
    """Отчёт по hiberfil/pagefile/Windows.old и т.п. Каждый элемент: dict(title, path, size, detail, kind)."""
    drive = os.path.abspath(drive)[:3] if len(os.path.abspath(drive)) >= 3 else "C:\\"
    candidates = [
        ("hiberfil.sys — файл гибернации", os.path.join(drive, "hiberfil.sys"),
         "Образ оперативной памяти для режима гибернации (~40% от RAM). Удаляется только командой powercfg -h off."),
        ("pagefile.sys — файл подкачки", os.path.join(drive, "pagefile.sys"),
         "Виртуальная память Windows. Трогать не рекомендуется — риск BSOD и замедления."),
        ("swapfile.sys — своп UWP-приложений", os.path.join(drive, "swapfile.sys"),
         "Файл подкачки для Store-приложений. Не удалять вручную."),
        ("MEMORY.DMP — дамп синего экрана", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "MEMORY.DMP"),
         "Полный дамп памяти после BSOD, часто равен объёму RAM. Можно удалять, если диагностика завершена."),
        ("Windows.old — предыдущая Windows", os.path.join(drive, "Windows.old"),
         "Копия старой системы для отката (15–30 ГБ). Нужна 10 дней после обновления."),
        ("$Windows.~BT — файлы обновления", os.path.join(drive, "$Windows.~BT"),
         "Временные файлы установки обновления Windows."),
        ("$Recycle.Bin — корзина", os.path.join(drive, "$Recycle.Bin"),
         "Удалённые файлы, ожидающие очистки."),
    ]
    out: list[dict] = []
    for title, path, detail in candidates:
        size = 0
        exists = os.path.exists(path)
        if exists:
            try:
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                elif os.path.isdir(path):
                    size = _quick_dir_size(path)
            except OSError:
                size = -1
        out.append({"title": title, "path": path, "exists": exists, "size": size, "detail": detail})
    return out


def _quick_dir_size(root: str, budget_files: int = 20000) -> int:
    total = 0
    n = 0
    stack = [root]
    while stack and n < budget_files:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    if n >= budget_files:
                        break
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            try:
                                total += e.stat(follow_symlinks=False).st_size
                            except OSError:
                                pass
                            n += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total
