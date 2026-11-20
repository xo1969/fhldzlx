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


_PHOTO_CACHE: dict[tuple, object] = {}
_PIL_READY = False
try:  # 只为抗锯齿绘制，缺失时所有控件自动退回 Tk 原生图形
    from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk  # type: ignore
    _PIL_READY = True
except Exception:  # pragma: no cover
    Image = ImageChops = ImageDraw = ImageFont = ImageTk = None  # type: ignore


def _finish_photo(key: tuple, img, width: int, height: int, bg: str | None):
    if bg:
        plate = Image.new("RGBA", (width, height), hex_to_rgb(bg) + (255,))
        plate.alpha_composite(img)
        img = plate
    try:
        photo = ImageTk.PhotoImage(img)
    except Exception:
        return None
    _PHOTO_CACHE[key] = photo
    return photo


def rr_photo(width: float, height: float, radius: float, fill: str,
             outline: str = "", border: float = 1, bg: str | None = None,
             supersample: int = 4):
    """用 PIL 超采样渲染抗锯齿圆角矩形，返回可直接放到 Canvas 的 PhotoImage。

    环境里没有 Pillow 时返回 None，调用方退回 Tk 原生 round_rect。
    """
    if not _PIL_READY:
        return None
    w = max(1, int(round(width)))
    h = max(1, int(round(height)))
    border = float(border) if outline else 0.0
    key = ("rr", w, h, round(float(radius), 1), fill, outline, round(border, 1), bg)
    cached = _PHOTO_CACHE.get(key)
    if cached is not None:
        return cached
    s = max(2, int(supersample))
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    side = max(0.0, float(radius)) * s
    draw.rounded_rectangle(
        [0, 0, w * s - 1, h * s - 1], radius=side,
        fill=hex_to_rgb(fill) + (255,),
        outline=(hex_to_rgb(outline) + (255,)) if outline else None,
        width=max(1, int(round(border * s))) if outline else 1,
    )
    img = img.resize((w, h), Image.LANCZOS)
    return _finish_photo(key, img, w, h, bg)


def toggle_photo(width: float, height: float, value: bool, track_on: str,
                 track_off: str, outline: str, bg: str,
                 knob_on: str = "#fff7ef", knob_off: str = MUTED,
                 supersample: int = 4):
    """整块开关（轨道 + 圆钮）一次性抗锯齿渲染，避免圆钮方底。"""
    if not _PIL_READY:
        return None
    w = max(1, int(round(width)))
    h = max(1, int(round(height)))
    key = ("toggle", w, h, bool(value), track_on, track_off, outline, bg,
           knob_on, knob_off)
    cached = _PHOTO_CACHE.get(key)
    if cached is not None:
        return cached
    s = max(2, int(supersample))
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, int(round(1 * s)))
    d.rounded_rectangle(
        [pad, pad, w * s - pad - 1, h * s - pad - 1], radius=(h * s - pad * 2) / 2,
        fill=hex_to_rgb(track_on if value else track_off) + (255,),
        outline=hex_to_rgb(outline) + (255,),
        width=max(1, int(round(0.9 * s))),
    )
    r = (h * s) / 2 - 3 * s
    cx = (w * s - h * s / 2 - s) if value else (h * s / 2 + s)
    cy = h * s / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              fill=hex_to_rgb(knob_on if value else knob_off) + (255,))
    img = img.resize((w, h), Image.LANCZOS)
    return _finish_photo(key, img, w, h, bg)


def slider_photo(width: float, height: float, value: float, color: str,
                 track: str, bg: str, pad: float = 7, knob_r: float = 7,
                 knob_fill: str = "#fdf6ef", supersample: int = 4):
    """整条滑杆（轨道 + 已填充段 + 圆钮）一次性渲染。"""
    if not _PIL_READY:
        return None
    w = max(1, int(round(width)))
    h = max(1, int(round(height)))
    value = max(0.0, min(1.0, float(value)))
    key = ("slider", w, h, round(value, 4), color, track, bg,
           round(pad, 1), round(knob_r, 1), knob_fill)
    cached = _PHOTO_CACHE.get(key)
    if cached is not None:
        return cached
    s = max(2, int(supersample))
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = pad * s
    th = max(2.0, 3.0 * s)
    cy = h * s / 2
    x1 = p + (w * s - p * 2) * value
    d.rounded_rectangle([p, cy - th / 2, w * s - p, cy + th / 2], radius=th / 2,
                        fill=hex_to_rgb(track) + (255,))
    if x1 - p > 1:
        d.rounded_rectangle([p, cy - th / 2, x1, cy + th / 2], radius=th / 2,
                            fill=hex_to_rgb(color) + (255,))
    r = knob_r * s
    d.ellipse([x1 - r, cy - r, x1 + r, cy + r], fill=hex_to_rgb(knob_fill) + (255,),
              outline=hex_to_rgb(darken(color, 0.2)) + (255,),
              width=max(1, int(round(1 * s))))
    img = img.resize((w, h), Image.LANCZOS)
    return _finish_photo(key, img, w, h, bg)


