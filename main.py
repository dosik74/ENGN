"""Точка входа SmartSpace. Запуск: python main.py"""
from __future__ import annotations

import os
import sys
import traceback

# Чтобы `python main.py` работал из корня без установки пакета
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _missing_deps() -> list[str]:
    missing: list[str] = []
    try:
        import PySide6  # noqa: F401
    except ImportError:
        missing.append("PySide6")
    try:
        import send2trash  # noqa: F401
    except ImportError:
        missing.append("send2trash")
    try:
        import psutil  # noqa: F401
    except ImportError:
        missing.append("psutil")
    return missing


def main() -> int:
    missing = _missing_deps()
    if missing:
        print("SmartSpace: не хватает зависимостей: " + ", ".join(missing))
        print("Установите их командой:")
        print("    pip install -r requirements.txt")
        # Покажем GUI-ошибку, если Qt доступен
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "SmartSpace — нет зависимостей",
                "Не хватает пакетов: " + ", ".join(missing) + "\n\nВыполните:\n    pip install -r requirements.txt",
            )
        except Exception:
            pass
        return 1

    try:
        from smartspace.ui.main_window import MainWindow, create_app

        app = create_app()
        win = MainWindow()
        win.show()
        return int(app.exec())
    except Exception:
        traceback.print_exc()
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "SmartSpace — ошибка запуска", traceback.format_exc()[-3000:])
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
