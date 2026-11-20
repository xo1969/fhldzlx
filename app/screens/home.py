"""首页：品牌横幅、数据概览、课程选择。"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox

from .. import content as C
from .. import theme as T
from .. import widgets as W
from .base import BaseScreen

HERO_BG = "#141b33"


class HomeScreen(BaseScreen):
    name = "home"

    def __init__(self, app, master):
        super().__init__(app, master)
        self.category = str(app.settings.get("last_category", "en") or "en")
        if self.category not in C.CATEGORY_NAMES:
            self.category = "en"
        self.scroll = W.ScrollFrame(self, bg=T.BG)
        self.scroll.pack(fill="both", expand=True)
        self.body = self.scroll.body
        self._build_hero()
        self._build_stats()
        self._build_lessons()
        self.scroll.attach()
        self._col_job = None
        self.scroll.canvas.bind("<Configure>", self._on_resize, add="+")

    # ------------------------------------------------------------ 自适应
    def _cols_for_width(self) -> int:
        width = self.scroll.canvas.winfo_width()
        if width <= 1:
            return 4
        return max(2, min(4, int((width + T.px(14)) // T.px(246))))

    def _on_resize(self, _event=None) -> None:
        if self._col_job:
            try:
                self.after_cancel(self._col_job)
            except Exception:
                pass
        self._col_job = self.after(140, self._apply_columns)

    def _apply_columns(self) -> None:
        self._col_job = None
        if self._cols_for_width() != getattr(self, "_cols", 4):
            self._rebuild_lessons()

    # ------------------------------------------------------------ 横幅
    def _build_hero(self) -> None:
        wrap = tk.Frame(self.body, bg=T.BG, height=T.px(246))
        wrap.pack(fill="x", padx=T.px(26), pady=(T.px(18), T.px(14)))
        wrap.pack_propagate(False)
        self.hero_wrap = wrap
        self.hero_canvas = tk.Canvas(wrap, bg=T.BG, highlightthickness=0, bd=0)
        self.hero_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.hero_canvas.bind("<Configure>", lambda e: self._draw_hero_bg())

        content = tk.Frame(wrap, bg=HERO_BG)
        content.place(x=T.px(34), y=T.px(26), relwidth=0.63, height=T.px(194))
        self.hero_content = content

        W.Pill(content, "FIREWHEEL TYPING · 风火轮打字", fg=T.ORANGE, bg=HERO_BG,
               size=9).pack(anchor="w")
        title = W.label(content, "风火轮转，键指生花", size=27, bold=True, color=T.TEXT,
                        bg=HERO_BG)
        title.pack(anchor="w", pady=(T.px(10), 0))
        W.label(content, "中英文打字练习 · 背景音乐 · 详细速度统计", size=11,
                color=T.TEXT_SOFT, bg=HERO_BG).pack(anchor="w", pady=(T.px(6), 0))
        self.hero_last = W.label(content, "", size=9, color=T.MUTED, bg=HERO_BG)
        self.hero_last.pack(anchor="w", pady=(T.px(2), 0))

        btns = tk.Frame(content, bg=HERO_BG)
        btns.pack(anchor="w", pady=(T.px(14), 0))
        W.Button(btns, "立即练习", command=self._quick_start, kind="primary", size="lg",
                 icon="▶", bg=HERO_BG).pack(side="left")
        W.Button(btns, "随机来一局", command=self._random_start, kind="ghost", size="lg",
                 icon="⚡", bg=HERO_BG).pack(side="left", padx=T.px(10))
        W.Button(btns, "自定义文本", command=self._custom, kind="ghost", size="lg",
                 bg=HERO_BG).pack(side="left")

        self.emblem = None

    def _draw_hero_bg(self) -> None:
        c = self.hero_canvas
        c.delete("all")
        w = c.winfo_width() or 1
        h = c.winfo_height() or 1
        T.round_rect(c, 0, 0, w, h, T.px(18), fill=HERO_BG, outline=T.BORDER, width=1)
        # 右侧光晕
        cx, cy = w - T.px(120), h / 2
        for i in range(16, 0, -1):
            r = T.px(24) * i * 0.62
            color = T.mix(HERO_BG, T.ORANGE, 0.012 * (17 - i))
            c.create_oval(cx - r, cy - r * 0.95, cx + r, cy + r * 0.95, fill=color,
                          outline=color)
        # 底部细光线
        c.create_line(T.px(28), h - T.px(16), w - T.px(28), h - T.px(16),
                      fill=T.mix(HERO_BG, T.ORANGE, 0.18), width=1)
        # 星火点缀
        sparks = [(0.55, 0.22, 2), (0.63, 0.78, 1.5), (0.82, 0.16, 2.2), (0.9, 0.72, 1.8),
                  (0.72, 0.55, 1.4), (0.48, 0.68, 1.6)]
        for fx, fy, r in sparks:
            x, y = w * fx, h * fy
            rad = T.px(r)
            c.create_oval(x - rad, y - rad, x + rad, y + rad,
                          fill=T.mix(HERO_BG, T.GOLD, 0.55), outline="")
        # 品牌徽章（直接画在横幅画布上，避免出现方形色块）
        self._draw_emblem(c, w - T.px(137), h / 2)

    def _draw_emblem(self, c, cx: float, cy: float) -> None:
        for i in range(12, 0, -1):
            r = T.px(7.4) * i
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          fill=T.mix(HERO_BG, T.ORANGE, 0.03 * (13 - i)), outline="")
        r = T.px(62)
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill=T.mix(HERO_BG, T.ORANGE, 0.16), outline=T.ORANGE, width=T.px(2))
        c.create_text(cx, cy + T.px(2), text="风", fill=T.ORANGE_HI,
                      font=T.font(46, bold=True, family=T.FONT_CN))
        # 风火轮：外圈弧线
        for offset, color, width in ((0, T.GOLD, 2), (120, T.RED, 1), (240, T.ORANGE, 1)):
            r2 = T.px(84)
            c.create_arc(cx - r2, cy - r2, cx + r2, cy + r2, start=offset + 20,
                         extent=70, style="arc", outline=T.mix(HERO_BG, color, 0.7),
                         width=T.px(width))
        # 混天绫飘带
        c.create_line(cx - T.px(96), cy + T.px(58), cx - T.px(40), cy + T.px(78),
                      cx + T.px(18), cy + T.px(62), cx + T.px(70), cy + T.px(86),
                      fill=T.mix(HERO_BG, T.RED, 0.55), width=T.px(3), smooth=True)

    # ------------------------------------------------------------ 数据概览
    def _build_stats(self) -> None:
        row = tk.Frame(self.body, bg=T.BG)
        row.pack(fill="x", padx=T.px(26))
        self.stat_values: dict[str, tk.Label] = {}
        self.stat_subs: dict[str, tk.Label] = {}
        specs = [
            ("today", "今日练习", "0 次", T.ORANGE),
            ("chars", "累计字数", "0 字", T.GOLD),
            ("avg", "平均速度", "0", T.GREEN),
            ("best", "最佳速度", "0", T.CYAN),
        ]
        for idx, (key, title, default, color) in enumerate(specs):
            row.grid_columnconfigure(idx, weight=1, uniform="stats")
            card = W.Card(row, bg=T.CARD, border=T.BORDER)
            card.grid(row=0, column=idx, sticky="nsew",
                      padx=(0 if idx == 0 else T.px(7), 0 if idx == len(specs) - 1 else T.px(7)))
            body = tk.Frame(card.inner, bg=T.CARD)
            body.pack(fill="both", expand=True, padx=T.px(16), pady=T.px(12))
            top = tk.Frame(body, bg=T.CARD)
            top.pack(fill="x")
            tk.Frame(top, bg=color, width=T.px(3), height=T.px(12)).pack(side="left",
                                                                        padx=(0, T.px(7)))
            W.label(top, title, size=9, color=T.MUTED, bg=T.CARD).pack(side="left")
            value_row = tk.Frame(body, bg=T.CARD)
            value_row.pack(fill="x", pady=(T.px(4), 0))
            value = W.label(value_row, default, size=19, bold=True, color=T.TEXT, bg=T.CARD)
            value.pack(side="left")
            self.stat_values[key] = value
            sub = W.label(body, "", size=8, color=T.DIM, bg=T.CARD)
            sub.pack(anchor="w")
            self.stat_subs[key] = sub

    # ------------------------------------------------------------ 课程
    def _build_lessons(self) -> None:
        head = tk.Frame(self.body, bg=T.BG)
        head.pack(fill="x", padx=T.px(26), pady=(T.px(20), T.px(10)))
        W.label(head, "选择练习", size=15, bold=True, color=T.TEXT, bg=T.BG).pack(side="left")
        self.tabs = W.Segmented(head, [(c["id"], c["name"]) for c in C.CATEGORIES],
                                value=self.category, command=self._set_category, bg=T.BG,
                                height=34, size=10)
        self.tabs.pack(side="left", padx=T.px(16))
        W.Button(head, "自定义文本", command=self._custom, kind="ghost", size="sm",
                 icon="✎", bg=T.BG).pack(side="right")
        self.section_hint = W.label(head, "", size=9, color=T.DIM, bg=T.BG)
        self.section_hint.pack(side="right", padx=T.px(12))

        self.grid_box = tk.Frame(self.body, bg=T.BG)
        self.grid_box.pack(fill="both", expand=True, padx=T.px(26), pady=(0, T.px(24)))
        self._rebuild_lessons()

    def _rebuild_lessons(self) -> None:
        W.clear(self.grid_box)
        lessons = C.lessons_of(self.category)
        cols = self._cols_for_width()
        for col in range(max(4, getattr(self, "_cols", 4))):
            self.grid_box.grid_columnconfigure(col, weight=0, uniform="")
        self._cols = cols
        for col in range(cols):
            self.grid_box.grid_columnconfigure(col, weight=1, uniform="lesson")
        for idx, lesson in enumerate(lessons):
            row, col = divmod(idx, cols)
            card = LessonCard(self.grid_box, lesson, self._start_lesson)
            card.grid(row=row, column=col, sticky="nsew",
                      padx=(0 if col == 0 else T.px(7), 0 if col == cols - 1 else T.px(7)),
                      pady=(0, T.px(10)))
        cat = next((c for c in C.CATEGORIES if c["id"] == self.category), None)
        if cat:
            self.section_hint.configure(text=cat["subtitle"])
        self.scroll.attach(self.grid_box)

    # ------------------------------------------------------------ 行为
    def _set_category(self, value: str) -> None:
        self.category = value
        self.app.settings["last_category"] = value
        self.app.settings.save()
        self._rebuild_lessons()

    def _start_lesson(self, lesson_id: str) -> None:
        self.app.start_practice(lesson_id=lesson_id, category=self.category)

    def _quick_start(self) -> None:
        last = self.app.settings.get("last_session") or {}
        lesson_id = last.get("lesson_id") if isinstance(last, dict) else None
        if lesson_id and C.get_lesson(lesson_id):
            self.app.start_practice(lesson_id=lesson_id)
            return
        saved = self.app.settings.get("last_lesson") or {}
        lesson_id = saved.get(self.category) if isinstance(saved, dict) else None
        if lesson_id and C.get_lesson(lesson_id):
            self.app.start_practice(lesson_id=lesson_id)
        else:
            self.app.random_practice(self.category)

    def _random_start(self) -> None:
        self.app.random_practice(self.category)

    def _custom(self):
        dialog = CustomTextDialog(self, self.app)
        return dialog

    # ------------------------------------------------------------ 刷新
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        summary = self.app.history.summary()
        daily = self.app.history.daily(1)
        today = daily[-1] if daily else {"n": 0, "avg_cpm": 0.0}
        self.stat_values["today"].configure(text=f"{today['n']} 次")
        self.stat_subs["today"].configure(text="今天已完成的对局")
        self.stat_values["chars"].configure(text=_fmt_num(summary["chars"]))
        self.stat_subs["chars"].configure(text=f"约 {summary['count']} 次练习累计")
        self.stat_values["avg"].configure(text=f"{summary['avg_cpm']:.0f}")
        self.stat_subs["avg"].configure(
            text=f"字符/分 · 正确率 {summary['avg_accuracy']:.0f}%")
        self.stat_values["best"].configure(text=f"{summary['best_cpm']:.0f}")
        self.stat_subs["best"].configure(text="字符/分 · 历史最佳单局")

        last = self.app.settings.get("last_session") or {}
        if isinstance(last, dict) and last.get("title"):
            cpm = float(last.get("cpm") or 0)
            if str(last.get("mode", "en")).startswith("cn"):
                speed = f"{cpm:.0f} 字/分" if cpm else ""
            else:
                speed = f"{cpm / 5:.0f} WPM" if cpm else ""
            extra = f" · 上次速度 {speed}" if speed else ""
            self.hero_last.configure(text=f"上次练习：{last['title']}{extra}")
        else:
            self.hero_last.configure(text="还没有练习记录，从「基准键位」开始吧")


def _fmt_num(value: int) -> str:
    if value >= 10000:
        return f"{value / 10000:.1f} 万"
    return f"{value}"


class LessonCard(tk.Frame):
    """课程卡片（整块可点击）。"""

    def __init__(self, master, lesson: dict, command):
        super().__init__(master, bg=T.BORDER)
        self.lesson = lesson
        self.command = command
        self.inner = tk.Frame(self, bg=T.CARD)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)
        body = tk.Frame(self.inner, bg=T.CARD)
        body.pack(fill="both", expand=True, padx=T.px(14), pady=T.px(10))

        top = tk.Frame(body, bg=T.CARD)
        top.pack(fill="x")
        symbol = {"en": "A", "cn": "中", "num": "#"}.get(lesson["category"], "A")
        self.badge = W.Pill(top, symbol, fg=T.ORANGE, bg=T.CARD, size=8, pad=10)
        self.badge.pack(side="left")
        self.dots = LevelDots(top, lesson.get("level", 1), bg=T.CARD)
        self.dots.pack(side="right")

        self.title = W.label(body, lesson["title"], size=12, bold=True, color=T.TEXT, bg=T.CARD)
        self.title.pack(anchor="w", pady=(T.px(6), 0))
        self.desc = W.label(body, lesson.get("desc", ""), size=8, color=T.MUTED, bg=T.CARD,
                            wraplength=T.px(200), justify="left")
        self.desc.pack(anchor="w")
        body.bind("<Configure>",
                  lambda e, label=self.desc: label.configure(
                      wraplength=max(T.px(90), e.width)))

        self._widgets = [self, self.inner, body, top, self.title, self.desc]
        for widget in self._widgets + [self.badge, self.dots]:
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
            widget.bind("<ButtonRelease-1>", self._click, add="+")
            widget.configure(cursor="hand2")

    def _enter(self, _event=None):
        self.configure(bg=T.ORANGE)
        for widget in self._widgets:
            widget.configure(bg=T.CARD_HOVER)
        self.title.configure(fg=T.ORANGE_HI)
        self.badge.configure(bg=T.CARD_HOVER)
        self.dots.configure(bg=T.CARD_HOVER)

    def _leave(self, _event=None):
        self.configure(bg=T.BORDER)
        for widget in self._widgets:
            widget.configure(bg=T.CARD)
        self.title.configure(fg=T.TEXT)
        self.badge.configure(bg=T.CARD)
        self.dots.configure(bg=T.CARD)

    def _click(self, _event=None):
        self.command(self.lesson["id"])


class LevelDots(tk.Canvas):
    def __init__(self, master, level: int = 1, bg: str = T.CARD):
        self._bg = bg
        super().__init__(master, width=T.px(38), height=T.px(12), bg=bg,
                         highlightthickness=0, bd=0)
        colors = [T.GREEN, T.GOLD, T.RED]
        for i in range(3):
            x = T.px(4) + i * T.px(11)
            filled = i < int(level)
            color = colors[i] if filled else T.mix(bg, T.MUTED, 0.35)
            r = T.px(3)
            self.create_oval(x - r, T.px(6) - r, x + r, T.px(6) + r, fill=color, outline=color)


class CustomTextDialog(tk.Toplevel):
    """粘贴任意文本开始练习。"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("自定义文本")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        self.geometry(f"{T.px(660)}x{T.px(520)}")
        self.transient(master.winfo_toplevel())
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self._build()
        self._center(master)

    def _center(self, master):
        self.update_idletasks()
        top = master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build(self):
        tk.Frame(self, bg=T.ORANGE, height=T.px(3)).pack(fill="x")
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=T.px(24), pady=(T.px(16), T.px(4)))
        W.label(head, "自定义文本", size=16, bold=True, color=T.TEXT, bg=T.BG).pack(side="left")
        W.Button(head, "关闭", command=self.destroy, kind="ghost", size="sm",
                 bg=T.BG).pack(side="right")
        W.label(self, "粘贴或输入任意中英文内容，中文会自动按句子切成短行，英文按整段练习。",
                size=9, color=T.MUTED, bg=T.BG).pack(anchor="w", padx=T.px(24))

        foot = tk.Frame(self, bg=T.BG)
        foot.pack(side="bottom", fill="x", padx=T.px(24), pady=(0, T.px(16)))
        self.count = W.label(foot, "0 字", size=9, color=T.DIM, bg=T.BG)
        self.count.pack(side="left")
        W.Button(foot, "开始练习", command=self._start, kind="primary", size="md",
                 icon="▶", bg=T.BG).pack(side="right")

        wrap = tk.Frame(self, bg=T.BORDER)
        wrap.pack(fill="both", expand=True, padx=T.px(24), pady=T.px(12))
        self.text = tk.Text(wrap, bg=T.PANEL, fg=T.TEXT, insertbackground=T.ORANGE,
                            font=T.font(12), wrap="word", relief="flat", bd=0,
                            padx=T.px(14), pady=T.px(12), undo=True,
                            selectbackground=T.mix(T.PANEL, T.ORANGE, 0.35))
        self.text.pack(fill="both", expand=True, padx=1, pady=1)
        self.text.insert("1.0", "")
        self.text.focus_set()
        self.text.bind("<KeyRelease>", self._update_count)
        self.bind("<Escape>", lambda e: self.destroy())

    def _update_count(self, _event=None):
        content = self.text.get("1.0", "end").strip()
        self.count.configure(text=f"{len(content)} 字")

    def _start(self):
        raw = self.text.get("1.0", "end").strip()
        plan = C.build_custom(raw, "自定义文本")
        if not plan:
            messagebox.showwarning("内容为空", "请输入至少一段文字再开始。", parent=self)
            return
        self.destroy()
        self.app.start_practice(plan=plan)