def hero_photo(width: float, height: float, base: str = "#141b33",
               border: str = BORDER, glow: str = ORANGE, warm: str = RED,
               accent: str = GOLD, bg: str = BG, radius: float = 18,
               supersample: int = 2):
    """首页横幅整图：圆角卡片 + 右侧光晕 + 风火轮徽章 + 混天绫，全靠 PIL 抗锯齿。"""
    if not _PIL_READY:
        return None
    w = max(1, int(round(width)))
    h = max(1, int(round(height)))
    key = ("hero", w, h, base, border, glow, warm, accent, bg, round(radius, 1))
    cached = _PHOTO_CACHE.get(key)
    if cached is not None:
        return cached
    s = max(1, int(supersample))
    W, H = w * s, h * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = radius * s
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=r, fill=hex_to_rgb(base) + (255,),
                        outline=hex_to_rgb(border) + (255,), width=max(1, s // 2 + 1))

    inside = Image.new("L", (W, H), 0)
    ImageDraw.Draw(inside).rounded_rectangle([0, 0, W - 1, H - 1], radius=r,
                                             fill=255)

    def paste_glow(cx: float, cy: float, rad: float, color: str, strength: float) -> None:
        grad = Image.radial_gradient("L").resize((max(2, int(rad * 2)),) * 2,
                                                 Image.BILINEAR)
        # radial_gradient: 中心 0、圆边 181、四角 255 —— 反相后把圆边压到 0，避免出现方形光块
        grad = grad.point(lambda v: int(max(0, 255 - v - 74) / 181 * 255 * strength))
        mask = Image.new("L", (W, H), 0)
        mask.paste(grad, (int(cx - rad), int(cy - rad)))
        mask = ImageChops.multiply(mask, inside)
        img.paste(Image.new("RGB", (W, H), hex_to_rgb(color)), (0, 0), mask)

    paste_glow(W - 120 * s, H / 2, 230 * s, glow, 0.42)
    emblem_x, emblem_y = W - 137 * s, H / 2
    paste_glow(emblem_x, emblem_y, 112 * s, glow, 0.34)

    ring_r = 62 * s
    d.ellipse([emblem_x - ring_r, emblem_y - ring_r, emblem_x + ring_r, emblem_y + ring_r],
              fill=mix(base, glow, 0.16), outline=glow, width=max(2, 2 * s))
    arc_r = 84 * s
    for offset, color, lw in ((20, accent, 2), (140, warm, 1), (260, glow, 1)):
        d.arc([emblem_x - arc_r, emblem_y - arc_r, emblem_x + arc_r, emblem_y + arc_r],
              start=offset, end=offset + 70, fill=color, width=max(1, lw * s))
    ribbon = [(emblem_x - 96 * s, emblem_y + 58 * s),
              (emblem_x - 40 * s, emblem_y + 78 * s),
              (emblem_x + 18 * s, emblem_y + 62 * s),
              (emblem_x + 70 * s, emblem_y + 86 * s)]
    d.line(ribbon, fill=mix(base, warm, 0.55), width=max(2, 3 * s), joint="curve")
    d.line([(28 * s, H - 16 * s), (W - 28 * s, H - 16 * s)],
           fill=mix(base, glow, 0.18), width=max(1, s))
    for fx, fy, rad in ((0.55, 0.22, 2), (0.63, 0.78, 1.5), (0.82, 0.16, 2.2),
                        (0.9, 0.72, 1.8), (0.72, 0.55, 1.4), (0.48, 0.68, 1.6)):
        x, y, rr = W * fx, H * fy, rad * s
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=mix(base, accent, 0.55))

    glyph = None
    size = int(46 * s * FACTOR * max(0.8, UI_SCALE))
    for path in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc",
                 "C:/Windows/Fonts/simhei.ttf"):
        try:
            glyph = ImageFont.truetype(path, size)
            break
        except Exception:
            continue
    if glyph is not None:
        d.text((emblem_x, emblem_y + 2 * s), "风", font=glyph, fill=ORANGE_HI,
               anchor="mm")
    img = img.resize((w, h), Image.LANCZOS)
    return _finish_photo(key, img, w, h, bg)


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
