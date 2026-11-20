"""自绘控件库：按钮、开关、滑杆、分段选择、进度条、图表、虚拟键盘。"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from . import theme as T


# ---------------------------------------------------------------- 基础工具

def parent_bg(widget) -> str:
    for key in ("bg", "background"):
        try:
            value = widget.cget(key)
            if value:
                return str(value)
        except tk.TclError:
            continue
    return T.BG


def label(master, text: str = "", size: int = 10, color: str = T.TEXT, bold: bool = False,
          bg: str | None = None, mono: bool = False, cn: bool = False,
          family: str | None = None, **kw) -> tk.Label:
    return tk.Label(master, text=text, font=T.font(size, bold, family, mono, cn),
                    fg=color, bg=bg or parent_bg(master), anchor="w", bd=0, **kw)


def divider(master, color: str = T.BORDER, pady: int = 0) -> tk.Frame:
    bg = parent_bg(master)
    holder = tk.Frame(master, bg=bg)
    line = tk.Frame(holder, bg=color, height=1)
    line.pack(fill="x", pady=T.px(pady))
    return holder


def clear(widget: tk.Widget) -> None:
    for child in list(widget.winfo_children()):
        child.destroy()


# ---------------------------------------------------------------- 按钮

_SIZES = {"xs": (24, 9, 20), "sm": (30, 10, 24), "md": (38, 11, 32), "lg": (48, 13, 40)}


class Button(tk.Canvas):
    """圆角按钮，支持 primary / soft / ghost / danger / link 五种样式。"""

    def __init__(self, master, text: str = "", command=None, kind: str = "primary",
                 size: str = "md", width: int | None = None, height: int | None = None,
                 icon: str = "", pad: int | None = None, bg: str | None = None,
                 radius: int | None = None, font_size: int | None = None, **kw):
        self._bg = bg or parent_bg(master)
        h_px, fs, pad_default = _SIZES.get(size, _SIZES["md"])
        self._ch = T.px(height or h_px)
        self._fs = font_size or fs
        self._font = T.font_obj(self._fs, bold=(kind in ("primary", "danger")))
        self._radius = T.px(radius) if radius is not None else self._ch // 2
        self.text = text
        self.icon = icon
        self.kind = kind
        self.command = command
        self.enabled = True
        self._hover = False
        self._pressed = False
        textw = self._font.measure(text) if text else 0
        iconw = T.px(16) if icon else 0
        padpx = T.px(pad if pad is not None else pad_default)
        self._cw = T.px(width) if width else max(T.px(48), textw + iconw + padpx)
        super().__init__(master, width=self._cw, height=self._ch, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    # -- 外观 -------------------------------------------------------
    def _palette(self) -> tuple[str, str, str, str]:
        """(填充, 文字, 悬停填充, 悬停文字)"""
        kind = self.kind
        if kind == "primary":
            return T.ORANGE, "#1a1004", T.ORANGE_HI, "#1a1004"
        if kind == "danger":
            return "#33131f", T.RED, "#451a2a", "#ff7a86"
        if kind == "ghost":
            return self._bg, T.TEXT_SOFT, T.PANEL_2, T.TEXT
        if kind == "link":
            return self._bg, T.ORANGE, self._bg, T.ORANGE_HI
        if kind == "success":
            return "#10362c", T.GREEN, "#15453a", T.GREEN
        return T.PANEL_2, T.TEXT_SOFT, T.CARD_HOVER, T.TEXT  # soft

    def _draw(self) -> None:
        self.delete("all")
        fill, fg, hfill, hfg = self._palette()
        if not self.enabled:
            fill, fg = (T.PANEL if self.kind != "ghost" else self._bg), T.DIM
        elif self._pressed:
            fill = T.darken(hfill, 0.12)
            fg = hfg
        elif self._hover:
            fill, fg = hfill, hfg

        border = ""
        if self.kind in ("ghost", "soft", "danger"):
            border = T.BORDER_HI if self.kind == "ghost" else T.BORDER
            if self._hover and self.enabled:
                border = T.mix(border, T.ORANGE, 0.45)
        # 用 PIL 超采样出圆角图，边缘带抗锯齿（Tk 原生图形是硬边）
        photo = T.rr_photo(self._cw, self._ch, self._radius, fill,
                           outline=border, border=1 if border else 0, bg=self._bg)
        if photo is not None:
            self.create_image(0, 0, anchor="nw", image=photo)
        else:
            T.round_rect(self, 0, 0, self._cw, self._ch, self._radius, fill=fill,
                         outline=border or fill, width=1)

        cx = self._cw / 2
        cy = self._ch / 2
        if self.icon:
            icon_w = T.px(17)
            textw = self._font.measure(self.text) if self.text else 0
            total_w = textw + icon_w if self.text else icon_w
            left = cx - total_w / 2
            self.create_text(left + T.px(1), cy, text=self.icon,
                             font=T.font(self._fs, family=T.FONT_SYM), fill=fg, anchor="w")
            if self.text:
                self.create_text(left + icon_w, cy + 1, text=self.text, font=self._font,
                                 fill=fg, anchor="w")
        elif self.text:
            self.create_text(cx, cy + 1, text=self.text, font=self._font,
                             fill=fg, anchor="c")

    # -- 交互 -------------------------------------------------------
    def _on_enter(self, _event=None):
        self._hover = True
        if self.enabled:
            self.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _event=None):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event=None):
        if not self.enabled:
            return
        self._pressed = True
        self._draw()

    def _on_release(self, event=None):
        if not self.enabled:
            return
        was = self._pressed
        self._pressed = False
        self._draw()
        if was and event is not None:
            inside = 0 <= event.x <= self._cw and 0 <= event.y <= self._ch
            if inside and self.command:
                self.command()

    # -- 状态 -------------------------------------------------------
    def configure_text(self, text: str, width: int | None = None) -> None:
        self.text = text
        if width:
            self._cw = T.px(width)
            self.configure(width=self._cw)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_kind(self, kind: str) -> None:
        self.kind = kind
        self._draw()


class PlayerButton(tk.Canvas):
    """播放器控件：上一首 / 播放 / 暂停 / 下一首，图形自绘。"""

    def __init__(self, master, kind: str, command=None, size: int = 34,
                 primary: bool = False, bg: str | None = None):
        self._bg = bg or parent_bg(master)
        self._size = T.px(size)
        self.kind = kind
        self.primary = primary
        self.command = command
        self._hover = False
        self.enabled = True
        super().__init__(master, width=self._size, height=self._size, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def _set_hover(self, value: bool) -> None:
        self._hover = value
        self._draw()

    def _click(self, _event=None):
        if self.enabled and self.command:
            self.command()

    def _draw(self) -> None:
        self.delete("all")
        s = self._size
        if self.primary:
            fill = T.ORANGE if not self._hover else T.ORANGE_HI
            fg = "#1a1004"
            self.create_oval(0, 0, s, s, fill=fill, outline=fill)
        else:
            fill = self._bg
            fg = T.TEXT if self._hover else T.TEXT_SOFT
            if self._hover:
                self.create_oval(0, 0, s, s, fill=T.PANEL_2, outline=T.PANEL_2)
        if not self.enabled:
            fg = T.DIM
        c = s / 2
        k = s / 34.0
        if self.kind == "play":
            self.create_polygon(c - 5 * k, c - 8 * k, c - 5 * k, c + 8 * k, c + 8 * k, c,
                                fill=fg, outline=fg)
        elif self.kind == "pause":
            bar_w = 3.4 * k
            self.create_rectangle(c - 6 * k, c - 7.5 * k, c - 6 * k + bar_w, c + 7.5 * k,
                                  fill=fg, outline=fg)
            self.create_rectangle(c + 2.2 * k, c - 7.5 * k, c + 2.2 * k + bar_w, c + 7.5 * k,
                                  fill=fg, outline=fg)
        elif self.kind == "next":
            self.create_polygon(c - 8 * k, c - 7 * k, c - 8 * k, c + 7 * k, c + 1.5 * k, c,
                                fill=fg, outline=fg)
            self.create_rectangle(c + 2.5 * k, c - 7 * k, c + 5.5 * k, c + 7 * k, fill=fg, outline=fg)
        elif self.kind == "prev":
            self.create_polygon(c + 8 * k, c - 7 * k, c + 8 * k, c + 7 * k, c - 1.5 * k, c,
                                fill=fg, outline=fg)
            self.create_rectangle(c - 5.5 * k, c - 7 * k, c - 2.5 * k, c + 7 * k, fill=fg, outline=fg)

    def set_kind(self, kind: str) -> None:
        self.kind = kind
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._draw()


# ---------------------------------------------------------------- 开关 / 滑杆 / 分段

class Toggle(tk.Canvas):
    def __init__(self, master, value: bool = False, command=None, bg: str | None = None,
                 width: int = 44, height: int = 24):
        self._bg = bg or parent_bg(master)
        self._cw, self._ch = T.px(width), T.px(height)
        self.value = bool(value)
        self.command = command
        super().__init__(master, width=self._cw, height=self._ch, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        h = self._ch
        track = T.ORANGE if self.value else T.PANEL_2
        outline = T.ORANGE if self.value else T.BORDER_HI
        photo = T.toggle_photo(self._cw, h, self.value, T.ORANGE, T.PANEL_2, outline,
                               self._bg)
        if photo is not None:
            self.create_image(0, 0, anchor="nw", image=photo)
            return
        T.round_rect(self, 1, 1, self._cw - 1, h - 1, (h - 2) / 2, fill=track,
                     outline=outline, width=1)
        r = h / 2 - T.px(3)
        cx = (self._cw - h / 2 - T.px(1)) if self.value else (h / 2 + T.px(1))
        knob = "#fff7ef" if self.value else T.MUTED
        self.create_oval(cx - r, h / 2 - r, cx + r, h / 2 + r, fill=knob, outline=knob)

    def _toggle(self, _event=None):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command(self.value)

    def set(self, value: bool, notify: bool = False) -> None:
        self.value = bool(value)
        self._draw()
        if notify and self.command:
            self.command(self.value)


class Slider(tk.Canvas):
    def __init__(self, master, value: float = 0.5, command=None, width: int = 160,
                 height: int = 22, bg: str | None = None, color: str = T.ORANGE):
        self._bg = bg or parent_bg(master)
        self._cw, self._ch = T.px(width), T.px(height)
        self.value = max(0.0, min(1.0, float(value)))
        self.command = command
        self.color = color
        self._drag = False
        super().__init__(master, width=self._cw, height=self._ch, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _pad(self) -> int:
        return T.px(7)

    def _draw(self) -> None:
        self.delete("all")
        h, w = self._ch, self._cw
        pad = self._pad()
        photo = T.slider_photo(w, h, self.value, self.color, T.PANEL_2, self._bg,
                              pad=pad, knob_r=T.px(7))
        if photo is not None:
            self.create_image(0, 0, anchor="nw", image=photo)
            return
        cy = h / 2
        th = T.px(4)
        top = cy - th / 2
        T.round_rect(self, pad, top, w - pad, cy + th / 2, th / 2,
                     fill=T.PANEL_2, outline=T.PANEL_2)
        x = pad + (w - pad * 2) * self.value
        if x - pad > 1:
            T.round_rect(self, pad, top, x, cy + th / 2, th / 2,
                         fill=self.color, outline=self.color)
        r = T.px(7)
        self.create_oval(x - r, cy - r, x + r, cy + r, fill="#fdf6ef",
                         outline=T.darken(self.color, 0.2), width=1)

    def _set_from_x(self, x: float) -> None:
        pad = self._pad()
        span = max(1, self._cw - pad * 2)
        self.value = max(0.0, min(1.0, (x - pad) / span))
        self._draw()
        if self.command:
            self.command(self.value)

    def _on_press(self, event):
        self._drag = True
        self._set_from_x(event.x)

    def _on_drag(self, event):
        if self._drag:
            self._set_from_x(event.x)

    def _on_release(self, _event):
        self._drag = False

    def set(self, value: float, notify: bool = False) -> None:
        self.value = max(0.0, min(1.0, float(value)))
        self._draw()
        if notify and self.command:
            self.command(self.value)


class Segmented(tk.Canvas):
    """分段选择器（如：短 / 中 / 长）。"""

    def __init__(self, master, options: list[tuple[str, str]], value: str = "",
                 command=None, bg: str | None = None, height: int = 32, size: int = 10):
        self._bg = bg or parent_bg(master)
        self.options = options
        self.value = value or (options[0][0] if options else "")
        self.command = command
        self._fs = size
        self._font = T.font_obj(size, bold=True)
        widths = [self._font.measure(text) + T.px(26) for _, text in options]
        self._cw = sum(widths) + T.px(8)
        self._widths = widths
        self._ch = T.px(height)
        super().__init__(master, width=self._cw, height=self._ch, bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def _rect_of(self, index: int) -> tuple[float, float]:
        pad = T.px(4)
        x = pad
        for i in range(index):
            x += self._widths[i]
        return x, x + self._widths[index]

    def _draw(self) -> None:
        self.delete("all")
        outer = T.rr_photo(self._cw, self._ch, self._ch / 2, T.PANEL,
                           outline=T.BORDER, border=1, bg=self._bg)
        if outer is not None:
            self.create_image(0, 0, anchor="nw", image=outer)
        else:
            T.round_rect(self, 0, 0, self._cw, self._ch, self._ch / 2, fill=T.PANEL,
                         outline=T.BORDER)
        for idx, (value, text) in enumerate(self.options):
            x0, x1 = self._rect_of(idx)
            if value == self.value:
                pill = T.rr_photo(x1 - x0, self._ch - T.px(8), (self._ch - T.px(8)) / 2,
                                  T.ORANGE, bg=T.PANEL)
                if pill is not None:
                    self.create_image(x0, T.px(4), anchor="nw", image=pill)
                else:
                    T.round_rect(self, x0, T.px(4), x1, self._ch - T.px(4),
                                 (self._ch - T.px(8)) / 2, fill=T.ORANGE, outline=T.ORANGE)
                color = "#1a1004"
            else:
                color = T.MUTED
            self.create_text((x0 + x1) / 2, self._ch / 2 + 1, text=text, fill=color,
                             font=self._font, anchor="c")

    def _click(self, event):
        pad = T.px(4)
        x = pad
        for idx, (value, _text) in enumerate(self.options):
            if x <= event.x <= x + self._widths[idx]:
                self.set(value)
                return
            x += self._widths[idx]

    def set(self, value: str, notify: bool = True) -> None:
        if value == self.value:
            return
        self.value = value
        self._draw()
        if notify and self.command:
            self.command(value)


class ProgressBar(tk.Canvas):
    def __init__(self, master, height: int = 8, bg: str | None = None, value: float = 0.0,
                 color: str = T.ORANGE, track: str = T.PANEL_2):
        self._bg = bg or parent_bg(master)
        self._ch = T.px(height)
        self.value = max(0.0, min(1.0, value))
        self.color = color
        self.track = track
        super().__init__(master, height=self._ch, bg=self._bg, highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(1, self.winfo_width())
        h = self._ch
        track = T.rr_photo(w, h, h / 2, self.track, bg=self._bg)
        if track is not None:
            self.create_image(0, 0, anchor="nw", image=track)
        else:
            T.round_rect(self, 0, 0, w, h, h / 2, fill=self.track, outline=self.track)
        filled = max(0.0, min(1.0, self.value)) * w
        if filled > 1:
            fw = max(int(round(max(filled, h))), h)
            bar = T.rr_photo(fw, h, h / 2, self.color, bg=self.track)
            if bar is not None:
                self.create_image(0, 0, anchor="nw", image=bar)
            else:
                T.round_rect(self, 0, 0, fw, h, h / 2, fill=self.color, outline=self.color)

    def set(self, value: float) -> None:
        self.value = max(0.0, min(1.0, float(value)))
        self._draw()


class Pill(tk.Canvas):
    """小标签（等级、键位提示等）。"""

    def __init__(self, master, text: str, fg: str = T.ORANGE, bg: str | None = None,
                 fill: str | None = None, size: int = 9, pad: int = 12, bold: bool = True):
        self._bg = bg or parent_bg(master)
        self._font = T.font_obj(size, bold=bold)
        self.text = text
        self.fg = fg
        self.fill = fill or T.mix(T.CARD, fg, 0.16)
        h = T.px(size * 2.2 + 4)
        w = self._font.measure(text) + T.px(pad)
        self._ch = h
        super().__init__(master, width=w, height=h, bg=self._bg, highlightthickness=0, bd=0)
        photo = T.rr_photo(w, h, h / 2, self.fill, bg=self._bg)
        if photo is not None:
            self.create_image(0, 0, anchor="nw", image=photo)
        else:
            T.round_rect(self, 0, 0, w, h, h / 2, fill=self.fill, outline=self.fill)
        self.create_text(w / 2, h / 2 + 1, text=text, fill=fg, font=self._font, anchor="c")


# ---------------------------------------------------------------- 卡片 / 滚动容器

class Card(tk.Frame):
    """带 1px 边框的面板，内部 self.inner 放内容。"""

    def __init__(self, master, bg: str = T.CARD, border: str = T.BORDER, pad: int = 0, **kw):
        super().__init__(master, bg=border, **kw)
        self.bg_color = bg
        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._pad = pad
        if pad:
            self.body = tk.Frame(self.inner, bg=bg)
            self.body.pack(fill="both", expand=True, padx=T.px(pad), pady=T.px(pad))
        else:
            self.body = self.inner

    def set_border(self, color: str) -> None:
        self.configure(bg=color)


class ScrollFrame(tk.Frame):
    """可滚动区域，内容放进 .body。"""

    def __init__(self, master, bg: str = T.BG, **kw):
        super().__init__(master, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_body(self, _event=None):
        # 窗口项宽度跟随画布：否则缩放重建后内容会按旧/请求宽度溢出被裁掉
        width = self.canvas.winfo_width()
        if width > 1:
            self.canvas.itemconfigure(self._win, width=width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_bar()

    def _on_canvas(self, event=None):
        width = self.canvas.winfo_width()
        if width > 1:
            self.canvas.itemconfigure(self._win, width=width)
        self._sync_bar()

    def _sync_bar(self) -> None:
        """内容没有溢出时把滚动条藏起来，避免右侧一条空蓝带。"""
        try:
            bbox = self.canvas.bbox("all")
            need = bool(bbox) and (bbox[3] - bbox[1]) > self.canvas.winfo_height() + 1
        except Exception:
            need = True
        mapped = bool(self.bar.winfo_ismapped())
        if need and not mapped:
            self.bar.pack(side="right", fill="y")
        elif not need and mapped:
            self.bar.pack_forget()

    def _bind_wheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self, _event=None):
        self.canvas.unbind_all("<MouseWheel>")

    def attach(self, widget=None) -> None:
        """把滚轮事件递归绑定到内容区的所有子控件。"""
        target = widget or self.body

        def walk(item):
            item.bind("<MouseWheel>", self._wheel, add="+")
            for child in item.winfo_children():
                if not isinstance(child, (tk.Text, tk.Listbox)):
                    walk(child)

        walk(target)

    def _wheel(self, event):
        delta = int(-event.delta / 120) if event.delta else 0
        if delta:
            self.canvas.yview_scroll(delta * 2, "units")

    def to_top(self) -> None:
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------- 图表

class LineChart(tk.Canvas):
    """练习速度趋势折线图（含悬停提示）。"""

    def __init__(self, master, height: int = 210, bg: str = T.CARD, color: str = T.ORANGE):
        super().__init__(master, height=T.px(height), bg=bg, highlightthickness=0, bd=0)
        self.bg_color = bg
        self.color = color
        self.points: list[dict] = []
        self._hover_idx: int | None = None
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set_points(self, points: list[dict]) -> None:
        self.points = list(points or [])
        self._draw()

    def _geometry(self):
        w = max(10, self.winfo_width())
        h = max(10, self.winfo_height())
        left, right, top, bottom = T.px(46), T.px(16), T.px(18), T.px(28)
        return w, h, left, top, w - right, h - bottom

    def _values(self) -> list[float]:
        return [float(p.get("value", 0) or 0) for p in self.points]

    def _draw(self) -> None:
        self.delete("all")
        w, h, l, t, r, b = self._geometry()
        values = self._values()
        if not values:
            self.create_text(w / 2, h / 2 - T.px(6), text="还没有练习记录",
                             fill=T.MUTED, font=T.font(11))
            self.create_text(w / 2, h / 2 + T.px(16), text="完成一次练习后，这里会出现速度曲线",
                             fill=T.DIM, font=T.font(9))
            return
        vmax = max(values) * 1.15 or 10
        vmax = max(vmax, 10)
        # 网格
        for i in range(4):
            y = t + (b - t) * i / 3
            self.create_line(l, y, r, y, fill=T.mix(self.bg_color, T.BORDER, 0.85), width=1)
            value = vmax * (3 - i) / 3
            self.create_text(l - T.px(8), y, text=f"{value:.0f}", fill=T.DIM,
                             font=T.font(8), anchor="e")
        n = len(values)
        step = (r - l) / max(1, n - 1) if n > 1 else 0
        xs = [l + step * i if n > 1 else (l + r) / 2 for i in range(n)]
        ys = [b - (v / vmax) * (b - t) for v in values]

        # 面积
        area = [xs[0], b]
        for x, y in zip(xs, ys):
            area += [x, y]
        area += [xs[-1], b]
        self.create_polygon(area, fill=T.mix(self.bg_color, self.color, 0.13), outline="")
        # 折线
        if n > 1:
            self.create_line(*[coord for pair in zip(xs, ys) for coord in pair],
                             fill=self.color, width=T.px(2), smooth=True,
                             splinesteps=16)
        # 数据点
        for i, (x, y) in enumerate(zip(xs, ys)):
            highlight = (self._hover_idx == i) or i == len(values) - 1
            radius = T.px(4.5 if highlight else 3)
            self.create_oval(x - radius, y - radius, x + radius, y + radius,
                             fill=self.color if highlight else self.bg_color,
                             outline=self.color, width=2)
        # X 轴标签（按可用宽度稀疏，跨天时显示"月-日 时:分"，总是保留最后一项）
        per = max(1, int((r - l) // T.px(72)))
        label_every = max(1, math.ceil(n / per))
        last_drawn = -999.0
        for i, point in enumerate(self.points):
            if i % label_every and i != n - 1:
                continue
            if i != n - 1 and xs[i] - last_drawn < T.px(64):
                continue
            if i == n - 1 and xs[i] - last_drawn < T.px(52):
                continue
            text = str(point.get("label", ""))
            tw = T.font_obj(8).measure(text)
            lx = min(max(xs[i], l + tw / 2), r - tw / 2)
            self.create_text(lx, b + T.px(12), text=text, fill=T.DIM, font=T.font(8),
                             anchor="n")
            last_drawn = xs[i]
        # 悬停提示
        if self._hover_idx is not None and 0 <= self._hover_idx < n:
            i = self._hover_idx
            self.create_line(xs[i], t, xs[i], b,
                             fill=T.mix(self.bg_color, self.color, 0.35), dash=(3, 3))
            value = values[i]
            text = f"{value:.0f} {self.points[i].get('unit', '')}".strip()
            tw = T.font_obj(9, bold=True).measure(text) + T.px(16)
            bx = min(max(xs[i] - tw / 2, l), r - tw)
            by = max(t, ys[i] - T.px(30))
            T.round_rect(self, bx, by, bx + tw, by + T.px(22), T.px(6),
                         fill=T.PANEL_2, outline=T.BORDER_HI)
            self.create_text(bx + tw / 2, by + T.px(11), text=text, fill=T.TEXT,
                             font=T.font(9, bold=True), anchor="c")

    def _on_motion(self, event):
        if not self.points:
            return
        w, h, l, t, r, b = self._geometry()
        values = self._values()
        n = len(values)
        if n == 1:
            idx = 0
        else:
            step = (r - l) / (n - 1)
            idx = int(round((event.x - l) / step)) if step else 0
        idx = max(0, min(n - 1, idx))
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._draw()

    def _on_leave(self, _event=None):
        if self._hover_idx is not None:
            self._hover_idx = None
            self._draw()


class BarChart(tk.Canvas):
    """各模式平均速度柱状图。"""

    def __init__(self, master, height: int = 170, bg: str = T.CARD):
        super().__init__(master, height=T.px(height), bg=bg, highlightthickness=0, bd=0)
        self.bg_color = bg
        self.items: list[dict] = []
        self.bind("<Configure>", lambda e: self._draw())

    def set_items(self, items: list[dict]) -> None:
        self.items = list(items or [])
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(10, self.winfo_width())
        h = max(10, self.winfo_height())
        if not self.items:
            self.create_text(w / 2, h / 2, text="暂无数据", fill=T.MUTED, font=T.font(10))
            return
        l, r, t, b = T.px(16), T.px(16), T.px(22), T.px(34)
        n = len(self.items)
        slot = (w - l - r) / max(1, n)
        vmax = max([float(i.get("value", 0) or 0) for i in self.items] + [10]) * 1.2
        # 标签太挤时隔几个画一个（总是保留最后一项，且不和前一个贴在一起）
        per = max(1, int((w - l - r) // T.px(38)))
        label_step = max(1, math.ceil(n / max(1, per)))
        centers = [l + slot * i + slot / 2 for i in range(n)]
        candidates = sorted(set(range(0, n, label_step)) | {n - 1})
        chosen: list[int] = []
        for idx in candidates:
            if chosen and centers[idx] - centers[chosen[-1]] < T.px(44):
                if idx == n - 1:
                    chosen.pop()
                else:
                    continue
            chosen.append(idx)
        for idx, item in enumerate(self.items):
            value = float(item.get("value", 0) or 0)
            color = item.get("color", T.ORANGE)
            bar_w = min(T.px(46), slot * 0.52)
            x0 = l + slot * idx + (slot - bar_w) / 2
            bar_h = max(T.px(3), (value / vmax) * (b - t))
            y0 = b - bar_h
            T.round_rect(self, x0, y0, x0 + bar_w, b, T.px(6),
                         fill=T.mix(self.bg_color, color, 0.85), outline="")
            if value > 0 or n <= 6:
                self.create_text(x0 + bar_w / 2, y0 - T.px(11), text=f"{value:.0f}",
                                 fill=T.TEXT, font=T.font(9, bold=True), anchor="c")
            if idx in chosen:
                self.create_text(x0 + bar_w / 2, b + T.px(16), text=item.get("label", ""),
                                 fill=T.MUTED, font=T.font(9), anchor="c")


# ---------------------------------------------------------------- 虚拟键盘

SHIFT_ROWS = [
    "`1234567890-=",
    "qwertyuiop[]\\",
    "asdfghjkl;'",
    "zxcvbnm,./",
]
SHIFT_MAP = {
    "~": "`", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7",
    "*": "8", "(": "9", ")": "0", "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
    ":": ";", '"': "'", "<": ",", ">": ".", "?": "/",
}
SHIFT_TOP = {
    "`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&",
    "8": "*", "9": "(", "0": ")", "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"', ",": "<", ".": ">", "/": "?",
}
FINGER_OF = {
    "`": "l_pinky", "1": "l_pinky", "q": "l_pinky", "a": "l_pinky", "z": "l_pinky",
    "2": "l_ring", "w": "l_ring", "s": "l_ring", "x": "l_ring",
    "3": "l_middle", "e": "l_middle", "d": "l_middle", "c": "l_middle",
    "4": "l_index", "r": "l_index", "f": "l_index", "v": "l_index",
    "5": "l_index", "t": "l_index", "g": "l_index", "b": "l_index",
    "6": "r_index", "y": "r_index", "h": "r_index", "n": "r_index",
    "7": "r_index", "u": "r_index", "j": "r_index", "m": "r_index",
    "8": "r_middle", "i": "r_middle", "k": "r_middle", ",": "r_middle",
    "9": "r_ring", "o": "r_ring", "l": "r_ring", ".": "r_ring",
    "0": "r_pinky", "p": "r_pinky", ";": "r_pinky", "/": "r_pinky",
    "-": "r_pinky", "=": "r_pinky", "[": "r_pinky", "]": "r_pinky",
    "'": "r_pinky", "\\": "r_pinky",
}


def key_for_char(ch: str) -> tuple[str, bool]:
    """返回 (物理键位字符, 是否需要 Shift)。"""
    if not ch:
        return "", False
    if ch == " ":
        return " ", False
    if ch in "\n\r\t":
        return " ", False
    if ch.isalpha():
        return ch.lower(), ch.isupper()
    if ch in SHIFT_MAP:
        return SHIFT_MAP[ch], True
    return ch.lower(), False


class VirtualKeyboard(tk.Canvas):
    """指法键盘：高亮下一个按键，按下时闪烁，按手指分区着色。"""

    def __init__(self, master, height: int = 150, bg: str = T.CARD):
        super().__init__(master, height=T.px(height), bg=bg, highlightthickness=0, bd=0)
        self.bg_color = bg
        self.target: tuple[str, bool] = ("", False)
        self.flash_key: str | None = None
        self._after_id: str | None = None
        self.bind("<Configure>", lambda e: self._draw())

    def set_target_char(self, ch: str) -> None:
        target = key_for_char(ch)
        if target != self.target:
            self.target = target
            self._draw()

    def flash(self, ch: str) -> None:
        key, _shift = key_for_char(ch)
        if not key:
            return
        self.flash_key = key
        self._draw()
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(90, self._clear_flash)

    def _clear_flash(self) -> None:
        self.flash_key = None
        self._after_id = None
        self._draw()

    # -- 布局 -------------------------------------------------------
    def _layout(self):
        w = max(20, self.winfo_width())
        h = max(20, self.winfo_height())
        gap = T.px(4)
        rows = SHIFT_ROWS
        max_len = max(len(r) for r in rows)
        key_w = (w - gap * (max_len - 1)) / max_len
        key_h = (h - gap * 4.4) / 5.2
        return w, h, gap, rows, key_w, key_h

    def _draw(self) -> None:
        self.delete("all")
        w, h, gap, rows, key_w, key_h = self._layout()
        font_main = T.font_obj(10, bold=True)
        font_sym = T.font_obj(7)
        keys: dict[str, tuple[float, float, float, float]] = {}
        for row_idx, row in enumerate(rows):
            row_w = len(row) * key_w + (len(row) - 1) * gap
            x = (w - row_w) / 2
            # 行首缩进（模拟真实键盘的错位）
            offset = [0, 0.55, 0.95, 1.45][row_idx]
            y = T.px(6) + row_idx * (key_h + gap)
            x += offset * key_w * 0
            for ch in row:
                rect = (x, y, x + key_w, y + key_h)
                self._draw_key(ch, rect, font_main, font_sym)
                keys[ch] = rect
                x += key_w + gap

        # 空格键
        space_y = T.px(6) + 4 * (key_h + gap)
        space_w = min(w * 0.46, key_w * 7)
        space_rect = ((w - space_w) / 2, space_y, (w + space_w) / 2, space_y + key_h * 0.9)
        target_key, target_shift = self.target
        is_target = target_key == " "
        fill = T.ORANGE if is_target else (T.CARD_HOVER if self.flash_key == " " else T.PANEL_2)
        fg = "#1a1004" if is_target else T.DIM
        T.round_rect(self, *space_rect, T.px(6), fill=fill, outline=T.BORDER, width=1)
        self.create_text((space_rect[0] + space_rect[2]) / 2,
                         (space_rect[1] + space_rect[3]) / 2, text="空格",
                         fill=fg, font=font_sym, anchor="c")
        # Shift 提示
        if target_shift:
            self.create_text(w - T.px(46), space_rect[1] + T.px(2), text="⇧ Shift",
                             fill=T.ORANGE, font=T.font(8, bold=True), anchor="e")

    def _draw_key(self, ch: str, rect, font_main, font_sym) -> None:
        x0, y0, x1, y1 = rect
        target_key, target_shift = self.target
        is_target = (target_key == ch)
        flashing = (self.flash_key == ch)
        finger = FINGER_OF.get(ch, "thumb")
        base = T.PANEL_2
        if is_target:
            fill, fg, border = T.ORANGE, "#1a1004", T.ORANGE
        elif flashing:
            fill, fg, border = T.CARD_HOVER, T.TEXT, T.ORANGE
        else:
            tint = T.FINGER_COLORS.get(finger, T.BORDER)
            fill = T.mix(base, tint, 0.14)
            fg = T.TEXT_SOFT
            border = T.BORDER
        T.round_rect(self, x0, y0, x1, y1, T.px(5), fill=fill, outline=border, width=1)
        top = SHIFT_TOP.get(ch)
        if top:
            self.create_text(x0 + T.px(4), y0 + T.px(4), text=top, fill=T.DIM,
                             font=font_sym, anchor="nw")
        self.create_text((x0 + x1) / 2, (y0 + y1) / 2 + (T.px(4) if top else T.px(1)),
                         text=ch.upper() if ch.isalpha() else ch, fill=fg,
                         font=font_main, anchor="c")


class Caret:
    """自绘打字光标：四条细边组成空心框，支持 竖线 / 方框 / 下划线 三种样式。

    用空心框而不是实心色块，字符本身不会被遮住；位置用 place 插值做平滑移动。
    """

    STYLES = (("bar", "竖线"), ("block", "方框"), ("underline", "下划线"))

    def __init__(self, master, bg: str, color: str = T.ORANGE, style: str = "bar",
                 smooth: bool = True, on_click=None):
        self.master = master
        self.bg = bg
        self.color = color
        self.style = style if style in ("bar", "block", "underline") else "bar"
        self.smooth = smooth
        self.on_click = on_click
        self._bars = [tk.Frame(master, bg=color, bd=0, highlightthickness=0,
                               cursor="xterm") for _ in range(4)]
        for bar in self._bars:
            bar.bind("<Button-1>", self._click)
        self._x = self._y = 0.0
        self._w = self._h = 2.0
        self._tx = self._ty = 0.0
        self._tw = self._th = 2.0
        self._job = None
        self._visible = False
        self.hide()

    # -- 位置与外观 -------------------------------------------------
    def _click(self, _event=None):
        if self.on_click:
            self.on_click()

    def set_style(self, style: str, color: str | None = None) -> None:
        self.style = style if style in ("bar", "block", "underline") else "bar"
        if color:
            self.color = color
        for bar in self._bars:
            bar.configure(bg=self.color)
        self._apply()

    def set_smooth(self, smooth: bool) -> None:
        self.smooth = bool(smooth)

    def place_box(self, x: float, y: float, w: float, h: float, animate: bool = True) -> None:
        self._tx, self._ty = float(x), float(y)
        self._tw, self._th = max(2.0, float(w)), max(4.0, float(h))
        if not self._visible:
            self._visible = True
            self._x, self._y, self._w, self._h = self._tx, self._ty, self._tw, self._th
            self._apply()
            return
        if not (animate and self.smooth):
            self._x, self._y, self._w, self._h = self._tx, self._ty, self._tw, self._th
            self._apply()
            return
        if self._job is None:
            self._job = self.master.after(14, self._tick)

    def hide(self) -> None:
        self._visible = False
        if self._job is not None:
            try:
                self.master.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        for bar in self._bars:
            bar.place_forget()

    def _tick(self) -> None:
        self._job = None
        dx, dy = self._tx - self._x, self._ty - self._y
        dw, dh = self._tw - self._w, self._th - self._h
        if abs(dx) < 0.6 and abs(dy) < 0.6 and abs(dw) < 0.6 and abs(dh) < 0.6:
            self._x, self._y, self._w, self._h = self._tx, self._ty, self._tw, self._th
            self._apply()
            return
        k = 0.42
        self._x += dx * k
        self._y += dy * k
        self._w += dw * k
        self._h += dh * k
        self._apply()
        self._job = self.master.after(14, self._tick)

    def _apply(self) -> None:
        if not self._visible:
            return
        x, y, w, h = self._x, self._y, self._w, self._h
        style = self.style
        thick = 3.0 if style != "block" else 2.0
        for bar in self._bars:
            bar.place_forget()
        if style == "bar":
            self._bars[0].place(x=round(x), y=round(y), width=3, height=round(h))
            self._bars[0].lift()
        elif style == "underline":
            self._bars[0].place(x=round(x), y=round(y + h - thick), width=round(w),
                                height=3)
            self._bars[0].lift()
        else:
            t = 2
            self._bars[0].place(x=round(x), y=round(y), width=round(w), height=t)
            self._bars[1].place(x=round(x), y=round(y + h - t), width=round(w), height=t)
            self._bars[2].place(x=round(x), y=round(y), width=t, height=round(h))
            self._bars[3].place(x=round(x + w - t), y=round(y), width=t, height=round(h))
            for bar in self._bars:
                bar.lift()


class Dropdown(tk.Frame):
    """轻量下拉选择：Canvas 自绘按钮 + tk.Menu 弹出列表（用于字体选择）。"""

    def __init__(self, master, options: list[tuple[str, str]], value: str = "",
                 command=None, bg: str = T.BG, width: int = 190, height: int = 32,
                 font_size: int = 9):
        super().__init__(master, bg=bg, width=T.px(width), height=T.px(height))
        self.pack_propagate(False)
        self.options = list(options)
        self.value = value if value is not None else ""
        self.command = command
        self._bg = bg
        self._font_size = font_size
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Button-1>", self._open)
        self._canvas.bind("<Enter>", lambda e: self._draw(hover=True))
        self._canvas.bind("<Leave>", lambda e: self._draw(hover=False))
        self._canvas.bind("<Configure>", lambda e: self._draw())
        self._menu = None
        self._draw()

    def set(self, value: str, notify: bool = True) -> None:
        self.value = value
        self._draw()
        if notify and self.command:
            self.command(value)

    def _label(self) -> str:
        for val, text in self.options:
            if val == self.value:
                return text
        return self.options[0][1] if self.options else ""

    def _draw(self, hover: bool = False) -> None:
        c = self._canvas
        c.delete("all")
        w = max(10, c.winfo_width())
        h = max(10, c.winfo_height())
        fill = T.CARD_HOVER if hover else T.PANEL_2
        photo = T.rr_photo(w, h, T.px(9), fill, outline=T.BORDER_HI, border=1, bg=self._bg)
        if photo is not None:
            c.create_image(0, 0, anchor="nw", image=photo)
        else:
            T.round_rect(c, 0, 0, w, h, T.px(9), fill=fill, outline=T.BORDER_HI, width=1)
        c.create_text(T.px(12), h / 2, text=self._label(), fill=T.TEXT, anchor="w",
                      font=T.font(self._font_size))
        c.create_text(w - T.px(14), h / 2 - T.px(1), text="▾", fill=T.MUTED, anchor="e",
                      font=T.font(10))

    def _open(self, _event=None) -> None:
        self._canvas.update_idletasks()
        menu = tk.Menu(self, tearoff=0, bg=T.PANEL_2, fg=T.TEXT,
                       activebackground=T.ORANGE, activeforeground="#1a1004",
                       bd=0, relief="flat", font=T.font(self._font_size))
        for val, text in self.options:
            menu.add_command(label=text, command=lambda v=val: self.set(v))
        self._menu = menu
        x = self._canvas.winfo_rootx()
        y = self._canvas.winfo_rooty() + self._canvas.winfo_height() + T.px(2)
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
