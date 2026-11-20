"""练习界面：目标文本、实时统计、虚拟键盘与结算。"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .. import content as C
from .. import engine as E
from .. import theme as T
from .. import widgets as W
from .base import BaseScreen

HINT_EN = "直接敲键盘开始，打错可以退格。Tab 重开 · Esc 返回"
HINT_CN = "在下方输入框输入加亮的一行，打完整行自动换行。F5 重开 · Esc 返回"


# ---------------------------------------------------------------- 文本面板

class TextSurface(tk.Frame):
    """目标文本显示：逐字着色 + 当前字符光标。"""

    def __init__(self, master, size: int = 26, cn: bool = False,
                 caret_style: str = "bar", caret_smooth: bool = True,
                 font_family: str = ""):
        super().__init__(master, bg=T.CARD)
        self._caret_style = caret_style
        self._font_family = font_family
        self._last_index = 0
        self.text = tk.Text(self, bg=T.CARD, fg=T.TEXT, relief="flat", bd=0,
                            highlightthickness=0, wrap="word", padx=T.px(30),
                            pady=T.px(22), insertwidth=0, cursor="arrow",
                            selectbackground=T.mix(T.CARD, T.ORANGE, 0.3),
                            spacing1=T.px(2), spacing2=T.px(10))
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.bar.set)
        # 滚动条先 pack，否则会被 Text 的请求宽度挤成 0 宽
        self.bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.set_font(size, cn)
        self.text.configure(state="disabled")
        self.caret = W.Caret(self, bg=T.CARD, style=caret_style, smooth=caret_smooth,
                             on_click=lambda: self.text.focus_set())
        self.bind("<Configure>", lambda e: self.set_cursor(self._last_index, animate=False))

    def apply_style(self, caret_style: str | None = None,
                    caret_smooth: bool | None = None,
                    font_family: str | None = None) -> None:
        if caret_style is not None:
            self._caret_style = caret_style
        if caret_smooth is not None:
            self.caret.set_smooth(caret_smooth)
        if font_family is not None:
            self._font_family = font_family
            self.set_font(getattr(self, "_size", 26), getattr(self, "_cn", False))
        self.set_cursor(self._last_index, animate=False)

    def show_bar(self, visible: bool) -> None:
        if visible:
            if not self.bar.winfo_ismapped():
                self.bar.pack(side="right", fill="y", before=self.text)
        elif self.bar.winfo_ismapped():
            self.bar.pack_forget()

    def set_font(self, size: int, cn: bool) -> None:
        self._size = int(size)
        self._cn = bool(cn)
        family = self._font_family or (T.FONT_CN if cn else T.FONT_MONO)
        scaled = max(10, int(round(size * T.get_scale())))
        self.text.configure(font=(family, scaled), spacing2=T.px(8 if not cn else 14))
        self.text.tag_configure("pend", foreground=T.TEXT, background=T.CARD)
        self.text.tag_configure("ok", foreground="#6d779c", background=T.CARD)
        self.text.tag_configure("bad", foreground="#ffd9dd", background="#571a26",
                                underline=True)
        self.text.tag_configure("cur", foreground="#ffe6cc",
                                background=T.mix(T.CARD, T.ORANGE, 0.55))
        self.text.tag_configure("cur_bad", foreground="#ffe3e6",
                                background=T.mix(T.CARD, T.RED, 0.55))
        # 标签优先级：cur_bad > cur > bad > ok > pend
        for tag in ("pend", "ok", "bad", "cur", "cur_bad"):
            self.text.tag_raise(tag)

    # -- 索引 -------------------------------------------------------
    @staticmethod
    def _idx(n: int) -> str:
        return f"1.0+{max(0, int(n))}c"

    # -- 内容 -------------------------------------------------------
    def set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")
        self.text.tag_add("pend", "1.0", "end-1c")
        self.text.mark_set("insert", "1.0")

    def mark(self, index: int, tag: str = "ok") -> None:
        self.text.tag_remove("pend", self._idx(index), self._idx(index + 1))
        self.text.tag_remove("bad", self._idx(index), self._idx(index + 1))
        self.text.tag_remove("ok", self._idx(index), self._idx(index + 1))
        if tag != "pend":
            self.text.tag_add(tag, self._idx(index), self._idx(index + 1))

    def clear_marks(self, start: int, end: int) -> None:
        for tag in ("ok", "bad", "cur_bad", "pend"):
            self.text.tag_remove(tag, self._idx(start), self._idx(end))
        self.text.tag_add("pend", self._idx(start), self._idx(end))

    def set_cursor(self, index: int, bad: bool = False, animate: bool = True) -> None:
        """把自绘光标移到第 index 个字符；越界或结尾时贴到最后一个字符。"""
        self._last_index = max(0, int(index))
        idx = self._idx(self._last_index)
        try:
            self.text.update_idletasks()
            info = self.text.bbox(idx)
            if not info:
                info = self.text.bbox("end-1c")
        except tk.TclError:
            info = None
        if not info:
            self.caret.hide()
            return
        bx, by, bw, bh = info
        x = self.text.winfo_x() + bx - 1
        y = self.text.winfo_y() + by
        self.caret.set_style(self._caret_style, color=T.RED if bad else T.ORANGE)
        self.caret.place_box(x, y, max(bw, 4) + 2, max(bh - 2, 8), animate=animate)

    def flash_bad(self, index: int, ms: int = 130) -> None:
        self.text.tag_add("bad", self._idx(index), self._idx(index + 1))
        current = self.text.get(self._idx(index), self._idx(index + 1))

        def undo():
            try:
                if current.strip():
                    self.text.tag_remove("bad", self._idx(index), self._idx(index + 1))

            except tk.TclError:
                pass

        self.after(ms, undo)

    def see(self, index: int) -> None:
        self.text.see(self._idx(index))

    def follow(self, index: int, margin_lines: int = 2) -> None:
        """让光标可见，并在光标下方留出约 margin_lines 行的余量。"""
        idx = self._idx(index)
        self.text.see(idx)
        self.text.update_idletasks()
        info = self.text.dlineinfo(idx)
        if not info:
            return
        line_h = max(1, int(info[3]))
        bottom = int(info[1]) + line_h
        height = max(1, self.text.winfo_height())
        margin = line_h * max(1, margin_lines)
        overflow = bottom - (height - margin)
        if overflow > 0:
            units = max(1, int(round(overflow / line_h + 0.49)))
            self.text.yview_scroll(units, "units")

    def page(self, direction: int) -> None:
        self.text.yview_scroll(direction, "pages")


# ---------------------------------------------------------------- 统计块

class StatBox(tk.Frame):
    def __init__(self, master, title: str, value: str = "0", unit: str = "",
                 color: str = T.TEXT, big: bool = False):
        super().__init__(master, bg=T.CARD)
        self.title = W.label(self, title, size=8, color=T.MUTED, bg=T.CARD)
        self.title.pack(anchor="w")
        row = tk.Frame(self, bg=T.CARD)
        row.pack(anchor="w", pady=(T.px(1), 0))
        self.value = W.label(row, value, size=22 if big else 17, bold=True, color=color,
                             bg=T.CARD)
        self.value.pack(side="left")
        self.unit = W.label(row, f" {unit}", size=8, color=T.DIM, bg=T.CARD)
        self.unit.pack(side="left", pady=(T.px(6), 0))
        self._color = color

    def set(self, value: str, unit: str | None = None, color: str | None = None) -> None:
        self.value.configure(text=value)
        if unit is not None:
            self.unit.configure(text=f" {unit}")
        if color:
            self.value.configure(fg=color)
            self._color = color


# ---------------------------------------------------------------- 练习页

class PracticeScreen(BaseScreen):
    name = "practice"

    def __init__(self, app, master):
        super().__init__(app, master)
        self.plan: dict | None = None
        self.session = None
        self.mode = "en"
        self.paused = False
        self._finished = False
        self._guard = False
        self._tick_id = None
        self._last_saved = None
        self._line_starts: list[int] = []
        self._build()

    # ------------------------------------------------------------ 构建
    def _build(self) -> None:
        # 顶部工具条
        header = tk.Frame(self, bg=T.BG)
        header.pack(fill="x", padx=T.px(22), pady=(T.px(12), T.px(6)))
        self.btn_back = W.Button(header, "返回", command=self._back, kind="ghost", size="sm",
                                 icon="←", bg=T.BG)
        self.btn_back.pack(side="left")
        self.title_label = W.label(header, "练习", size=15, bold=True, color=T.TEXT, bg=T.BG)
        self.title_label.pack(side="left", padx=T.px(12))
        self.mode_pill = W.Pill(header, "英文", fg=T.ORANGE, bg=T.BG, size=8)
        self.mode_pill.pack(side="left", padx=T.px(2))
        self.line_label = W.label(header, "", size=9, color=T.MUTED, bg=T.BG)
        self.line_label.pack(side="left", padx=T.px(10))

        self.btn_finish = W.Button(header, "结束本局", command=self._finish_click,
                                   kind="ghost", size="sm", bg=T.BG)
        self.btn_finish.pack(side="right")
        self.btn_restart = W.Button(header, "重新开始", command=self.restart, kind="soft",
                                    size="sm", icon="↻", bg=T.BG)
        self.btn_restart.pack(side="right", padx=T.px(8))
        self.btn_pause = W.Button(header, "暂停", command=self.toggle_pause, kind="soft",
                                  size="sm", icon="⏸", bg=T.BG)
        self.btn_pause.pack(side="right", padx=T.px(8))

        # 统计条
        strip_wrap = W.Card(self, bg=T.CARD, border=T.BORDER)
        strip_wrap.pack(fill="x", padx=T.px(22))
        strip = tk.Frame(strip_wrap.inner, bg=T.CARD)
        strip.pack(fill="x", padx=T.px(18), pady=T.px(10))
        self.box_speed = StatBox(strip, "速度", "0", "字/分", T.ORANGE, big=True)
        self.box_speed.pack(side="left", padx=(0, T.px(26)))
        self.box_acc = StatBox(strip, "正确率", "100", "%", T.GREEN)
        self.box_acc.pack(side="left", padx=(0, T.px(26)))
        self.box_time = StatBox(strip, "用时", "00:00", "", T.CYAN)
        self.box_time.pack(side="left", padx=(0, T.px(26)))
        self.box_keys = StatBox(strip, "击键", "0", "次", T.TEXT_SOFT)
        self.box_keys.pack(side="left", padx=(0, T.px(26)))
        self.box_progress = StatBox(strip, "进度", "0", "%", T.GOLD)
        self.box_progress.pack(side="left")

        prog_holder = tk.Frame(strip, bg=T.CARD)
        prog_holder.pack(side="right", fill="x", expand=True, padx=(T.px(24), 0))
        self.progress = W.ProgressBar(prog_holder, height=10, bg=T.CARD)
        self.progress.pack(fill="x", side="top", pady=(T.px(10), T.px(4)))
        self.hint_label = W.label(prog_holder, HINT_EN, size=8, color=T.DIM, bg=T.CARD)
        self.hint_label.pack(anchor="e")

        # 虚拟键盘（先 pack 到底部，否则会被文本卡挤成 0 高）
        self.keyboard_wrap = tk.Frame(self, bg=T.BG)
        self.keyboard = W.VirtualKeyboard(self.keyboard_wrap, height=148)
        self.keyboard.pack(fill="x", padx=T.px(22), pady=(0, T.px(8)))
        self.keyboard_visible = bool(self.app.settings.get("show_keyboard", True))
        if self.keyboard_visible:
            self.keyboard_wrap.pack(side="bottom", fill="x")

        # 文本区
        self.text_wrap = W.Card(self, bg=T.CARD, border=T.BORDER)
        self.text_wrap.pack(fill="both", expand=True, padx=T.px(22), pady=T.px(10))
        text_wrap = self.text_wrap
        settings = self.app.settings
        self.surface = TextSurface(
            text_wrap.inner, size=int(settings.target_font_size),
            caret_style=str(settings.get("caret_style", "bar")),
            caret_smooth=bool(settings.get("caret_smooth", True)),
            font_family=str(settings.get("practice_font") or ""))
        self.surface.pack(fill="both", expand=True, padx=1, pady=1)
        self.surface.text.bind("<KeyPress>", self._on_key)
        self.surface.text.bind("<Button-1>", lambda e: self._focus_input())

        # 中文输入区
        self.cn_panel = tk.Frame(text_wrap.inner, bg=T.PANEL)
        self.cn_entry_var = tk.StringVar()
        self.cn_entry = tk.Entry(self.cn_panel, textvariable=self.cn_entry_var,
                                 bg=T.PANEL_2, fg=T.TEXT, insertbackground=T.ORANGE,
                                 relief="flat", bd=0, font=(T.FONT_CN, 16),
                                 highlightthickness=2, highlightbackground=T.BORDER,
                                 highlightcolor=T.ORANGE, justify="left")
        self.cn_entry.pack(side="left", fill="x", expand=True, padx=(T.px(18), T.px(10)),
                           pady=T.px(12))
        self.cn_entry.configure(insertwidth=0)
        self.caret_cn = W.Caret(self.cn_panel, bg=T.PANEL, style="bar", smooth=True,
                                on_click=lambda: self.cn_entry.focus_set())
        self.cn_entry.bind("<FocusIn>", lambda e: self._place_cn_caret())
        self.cn_entry.bind("<FocusOut>", lambda e: self.caret_cn.hide())
        self.cn_entry_var.trace_add("write", self._on_cn_change)
        self.cn_entry.bind("<Escape>", lambda e: self._back())
        self.cn_entry.bind("<F5>", lambda e: self.restart())
        self.cn_skip = W.Button(self.cn_panel, "跳过本行", command=self._skip_line, kind="ghost",
                                size="sm", bg=T.PANEL)
        self.cn_skip.pack(side="right", padx=T.px(12))
        self.cn_matched = W.label(self.cn_panel, "", size=9, color=T.DIM, bg=T.PANEL)
        self.cn_matched.pack(side="right", padx=T.px(4))

        # 结算浮层
        self.overlay = tk.Frame(self, bg=T.BG)
        self._build_overlay()

    def _build_overlay(self) -> None:
        card = W.Card(self.overlay, bg=T.PANEL, border=T.BORDER)
        self.overlay_card = card
        card.place(relx=0.5, rely=0.5, anchor="center", width=T.px(660))
        body = tk.Frame(card.inner, bg=T.PANEL)
        body.pack(fill="both", expand=True, padx=T.px(34), pady=T.px(28))
        self.ov_kicker = W.label(body, "本局完成", size=9, color=T.MUTED, bg=T.PANEL)
        self.ov_kicker.pack(anchor="w")

        grade_row = tk.Frame(body, bg=T.PANEL)
        grade_row.pack(fill="x", pady=(T.px(4), T.px(10)))
        self.ov_grade_canvas = tk.Canvas(grade_row, width=T.px(96), height=T.px(96),
                                         bg=T.PANEL, highlightthickness=0, bd=0)
        self.ov_grade_canvas.pack(side="left")
        grade_text = tk.Frame(grade_row, bg=T.PANEL)
        grade_text.pack(side="left", padx=T.px(16), fill="y")
        self.ov_grade_label = W.label(grade_text, "", size=13, bold=True, color=T.ORANGE,
                                      bg=T.PANEL)
        self.ov_grade_label.pack(anchor="w", pady=(T.px(10), 0))
        self.ov_compare = W.label(grade_text, "", size=9, color=T.MUTED, bg=T.PANEL)
        self.ov_compare.pack(anchor="w")
        self.ov_best = W.Pill(grade_text, "新纪录", fg=T.GOLD, bg=T.PANEL, size=9)
        self.ov_best.pack(anchor="w", pady=(T.px(6), 0))

        speed_row = tk.Frame(body, bg=T.PANEL)
        speed_row.pack(fill="x", pady=(0, T.px(12)))
        self.ov_speed = W.label(speed_row, "0", size=44, bold=True, color=T.TEXT, bg=T.PANEL)
        self.ov_speed.pack(side="left")
        self.ov_speed_unit = W.label(speed_row, "字/分", size=10, color=T.MUTED, bg=T.PANEL)
        self.ov_speed_unit.pack(side="left", padx=(T.px(8), 0), pady=(T.px(20), 0))

        stats = tk.Frame(body, bg=T.PANEL)
        stats.pack(fill="x")
        self.ov_stats = {}
        for idx, (key, title) in enumerate((("acc", "正确率"), ("time", "用时"),
                                            ("chars", "字数"), ("keys", "击键"))):
            stats.grid_columnconfigure(idx, weight=1, uniform="ov")
            box = tk.Frame(stats, bg=T.PANEL_2)
            box.grid(row=0, column=idx, sticky="nsew",
                     padx=(0 if idx == 0 else T.px(5), 0 if idx == 3 else T.px(5)))
            inner = tk.Frame(box, bg=T.PANEL_2)
            inner.pack(fill="x", padx=T.px(12), pady=T.px(9))
            W.label(inner, title, size=8, color=T.MUTED, bg=T.PANEL_2).pack(anchor="w")
            value = W.label(inner, "0", size=15, bold=True, color=T.TEXT, bg=T.PANEL_2)
            value.pack(anchor="w")
            self.ov_stats[key] = value

        btns = tk.Frame(body, bg=T.PANEL)
        btns.pack(fill="x", pady=(T.px(20), 0))
        W.Button(btns, "再来一局", command=self.restart, kind="primary", size="md",
                 icon="↻", bg=T.PANEL).pack(side="left")
        W.Button(btns, "换一课", command=self._back, kind="soft", size="md",
                 bg=T.PANEL).pack(side="left", padx=T.px(8))
        W.Button(btns, "查看统计", command=lambda: self.app.show("stats"), kind="ghost",
                 size="md", bg=T.PANEL).pack(side="left")
        W.Button(btns, "返回首页", command=lambda: self.app.show("home"), kind="ghost",
                 size="md", bg=T.PANEL).pack(side="right")

    # ------------------------------------------------------------ 载入
    def on_show(self) -> None:
        self._start_tick()

    def on_hide(self) -> None:
        self._stop_tick()

    def load_plan(self, plan: dict) -> None:
        self.plan = plan
        self.mode = plan.get("engine", "en")
        self.paused = False
        self._finished = False
        self._guard = False
        self.overlay.place_forget()
        strict = bool(self.app.settings.get("strict_mode", True))
        cn = self.mode == "cn"
        self.surface.set_font(int(self.app.settings.target_font_size), cn)
        self.title_label.configure(text=plan.get("title", "练习"))
        if cn:
            self._set_cn_entry_font(str(self.app.settings.get("practice_font") or ""))
            self.session = E.ChineseSession(plan.get("lines") or [])
            content = "\n".join(self.session.lines)
            self.surface.set_text(content)
            self._line_starts = []
            total = 0
            for line in self.session.lines:
                self._line_starts.append(total)
                total += len(line) + 1
            self._render_cn_line(0, 0, 0)
        else:
            self.session = E.EnglishSession(plan.get("text") or "", strict=strict)
            self.surface.set_text(self.session.text)
            self.surface.set_cursor(0)
            self.keyboard.set_target_char(self.session.text[:1])
        self.mode_pill_text(cn)
        self.line_label.configure(text="")
        self.hint_label.configure(text=HINT_CN if cn else HINT_EN)
        self.progress.set(0.0)
        self._update_stats()
        self._show_keyboard(not cn and self.keyboard_visible)
        if cn:
            self.cn_panel.pack(side="bottom", fill="x", before=self.surface)
            self.cn_entry.configure(highlightbackground=T.BORDER)
            self.surface.show_bar(False)
        else:
            self.cn_panel.pack_forget()
            self.surface.show_bar(True)
        self._focus_input()
        self._start_tick()

    def mode_pill_text(self, cn: bool) -> None:
        # Pill 是画布，改文字直接重建
        parent = self.mode_pill.master
        self.mode_pill.destroy()
        label = "中文" if cn else ("符号" if self.plan and self.plan.get("mode") == "num" else "英文")
        color = T.CYAN if cn else T.ORANGE
        self.mode_pill = W.Pill(parent, label, fg=color, bg=T.BG, size=8)
        self.mode_pill.pack(side="left", padx=T.px(2), before=self.line_label)

    def _focus_input(self) -> None:
        if self.mode == "cn":
            self.cn_entry.focus_set()
        else:
            self.surface.text.focus_set()

    # ------------------------------------------------------------ 键盘输入（英文）
    def _on_key(self, event):
        if self.mode != "en" or not self.session:
            return "break"
        keysym = event.keysym
        if keysym == "Tab":
            self.restart()
            return "break"
        if keysym == "Escape":
            self._back()
            return "break"
        if keysym == "F5":
            self.restart()
            return "break"
        if keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
                      "Caps_Lock", "Super_L", "Super_R", "Menu"):
            return "break"
        if event.state & 0x4:  # Ctrl 组合键放行
            return ""
        if self.paused or self._finished:
            return "break"
        if keysym in ("Return", "KP_Enter"):
            self._handle("\n")
            return "break"
        if keysym == "BackSpace":
            self._handle("\b")
            return "break"
        ch = event.char
        if len(ch) == 1 and ch.isprintable():
            self._handle(ch)
        return "break"

    def _handle(self, ch: str) -> None:
        session = self.session
        if session is None or session.finished:
            return
        self.keyboard.flash(ch)
        pos_before = session.pos
        res = session.handle_key(ch)
        if res.kind == "ok":
            self.surface.mark(pos_before, "ok")
            self.surface.set_cursor(session.pos)
            self.surface.follow(session.pos)
            self.keyboard.set_target_char(session.text[session.pos]
                                          if session.pos < len(session.text) else "")
        elif res.kind == "bad":
            if session.strict:
                self.surface.set_cursor(session.pos, bad=True)
                self.surface.flash_bad(session.pos)
                if self.app.settings.get("sound_enabled", True):
                    self.app.sounds.play("error")
            else:
                self.surface.mark(pos_before, "bad")
                self.surface.set_cursor(session.pos)
                self.surface.follow(session.pos)
        elif res.kind == "back":
            self.surface.mark(session.pos, "pend")
            self.surface.set_cursor(session.pos)
            self.surface.follow(session.pos)
            self.keyboard.set_target_char(session.text[session.pos]
                                          if session.pos < len(session.text) else "")
        if self.app.settings.get("sound_enabled", True) and res.kind == "ok":
            self.app.sounds.play("click")
        self._update_stats()
        if res.finished or session.finished:
            self._finish()

    # ------------------------------------------------------------ 中文输入
    def _set_cn_entry_font(self, family: str = "") -> None:
        face = family or T.FONT_CN
        try:
            self.cn_entry.configure(font=(face, int(round(16 * T.get_scale()))))
        except tk.TclError:
            pass

    def apply_practice_style(self) -> None:
        """设置页改动后立刻同步练习区的字体与光标（不重开本局）。"""
        settings = self.app.settings
        style = str(settings.get("caret_style", "bar"))
        smooth = bool(settings.get("caret_smooth", True))
        family = str(settings.get("practice_font") or "")
        self.surface.apply_style(style, smooth, family)
        self._set_cn_entry_font(family)
        self.caret_cn.set_style(style)
        self.caret_cn.set_smooth(smooth)
        self._place_cn_caret(animate=False)

    def _place_cn_caret(self, animate: bool = True) -> None:
        """把中文输入框的自绘光标放到插入点。

        tkinter 的 Entry.bbox() 在隐藏原生光标（insertwidth=0）后不可靠，
        这里直接用字体度量计算插入点横坐标。
        """
        if self.mode != "cn":
            self.caret_cn.hide()
            return
        try:
            self.cn_entry.update_idletasks()
            index = self.cn_entry.index("insert")
            prefix = self.cn_entry.get()[:index]
            face = tkfont.Font(font=self.cn_entry.cget("font"))
            text_w = face.measure(prefix)
            line_h = max(8, face.metrics("linespace"))
        except (tk.TclError, ValueError):
            self.caret_cn.hide()
            return
        pad = 3 + int(self.cn_entry.winfo_x() and 0)
        x = self.cn_entry.winfo_x() + pad + text_w
        y = self.cn_entry.winfo_y() + max(0, (self.cn_entry.winfo_height() - line_h) // 2)
        self.caret_cn.set_style("bar")
        self.caret_cn.place_box(x, y, 4, line_h, animate=animate)

    def _on_cn_change(self, *_args) -> None:
        if self._guard or self.mode != "cn" or not self.session or self._finished:
            return
        if self.paused:
            return
        text = self.cn_entry_var.get()
        try:
            self.cn_entry.icursor("end")
        except tk.TclError:
            pass
        session = self.session
        line = session.line_text
        res = session.update_input(text)
        if res.line_completed:
            finished_line = res.line - 1 if not res.finished else len(session.lines) - 1
            self._render_cn_line(finished_line, len(session.lines[finished_line]),
                                 len(session.lines[finished_line]), cursor=False)
            self._guard = True
            self.cn_entry_var.set("")
            self._guard = False
            if res.finished:
                self._update_stats()
                self._finish()
                return
            self._render_cn_line(session.line_index, 0, 0)
            self.surface.follow(self._line_starts[session.line_index])
            self.after(16, self._place_cn_caret)
            self.keyboard.set_target_char(line[:1] if line else "")
        else:
            matched = session.matched
            typed = len(text)
            self._render_cn_line(session.line_index, matched, typed)
            self.surface.follow(self._line_starts[session.line_index])
            self.after(16, self._place_cn_caret)
        self.keyboard.set_target_char(self._next_cn_char())
        if self.app.settings.get("sound_enabled", True) and res.line_completed:
            self.app.sounds.play("click")
        self._update_stats()

    def _next_cn_char(self) -> str:
        if not self.session or self.mode != "cn":
            return ""
        line = self.session.line_text
        matched = self.session.matched
        return line[matched] if matched < len(line) else ""

    def _render_cn_line(self, line_index: int, matched: int, typed: int,
                        cursor: bool = True) -> None:
        if line_index < 0 or line_index >= len(self.session.lines):
            return
        start = self._line_starts[line_index]
        length = len(self.session.lines[line_index])
        for i in range(length):
            abs_idx = start + i
            if i < matched:
                self.surface.mark(abs_idx, "ok")
            elif i < typed:
                self.surface.mark(abs_idx, "bad")
            else:
                self.surface.mark(abs_idx, "pend")
        if cursor and matched < length:
            self.surface.set_cursor(start + matched)
        else:
            self.surface.text.tag_remove("cur", "1.0", "end")

    def _skip_line(self) -> None:
        if not self.session or self.mode != "cn":
            return
        res = self.session.skip_line()
        old = res.line - 1 if not res.finished else len(self.session.lines) - 1
        if 0 <= old < len(self.session.lines):
            self._render_cn_line(old, len(self.session.lines[old]),
                                 len(self.session.lines[old]), cursor=False)
        self._guard = True
        self.cn_entry_var.set("")
        self._guard = False
        if res.finished:
            self._update_stats()
            self._finish()
            return
        self._render_cn_line(self.session.line_index, 0, 0)
        self.surface.follow(self._line_starts[self.session.line_index])
        self._update_stats()
        self._focus_input()

    # ------------------------------------------------------------ 统计刷新
    def _update_stats(self) -> None:
        s = self.session
        if s is None:
            return
        cpm = s.cpm
        cn = self.mode == "cn"
        value, unit = E.speed_for("cn" if cn else ("num" if self.mode == "num" else "en"), cpm)
        self.box_speed.set(f"{value:.0f}", unit)
        self.box_acc.set(f"{s.accuracy:.0f}", "%",
                         T.GREEN if s.accuracy >= 95 else (T.GOLD if s.accuracy >= 85 else T.RED))
        self.box_time.set(E.format_clock(s.elapsed), "")
        self.box_keys.set(str(s.keystrokes), "次")
        self.box_progress.set(f"{s.progress * 100:.0f}", "%")
        self.progress.set(s.progress)
        if cn:
            self.line_label.configure(
                text=f"第 {min(s.line_index + 1, len(s.lines))} / {len(s.lines)} 行")
            line = s.line_text
            matched = s.matched
            self.cn_matched.configure(text=f"{matched}/{len(line)}" if line else "")
        else:
            total = len(s.text)
            self.line_label.configure(text=f"本局共 {total} 字")

    def _start_tick(self) -> None:
        self._stop_tick()
        self._tick()

    def _stop_tick(self) -> None:
        if self._tick_id:
            try:
                self.after_cancel(self._tick_id)
            except Exception:
                pass
            self._tick_id = None

    def _tick(self) -> None:
        self._tick_id = None
        if not self.winfo_exists():
            return
        if self.session and not self.session.finished and not self.paused:
            self._update_stats()
        self._tick_id = self.after(120, self._tick)

    # ------------------------------------------------------------ 控制
    def toggle_pause(self) -> None:
        if not self.session or self._finished:
            return
        self.paused = not self.paused
        if self.paused:
            self.session.pause()
            self.btn_pause.configure_text("继续")
            self.hint_label.configure(text="已暂停，点击「继续」恢复计时")
        else:
            self.session.resume()
            self.btn_pause.configure_text("暂停")
            self.hint_label.configure(text=HINT_CN if self.mode == "cn" else HINT_EN)
            self._focus_input()

    def _finish_click(self) -> None:
        if not self.session or self._finished:
            return
        if self.session.done_chars <= 0:
            self.app.toast("还没有开始输入，先敲几个字吧")
            return
        self._finish(manual=True)

    def restart(self) -> None:
        if not self.plan:
            self.app.show("home")
            return
        lesson_id = self.plan.get("lesson_id")
        if lesson_id and lesson_id != "custom" and C.get_lesson(lesson_id):
            self.app.start_practice(lesson_id=lesson_id, category=self.plan.get("mode"))
        else:
            self.load_plan(self.plan)

    def _back(self) -> None:
        self._stop_tick()
        self.app.show("home")

    def _show_keyboard(self, show: bool) -> None:
        if show:
            if not self.keyboard_wrap.winfo_ismapped():
                self.keyboard_wrap.pack(side="bottom", fill="x", before=self.text_wrap)
        else:
            self.keyboard_wrap.pack_forget()

    # ------------------------------------------------------------ 结算
    def _finish(self, manual: bool = False) -> None:
        if self._finished or not self.session:
            return
        self._finished = True
        s = self.session
        s.pause()
        s.finished = True
        cn = self.mode == "cn"
        mode = "cn" if cn else (self.plan.get("mode") or "en")
        unit = "字/分" if cn else "WPM"
        cpm = s.cpm
        acc = s.accuracy
        grade, grade_label = E.grade_for("cn" if cn else "en", cpm)
        prev_best = self.app.history.best(mode, "cpm")
        if self.app.settings.get("sound_enabled", True):
            self.app.sounds.play("finish")
        record = {
            "mode": mode,
            "lesson_id": self.plan.get("lesson_id", ""),
            "lesson_title": self.plan.get("title", ""),
            "chars": s.total_chars,
            "correct": s.done_chars,
            "wrong": s.errors,
            "keystrokes": s.keystrokes,
            "seconds": s.elapsed,
            "cpm": cpm,
            "wpm": s.wpm,
            "accuracy": acc,
            "grade": grade,
        }
        self._last_saved = record
        self.app.history.add(**record)
        self.app.settings["last_session"] = {
            "lesson_id": self.plan.get("lesson_id", ""),
            "title": self.plan.get("title", ""),
            "mode": mode,
            "cpm": round(cpm, 1),
        }
        if self.plan.get("lesson_id"):
            saved = self.app.settings.get("last_lesson")
            saved = dict(saved) if isinstance(saved, dict) else {}
            saved[mode] = self.plan["lesson_id"]
            self.app.settings["last_lesson"] = saved
        self.app.settings.save()
        rank = self.app.history.rank(cpm, mode)
        is_best = cpm > prev_best and prev_best > 0
        self._show_result(record, grade, grade_label, rank, is_best, unit)
        self._stop_tick()
        self._update_stats()

    def _show_result(self, record: dict, grade: str, grade_label: str, rank: float,
                     is_best: bool, unit: str) -> None:
        colors = {"S": T.GOLD, "A": T.ORANGE, "B": T.CYAN, "C": T.MUTED, "D": T.RED}
        color = colors.get(grade, T.ORANGE)
        c = self.ov_grade_canvas
        c.delete("all")
        size = T.px(96)
        c.create_oval(T.px(4), T.px(4), size - T.px(4), size - T.px(4),
                      fill=T.mix(T.PANEL, color, 0.16), outline=color, width=T.px(2))
        c.create_text(size / 2, size / 2 + T.px(2), text=grade, fill=color,
                      font=T.font(34, bold=True))
        self.ov_grade_label.configure(text=grade_label, fg=color)
        self.ov_compare.configure(
            text=f"本局速度超过了历史 {rank:.0f}% 的练习")
        if is_best:
            self.ov_best.pack(anchor="w", pady=(T.px(6), 0))
        else:
            self.ov_best.pack_forget()
        speed_value, speed_unit = E.speed_for("cn" if self.mode == "cn"
                                              else ("num" if self.mode == "num" else "en"),
                                              record["cpm"])
        self.ov_speed.configure(text=f"{speed_value:.0f}")
        self.ov_speed_unit.configure(text=speed_unit)
        self.ov_stats["acc"].configure(text=f"{record['accuracy']:.0f}%")
        self.ov_stats["time"].configure(text=E.format_clock(record["seconds"]))
        self.ov_stats["chars"].configure(text=str(record["chars"]))
        self.ov_stats["keys"].configure(text=str(record["keystrokes"]))
        self.overlay.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.overlay.lift()
