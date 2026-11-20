"""视觉主题：配色、字体、缩放与 ttk 样式。

设计：深空夜色 + 火焰橙 / 混天绫红（神话元素），全部控件自绘，避免 Windows 默认灰白控件破坏氛围。
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ---------------------------------------------------------------- 配色
BG = "#090c16"
BG_GLOW = "#111733"
PANEL = "#121830"
PANEL_2 = "#18203c"
CARD = "#151c35"
CARD_HOVER = "#1d2749"
BORDER = "#232c4c"
BORDER_HI = "#3a4677"
TEXT = "#eef2ff"
TEXT_SOFT = "#c2c9e0"
MUTED = "#8b95b8"
DIM = "#59628a"
GHOST = "#2a3358"

RED = "#ff4d5e"
RED_DEEP = "#b3243c"
ORANGE = "#ff8f3f"
ORANGE_HI = "#ffab63"
GOLD = "#ffc94d"
GREEN = "#35d9a1"
GREEN_DEEP = "#12775a"
CYAN = "#3fd0e0"
PURPLE = "#8f7bff"
PINK = "#ff6fae"

PENDING = "#7f89ab"
ERROR_BG = "#4a1622"
ERROR_FG = "#ff8a95"

ACCENT = ORANGE
ACCENT_HI = ORANGE_HI

# 指法配色（虚拟键盘）
FINGER_COLORS = {
    "l_pinky": "#6b4bb8", "l_ring": "#3f6fd8", "l_middle": "#2f9ac2",
    "l_index": "#2f9ac2", "l_index2": "#2fa88e", "thumb": "#5b6488",
    "r_index": "#2fa88e", "r_index2": "#b8862f", "r_middle": "#b8862f",
    "r_ring": "#b8562f", "r_pinky": "#b83f5b",
}

# ---------------------------------------------------------------- 字体

_UI_CANDIDATES = ["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei"]
_CN_CANDIDATES = ["Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "DengXian", "Noto Sans CJK SC"]
_MONO_CANDIDATES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Courier New"]

FONT_UI = "Microsoft YaHei UI"
FONT_CN = "Microsoft YaHei"
FONT_MONO = "Consolas"
FONT_SYM = "Segoe UI Symbol"

FACTOR = 1.0          # 界面缩放系数（按 DPI）
UI_SCALE = 1.0        # 用户可调的界面缩放
ROOT: tk.Misc | None = None
_font_cache: dict[tuple, tkfont.Font] = {}
_ttk_ready = False


def _pick(candidates: list[str], available: set[str]) -> str:
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


def init(root: tk.Misc, scale: float = 1.0) -> None:
    """在创建 Tk 之后调用：探测字体、DPI，并应用用户界面缩放。"""
    global FONT_UI, FONT_CN, FONT_MONO, FONT_SYM, FACTOR, ROOT, UI_SCALE, _ttk_ready
    ROOT = root
    try:
        UI_SCALE = max(0.85, min(1.30, float(scale)))
    except (TypeError, ValueError):
        UI_SCALE = 1.0
    _font_cache.clear()
    _ttk_ready = False
    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()
    FONT_UI = _pick(_UI_CANDIDATES, available)
    FONT_CN = _pick(_CN_CANDIDATES, available)
    FONT_MONO = _pick(_MONO_CANDIDATES, available)
    FONT_SYM = "Segoe UI Symbol" if "Segoe UI Symbol" in available else FONT_UI
    try:
        dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        dpi = 96.0
    FACTOR = max(0.9, min(1.8, dpi / 96.0))


def get_scale() -> float:
    return UI_SCALE


def px(value: float) -> int:
    return max(1, int(round(value * FACTOR * UI_SCALE)))


def font(size: int, bold: bool = False, family: str | None = None,
         mono: bool = False, cn: bool = False) -> tuple:
    fam = family or (FONT_MONO if mono else (FONT_CN if cn else FONT_UI))
    style = "bold" if bold else "normal"
    return (fam, max(7, int(round(size * UI_SCALE))), style)


def font_obj(size: int, bold: bool = False, family: str | None = None,
             mono: bool = False) -> tkfont.Font:
    real = max(7, int(round(size * UI_SCALE)))
    key = (real, bold, family or "", mono)
    if key not in _font_cache:
        fam = family or (FONT_MONO if mono else FONT_UI)
        _font_cache[key] = tkfont.Font(family=fam, size=real,
                                       weight="bold" if bold else "normal")
    return _font_cache[key]


# ---------------------------------------------------------------- 颜色工具

def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(c1: str, c2: str, t: float) -> str:
    """两色线性插值，t=0 返回 c1，t=1 返回 c2。"""
    t = max(0.0, min(1.0, t))
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def lighten(color: str, t: float = 0.15) -> str:
    return mix(color, "#ffffff", t)


def darken(color: str, t: float = 0.15) -> str:
    return mix(color, "#000000", t)


# ---------------------------------------------------------------- 绘制

def round_rect(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float,
               radius: float = 10, **kwargs):
    """用平滑多边形填充 + 手工描边（Tk 的 smooth 多边形描边会断线）。"""
    r = max(0.0, min(radius, abs(x1 - x0) / 2, abs(y1 - y0) / 2))
    pts = [
        x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
        x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
        x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
    ]
    outline = kwargs.pop("outline", "")
    width = kwargs.pop("width", 1)
    item = canvas.create_polygon(pts, smooth=True, splinesteps=16, outline="", **kwargs)
    if outline and r > 0:
        w = max(1.0, float(width))
        s = w / 2.0
        xa, ya, xb, yb = x0 + s, y0 + s, x1 - s, y1 - s
        canvas.create_line(xa + r, ya, xb - r, ya, fill=outline, width=w)
        canvas.create_line(xa + r, yb, xb - r, yb, fill=outline, width=w)
        canvas.create_line(xa, ya + r, xa, yb - r, fill=outline, width=w)
        canvas.create_line(xb, ya + r, xb, yb - r, fill=outline, width=w)
        d = 2 * r
        canvas.create_arc(xa, ya, xa + d, ya + d, start=90, extent=90, style="arc",
                          outline=outline, width=w)
        canvas.create_arc(xb - d, ya, xb, ya + d, start=0, extent=90, style="arc",
                          outline=outline, width=w)
        canvas.create_arc(xb - d, yb - d, xb, yb, start=270, extent=90, style="arc",
                          outline=outline, width=w)
        canvas.create_arc(xa, yb - d, xa + d, yb, start=180, extent=90, style="arc",
                          outline=outline, width=w)
    elif outline and r <= 0:
        canvas.create_rectangle(x0, y0, x1, y1, outline=outline, width=width)
    return item


def vgradient(canvas: tk.Canvas, x0: int, y0: int, x1: int, y1: int,
              colors: list[str], tags: str | None = None) -> None:
    """竖直渐变条带（用于 hero 背景）。"""
    height = max(1, y1 - y0)
    steps = min(height, 160)
    for i in range(steps):
        t = i / max(1, steps - 1)
        pos = t * (len(colors) - 1)
        idx = min(int(pos), len(colors) - 2)
        frac = pos - idx
        color = mix(colors[idx], colors[idx + 1], frac)
        ya = y0 + int(height * i / steps)
        yb = y0 + int(height * (i + 1) / steps) + 1
        canvas.create_rectangle(x0, ya, x1, yb, fill=color, outline=color,
                                tags=tags or ())


def glow_circle(canvas: tk.Canvas, cx: float, cy: float, radius: float,
                color: str, bg: str, steps: int = 14) -> None:
    """用同心圆模拟柔和光晕。"""
    for i in range(steps, 0, -1):
        t = i / steps
        c = mix(bg, color, (1 - t) ** 1.6 * 0.55)
        r = radius * t
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=c, outline=c)


# ---------------------------------------------------------------- ttk 样式

def setup_ttk(root: tk.Misc) -> None:
    global _ttk_ready
    if _ttk_ready:
        return
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=PANEL, foreground=TEXT, font=font(10))
    style.configure("TFrame", background=PANEL)
    style.configure("TLabel", background=PANEL, foreground=TEXT, font=font(10))

    # 滚动条：细长暗色，去掉两端箭头（clam 默认的箭头很丑）
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background=BORDER_HI, troughcolor=PANEL,
                        bordercolor=PANEL, arrowcolor=MUTED, darkcolor=BORDER_HI,
                        lightcolor=BORDER_HI, relief="flat", borderwidth=0,
                        width=px(8), arrowsize=0)
        style.map(f"{orient}.TScrollbar",
                  background=[("active", MUTED), ("pressed", ORANGE)],
                  arrowcolor=[("active", TEXT)])
    style.layout("Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough",
         {"sticky": "ns", "children": [
             ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.layout("Horizontal.TScrollbar", [
        ("Horizontal.Scrollbar.trough",
         {"sticky": "ew", "children": [
             ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])

    # 表格
    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    borderwidth=0, rowheight=px(30), font=font(10))
    style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED,
                    relief="flat", font=font(9, bold=True), padding=(px(6), px(6)))
    style.map("Treeview", background=[("selected", "#2b3663")],
              foreground=[("selected", TEXT)])
    style.map("Treeview.Heading", background=[("active", CARD_HOVER)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # 输入框
    style.configure("Dark.TEntry", fieldbackground=PANEL_2, foreground=TEXT,
                    insertcolor=ORANGE, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, padding=px(6))
    style.map("Dark.TEntry", bordercolor=[("focus", ORANGE)])

    _ttk_ready = True


def refresh_ttk() -> None:
    """主题色变化后重刷（本程序不切主题，保留接口）。"""
    global _ttk_ready
    _ttk_ready = False
    if ROOT is not None:
        setup_ttk(ROOT)
