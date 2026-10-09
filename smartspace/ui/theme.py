"""Единая тема SmartSpace «Моя волна»: все цвета и размеры — только здесь.

Тёмная сцена музыкального плеера: диагональный градиент #0B0B0B → #5A0F0A → #FF4A1C,
жёлтый акцент #FFE600, гротеск Inter, линейные иконки одной толщины (см. icons.py).
"""
from __future__ import annotations

APP_NAME = "SmartSpace"
APP_VERSION = "2.0"

# ---------------------------------------------------------------- цвета
BG_APP = "#0B0B0B"
BG_SIDEBAR = "#0B0B0B"
TEXT_MAIN = "#FFFFFF"
TEXT_DIM = "#8A8A8A"
YELLOW = "#FFE600"

GRAD_LEFT = "#0B0B0B"
GRAD_MID = "#5A0F0A"
GRAD_RIGHT = "#FF4A1C"

GLASS_PILL = "rgba(0, 0, 0, 0.35)"
GLASS_BORDER = "rgba(255, 255, 255, 0.16)"
CARD_BG = "rgba(255, 255, 255, 0.055)"
CARD_BORDER = "rgba(255, 255, 255, 0.09)"

SAFE_BG = "rgba(46, 160, 67, 0.22)"
SAFE_FG = "#B7F0C0"
MOD_BG = "rgba(200, 150, 20, 0.22)"
MOD_FG = "#FFE9A8"
ADV_BG = "rgba(200, 60, 50, 0.25)"
ADV_FG = "#FFC9C4"

# ---------------------------------------------------------------- шрифты
FONT_UI = '"Inter", "Segoe UI Variable", "Segoe UI", sans-serif'
MONO = '"JetBrains Mono", Consolas, "Cascadia Code", monospace'

# ---------------------------------------------------------------- размеры
SIDEBAR_W = 224
AVATAR = 36
COVER = 64
COVER_RADIUS = 8
TRANSPORT_SIDE = 48
TRANSPORT_MAIN = 64
ROUND_BTN = 40
PILL_RADIUS = 30
HERO_MAX = 72
HERO_MIN = 40
CLOUD_ICON = 56

HOVER_MS = 180
STAGE_MS = 500
ZOOM = 1.05

# ---------------------------------------------------------------- группы → цвет/иконка/палитра
GROUPS: dict[str, dict[str, str]] = {
    "GPU и игры": {"color": "#8B5CF6", "icon": "zap", "palette": "violet"},
    "Разработка": {"color": "#22C55E", "icon": "code", "palette": "green"},
    "Мессенджеры и приложения": {"color": "#2DD4BF", "icon": "message", "palette": "teal"},
    "Windows и обновления": {"color": "#FF4A1C", "icon": "shield", "palette": "ember"},
}

# Палитры сцены: левая/середина/правая точки градиента + цвет свечения
PALETTES: dict[str, dict[str, str]] = {
    "ember": {"left": "#0B0B0B", "mid": "#5A0F0A", "right": "#FF4A1C", "glow": "#FF6A2B"},
    "violet": {"left": "#0B0B0B", "mid": "#2A1065", "right": "#8B5CF6", "glow": "#A78BFA"},
    "green": {"left": "#0B0B0B", "mid": "#0B3B24", "right": "#22C55E", "glow": "#4ADE80"},
    "teal": {"left": "#0B0B0B", "mid": "#073B3A", "right": "#2DD4BF", "glow": "#5EEAD4"},
}


def palette_for_group(group: str) -> str:
    return GROUPS.get(group, {}).get("palette", "ember")


def group_color(group: str) -> str:
    return GROUPS.get(group, {}).get("color", "#FF4A1C")


def group_icon(group: str) -> str:
    return GROUPS.get(group, {}).get("icon", "folder")


