"""SmartSpace через pywebview: интерфейс — HTML/CSS/JS, логика — Python (webui.bridge)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import webview
except ImportError:
    print("Нужен pywebview:  pip install pywebview")
    raise SystemExit(1)

from webui.bridge import WebApi


def main() -> None:
    api = WebApi()
    ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui", "ui", "index.html")
    if not os.path.isfile(ui):
        print(f"Не найден интерфейс: {ui}")
        raise SystemExit(2)
    webview.create_window(
        "SmartSpace",
        ui,
        width=1200,
        height=760,
        min_size=(1000, 650),
        js_api=api,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
