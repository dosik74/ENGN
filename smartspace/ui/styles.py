"""Glass v2: панели прозрачны — размытый фон с тонировкой рисует _WallpaperCentral.

Шрифты: тело — Inter, заголовки/цифры — Soyuz Grotesk (srift), логотип — Crovas-Demo.
"""
from __future__ import annotations

from .fonts import FONT_STACK, HEAD_STACK, LOGO_STACK, MONO_STACK

ACCENT = "#7DD3FC"
ACCENT_DIM = "#38BDF8"
TEXT = "#F7F9FC"
TEXT_DIM = "#B9C1CC"

GLASS_QSS = f"""
* {{ font-family: {FONT_STACK}; font-weight: 400; }}
QMainWindow {{ color: {TEXT}; }}
QWidget#centralRoot {{ background: transparent; }}
QWidget {{ background: transparent; }}

/* ---------- Sidebar: тёмное стекло, фон рисует родитель ---------- */
QWidget#sidebar {{
    background: transparent;
    border-right: 1px solid rgba(255, 255, 255, 0.09);
}}
QLabel#logo {{
    font-family: {LOGO_STACK}; font-size: 21px; font-weight: 400;
    color: {TEXT}; padding: 4px 8px;
}}
QPushButton#navBtn {{
    background: transparent; color: {TEXT_DIM}; border: none;
    border-left: 3px solid transparent; border-radius: 0;
    padding: 11px 12px 11px 9px; text-align: left; font-size: 14px; font-weight: 500;
}}
QPushButton#navBtn:hover {{ background: rgba(255, 255, 255, 0.06); color: {TEXT}; }}
QPushButton#navBtn:checked {{
    background: rgba(255, 255, 255, 0.09); color: {TEXT};
    border-left: 3px solid {ACCENT_DIM}; font-weight: 600;
}}

/* ---------- Стеклянные карточки: только рамка, заливка — frost снизу ---------- */
QFrame#card {{
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 18px;
}}
QFrame#actionbar {{
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 16px;
}}
QLabel#title {{ font-family: {FONT_STACK}; font-size: 15px; font-weight: 600; color: {TEXT}; }}
QLabel#heroTitle {{ font-family: {HEAD_STACK}; font-size: 25px; font-weight: 700; color: #FFFFFF; }}
QLabel#heroSub {{ font-size: 13px; font-weight: 400; color: {TEXT_DIM}; }}
QLabel#subtitle {{ font-size: 12.5px; font-weight: 400; color: {TEXT_DIM}; }}
QLabel#bigNumber {{ font-family: {FONT_STACK}; font-size: 27px; font-weight: 700; color: #FFFFFF; }}
QLabel#muted {{ color: {TEXT_DIM}; font-size: 12px; font-weight: 400; }}
QLabel#mono {{ font-family: {MONO_STACK}; font-size: 12px; color: {TEXT_DIM}; }}

/* ---------- Главный CTA — белый pill со свечением (тень кодом) ---------- */
QPushButton#primary {{
    background: #F5F7FA; color: #0B0D12; border: none; border-radius: 14px;
    padding: 12px 26px; font-size: 14px; font-weight: 700;
}}
QPushButton#primary:hover {{ background: #FFFFFF; }}
QPushButton#primary:disabled {{ background: rgba(255,255,255,0.18); color: rgba(255,255,255,0.45); }}
QPushButton#ghost {{
    background: rgba(255, 255, 255, 0.05); color: {TEXT};
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 12px; padding: 9px 16px; font-size: 13px; font-weight: 500;
}}
QPushButton#ghost:hover {{ background: rgba(255, 255, 255, 0.11); }}
QPushButton#danger {{
    background: rgba(158, 43, 37, 0.55); color: #FFD9D6; border: 1px solid rgba(255, 120, 110, 0.35);
    border-radius: 12px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#danger:hover {{ background: rgba(158, 43, 37, 0.8); }}

/* ---------- Поиск и вводы ---------- */
QLineEdit#search {{
    background: rgba(255, 255, 255, 0.07); color: {TEXT};
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px; padding: 10px 16px; font-size: 13.5px;
}}
QLineEdit#search:focus {{ border: 1px solid {ACCENT_DIM}; background: rgba(255, 255, 255, 0.10); }}
QComboBox, QSpinBox {{
    background: rgba(255, 255, 255, 0.06); color: {TEXT};
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 12px; padding: 7px 12px; font-size: 13px;
}}
QComboBox QAbstractItemView {{
    background: #14181F; color: {TEXT};
    selection-background-color: {ACCENT_DIM}; selection-color: #0B0D12;
    border: 1px solid rgba(255,255,255,0.12);
}}
QCheckBox {{ color: {TEXT}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 19px; height: 19px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.08);
}}
QCheckBox::indicator:checked {{ background: {ACCENT_DIM}; border: 1px solid {ACCENT_DIM}; }}

/* ---------- Прогресс ---------- */
QProgressBar {{
    background: rgba(255,255,255,0.10); border: none; border-radius: 7px; height: 14px;
    text-align: center; color: {TEXT}; font-size: 11px;
}}
QProgressBar::chunk {{ background: {ACCENT_DIM}; border-radius: 6px; }}

/* ---------- Таблицы: собственный фон для читаемости ---------- */
QTableWidget, QTreeWidget, QListWidget {{
    background: rgba(13, 16, 21, 0.72); color: {TEXT};
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px; font-size: 13px; alternate-background-color: rgba(255,255,255,0.03);
}}
QTableWidget::item, QTreeWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background: rgba(255,255,255,0.05); color: {TEXT_DIM};
    border: none; padding: 7px; font-size: 12px; font-weight: 600;
}}

/* ---------- Лог ---------- */
QPlainTextEdit#log {{
    background: rgba(4, 6, 9, 0.82); color: #DCE1E8;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 12px; font-family: {MONO_STACK}; font-size: 12px;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.18); border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.30); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: rgba(255,255,255,0.18); border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{ background: #161B23; color: {TEXT}; border: 1px solid rgba(255,255,255,0.14); padding: 6px; }}
QTabWidget::pane {{ border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; background: rgba(13,16,21,0.6); }}
QTabBar::tab {{ background: transparent; color: {TEXT_DIM}; padding: 9px 18px; font-size: 13px; font-weight: 500; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; font-weight: 700; }}
"""

# Обратная совместимость со старым именем
FLUENT_QSS = GLASS_QSS