# ---------------------------------------------------------------- QSS
def build_qss() -> str:
    return f"""
* {{ font-family: {FONT_UI}; font-weight: 400; }}
QMainWindow {{ background: {BG_APP}; color: {TEXT_MAIN}; }}
QWidget#centralRoot {{ background: {BG_APP}; }}
QWidget#page {{ background: {BG_APP}; }}
QWidget {{ background: transparent; }}

/* Сайдбар */
QWidget#sidebar {{ background: {BG_SIDEBAR}; border-right: 1px solid rgba(255,255,255,0.07); }}
QLabel#logo {{ font-size: 21px; font-weight: 800; color: {YELLOW}; padding: 6px 8px; }}
QLabel#sideCap {{ color: {TEXT_DIM}; font-size: 11px; font-weight: 600; padding: 10px 12px 2px 12px; }}
QLabel#collSub {{ color: {TEXT_DIM}; font-size: 11px; }}
QLabel#collName {{ color: {TEXT_MAIN}; font-size: 12.5px; font-weight: 500; }}

/* Заголовки сцены */
QLabel#sectionTitle {{ font-size: 15px; font-weight: 600; color: {TEXT_MAIN}; }}
QLabel#statusText {{ font-size: 12px; color: {TEXT_DIM}; }}
QLabel#hint {{ font-size: 12px; color: {TEXT_DIM}; }}

/* Стеклянная pill */
QPushButton#pillBtn {{
    background: {GLASS_PILL}; color: {TEXT_MAIN};
    border: 1px solid {GLASS_BORDER}; border-radius: {PILL_RADIUS}px;
    padding: 12px 30px; font-size: 14px; font-weight: 600;
}}
QPushButton#pillBtn:hover {{ background: rgba(255,255,255,0.10); }}

/* Ссылка «Закрыть» */
QPushButton#linkBtn {{
    background: transparent; border: none; color: {TEXT_DIM};
    font-size: 12px; text-decoration: underline;
}}
QPushButton#linkBtn:hover {{ color: {TEXT_MAIN}; }}

/* Карточки списков */
QFrame#card {{
    background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 14px;
}}
QFrame#actionbar {{
    background: rgba(0,0,0,0.45); border: 1px solid {GLASS_BORDER}; border-radius: 16px;
}}
QLabel#title {{ font-size: 15px; font-weight: 600; color: {TEXT_MAIN}; }}
QLabel#subtitle {{ font-size: 12.5px; color: {TEXT_DIM}; }}
QLabel#bigNumber {{ font-size: 27px; font-weight: 700; color: #FFFFFF; }}
QLabel#muted {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#mono {{ font-family: {MONO}; font-size: 12px; color: {TEXT_DIM}; }}

/* Кнопки */
QPushButton#primary {{
    background: {YELLOW}; color: #111111; border: none; border-radius: 12px;
    padding: 11px 24px; font-size: 14px; font-weight: 700;
}}
QPushButton#primary:hover {{ background: #FFF04D; }}
QPushButton#primary:disabled {{ background: rgba(255,255,255,0.14); color: rgba(255,255,255,0.4); }}
QPushButton#ghost {{
    background: rgba(255,255,255,0.06); color: {TEXT_MAIN};
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 12px; padding: 9px 16px; font-size: 13px; font-weight: 500;
}}
QPushButton#ghost:hover {{ background: rgba(255,255,255,0.12); }}
QPushButton#danger {{
    background: rgba(158,43,37,0.55); color: #FFD9D6; border: 1px solid rgba(255,120,110,0.35);
    border-radius: 12px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#danger:hover {{ background: rgba(158,43,37,0.85); }}

/* Ввод */
QLineEdit#search {{
    background: rgba(255,255,255,0.07); color: {TEXT_MAIN};
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 20px; padding: 10px 18px; font-size: 13.5px;
}}
QLineEdit#search:focus {{ border: 1px solid {YELLOW}; }}
QComboBox {{
    background: rgba(255,255,255,0.06); color: {TEXT_MAIN};
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 12px; padding: 7px 12px; font-size: 13px;
}}
QComboBox QAbstractItemView {{
    background: #141414; color: {TEXT_MAIN};
    selection-background-color: {YELLOW}; selection-color: #111111;
}}
QCheckBox {{ color: {TEXT_MAIN}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 19px; height: 19px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.08);
}}
QCheckBox::indicator:checked {{ background: {YELLOW}; border: 1px solid {YELLOW}; }}

/* Прогресс */
QProgressBar {{
    background: rgba(255,255,255,0.10); border: none; border-radius: 7px;
    height: 14px; text-align: center; color: {TEXT_MAIN}; font-size: 11px;
}}
QProgressBar::chunk {{ background: {YELLOW}; border-radius: 6px; }}

/* Таблицы */
QTableWidget, QTreeWidget, QListWidget {{
    background: rgba(255,255,255,0.04); color: {TEXT_MAIN};
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px; font-size: 13px; alternate-background-color: rgba(255,255,255,0.02);
}}
QTableWidget::item, QTreeWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background: rgba(255,255,255,0.05); color: {TEXT_DIM};
    border: none; padding: 7px; font-size: 12px; font-weight: 600;
}}

/* Лог */
QPlainTextEdit#log {{
    background: #050505; color: #DCE1E8;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px; font-family: {MONO}; font-size: 12px;
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

QToolTip {{ background: #161616; color: {TEXT_MAIN}; border: 1px solid rgba(255,255,255,0.14); padding: 6px; }}
QTabWidget::pane {{ border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; background: transparent; }}
QTabBar::tab {{ background: transparent; color: {TEXT_DIM}; padding: 9px 18px; font-size: 13px; }}
QTabBar::tab:selected {{ color: {TEXT_MAIN}; border-bottom: 2px solid {YELLOW}; font-weight: 700; }}
"""
