"""统计页：速度趋势、模式对比、每日练习量、历史记录。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import engine as E
from .. import theme as T
from .. import widgets as W
from .base import BaseScreen

MODE_OPTIONS = [("", "全部"), ("en", "英文"), ("cn", "中文"), ("num", "符号")]
MODE_NAMES = {"en": "英文", "cn": "中文", "num": "符号"}
MODE_COLORS = {"en": T.ORANGE, "cn": T.CYAN, "num": T.PURPLE}


def _duration(seconds: float) -> str:
    seconds = int(seconds or 0)
    if seconds >= 3600:
        return f"{seconds / 3600:.1f} 小时"
    if seconds >= 60:
        return f"{seconds // 60} 分 {seconds % 60} 秒"
    return f"{seconds} 秒"


def _fmt_num(value: int) -> str:
    value = int(value or 0)
    if value >= 10000:
        return f"{value / 10000:.1f} 万"
    return str(value)


class StatsScreen(BaseScreen):
    name = "stats"

    def __init__(self, app, master):
        super().__init__(app, master)
        self.mode = ""
        self.scroll = W.ScrollFrame(self, bg=T.BG)
        self.scroll.pack(fill="both", expand=True)
        self.body = self.scroll.body
        self._build_header()
        self._build_cards()
        self._build_trend()
        self._build_charts()
        self._build_records()
        self.scroll.attach()
        self._bind_wheel_tree()

    # ------------------------------------------------------------ 结构
    def _build_header(self) -> None:
        row = tk.Frame(self.body, bg=T.BG)
        row.pack(fill="x", padx=T.px(26), pady=(T.px(20), T.px(14)))
        left = tk.Frame(row, bg=T.BG)
        left.pack(side="left")
        W.label(left, "练习统计", size=22, bold=True, bg=T.BG).pack(anchor="w")
        W.label(left, "每一次练习都会记录在本机，可随时清空", size=10, color=T.MUTED,
                bg=T.BG).pack(anchor="w", pady=(T.px(2), 0))

        right = tk.Frame(row, bg=T.BG)
        right.pack(side="right")
        self.filter = W.Segmented(right, MODE_OPTIONS, value="", command=self._set_mode,
                                  bg=T.BG, height=32)
        self.filter.pack(side="left")
        W.Button(right, "清空记录", command=self._clear, kind="danger", size="sm",
                 icon="🗑", bg=T.BG).pack(side="left", padx=T.px(12))

    def _build_cards(self) -> None:
        grid = tk.Frame(self.body, bg=T.BG)
        grid.pack(fill="x", padx=T.px(26))
        keys = [("count", "练习次数", T.CYAN), ("time", "累计时长", T.PURPLE),
                ("avg", "平均速度", T.ORANGE), ("best", "最佳速度", T.GOLD),
                ("acc", "平均正确率", T.GREEN)]
        self.cards: dict[str, tuple[tk.Label, tk.Label]] = {}
        for i, (key, title, color) in enumerate(keys):
            grid.columnconfigure(i, weight=1, uniform="statcard")
            card = W.Card(grid)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else T.px(10), 0))
            inner = tk.Frame(card.body, bg=T.CARD)
            inner.pack(fill="both", expand=True, padx=T.px(14), pady=T.px(12))
            tk.Frame(inner, bg=color, width=T.px(3)).pack(side="left", fill="y")
            holder = tk.Frame(inner, bg=T.CARD)
            holder.pack(side="left", fill="both", expand=True, padx=(T.px(10), 0))
            W.label(holder, title, size=9, color=T.MUTED, bg=T.CARD).pack(anchor="w")
            value = W.label(holder, "0", size=17, bold=True, bg=T.CARD)
            value.pack(anchor="w", pady=(T.px(2), 0))
            sub = W.label(holder, "", size=8, color=T.DIM, bg=T.CARD)
            sub.pack(anchor="w")
            self.cards[key] = (value, sub)

    def _build_trend(self) -> None:
        card = W.Card(self.body)
        card.pack(fill="x", padx=T.px(26), pady=(T.px(14), 0))
        head = tk.Frame(card.body, bg=T.CARD)
        head.pack(fill="x", padx=T.px(16), pady=(T.px(14), 0))
        W.label(head, "速度趋势", size=12, bold=True, bg=T.CARD).pack(side="left")
        self.trend_hint = W.label(head, "", size=9, color=T.MUTED, bg=T.CARD)
        self.trend_hint.pack(side="right")
        self.chart = W.LineChart(card.body, height=206, bg=T.CARD, color=T.ORANGE)
        self.chart.pack(fill="x", padx=T.px(10), pady=(T.px(6), T.px(10)))

    def _build_charts(self) -> None:
        row = tk.Frame(self.body, bg=T.BG)
        row.pack(fill="x", padx=T.px(26), pady=(T.px(14), 0))
        row.columnconfigure(0, weight=1, uniform="chart")
        row.columnconfigure(1, weight=1, uniform="chart")

        left = W.Card(row)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, T.px(10)))
        head = tk.Frame(left.body, bg=T.CARD)
        head.pack(fill="x", padx=T.px(16), pady=(T.px(14), 0))
        W.label(head, "各类型平均速度", size=12, bold=True, bg=T.CARD).pack(side="left")
        W.label(head, "英文 WPM · 中文 字/分 · 符号 字符/分", size=8,
                color=T.DIM, bg=T.CARD).pack(side="right")
        self.mode_chart = W.BarChart(left.body, height=178, bg=T.CARD)
        self.mode_chart.pack(fill="x", padx=T.px(10), pady=(T.px(4), T.px(10)))

        right = W.Card(row)
        right.grid(row=0, column=1, sticky="nsew")
        W.label(right.body, "近 14 天练习量", size=12, bold=True, bg=T.CARD).pack(
            anchor="w", padx=T.px(16), pady=(T.px(14), 0))
        self.day_chart = W.BarChart(right.body, height=178, bg=T.CARD)
        self.day_chart.pack(fill="x", padx=T.px(10), pady=(T.px(4), T.px(10)))

    def _build_records(self) -> None:
        card = W.Card(self.body)
        card.pack(fill="both", expand=True, padx=T.px(26), pady=(T.px(14), T.px(20)))
        head = tk.Frame(card.body, bg=T.CARD)
        head.pack(fill="x", padx=T.px(16), pady=(T.px(14), T.px(8)))
        W.label(head, "历史记录", size=12, bold=True, bg=T.CARD).pack(side="left")
        self.count_hint = W.label(head, "", size=9, color=T.MUTED, bg=T.CARD)
        self.count_hint.pack(side="right")

        wrap = tk.Frame(card.body, bg=T.CARD)
        wrap.pack(fill="both", expand=True, padx=T.px(12), pady=(0, T.px(12)))
        cols = ("time", "title", "mode", "cpm", "acc", "grade")
        heads = {"time": "时间", "title": "课程", "mode": "类型",
                 "cpm": "速度", "acc": "正确率", "grade": "评价"}
        widths = {"time": 128, "title": 300, "mode": 70, "cpm": 110, "acc": 90, "grade": 70}
        anchors = {"time": "w", "title": "w", "mode": "center",
                   "cpm": "e", "acc": "e", "grade": "center"}
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=11)
        for col in cols:
            self.tree.heading(col, text=heads[col], anchor=anchors[col])
            self.tree.column(col, width=T.px(widths[col]), anchor=anchors[col],
                             stretch=(col == "title"))
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for grade, color in (("S", T.GOLD), ("A", T.ORANGE), ("B", T.CYAN),
                             ("C", T.MUTED), ("D", T.RED)):
            self.tree.tag_configure(grade, foreground=color)

    def _bind_wheel_tree(self) -> None:
        def wheel(event):
            self.tree.yview_scroll(int(-event.delta / 120), "units")
            return "break"
        self.tree.bind("<MouseWheel>", wheel)

    # ------------------------------------------------------------ 交互
    def _set_mode(self, value: str) -> None:
        self.mode = value
        self.refresh()

    def _clear(self) -> None:
        scope = MODE_NAMES.get(self.mode, "全部")
        if not messagebox.askyesno("清空记录", f"确定要清空{scope}练习记录吗？此操作不可撤销。",
                                   parent=self.winfo_toplevel()):
            return
        self.app.history.clear(self.mode or None)
        self.refresh()
        self.app.toast("已清空练习记录")

    # ------------------------------------------------------------ 刷新
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        mode = self.mode or None
        s = self.app.history.summary(mode)
        unit = "字符/分"
        value, sub = self.cards["count"]
        value.configure(text=f"{s['count']}")
        sub.configure(text=f"共 {_fmt_num(s['chars'])} 字")
        value, sub = self.cards["time"]
        value.configure(text=_duration(s["seconds"]))
        sub.configure(text=f"平均每局 {_duration(s['avg_seconds'])}")
        avg_value, avg_unit = E.speed_for(self.mode or "all", s["avg_cpm"])
        best_value, best_unit = E.speed_for(self.mode or "all", s["best_cpm"])
        value, sub = self.cards["avg"]
        value.configure(text=f"{avg_value:.0f}")
        sub.configure(text=f"{avg_unit} · 正确率 {s['avg_accuracy']:.0f}%")
        value, sub = self.cards["best"]
        value.configure(text=f"{best_value:.0f}")
        sub.configure(text=f"{best_unit} · 最佳单局")
        value, sub = self.cards["acc"]
        value.configure(text=f"{s['avg_accuracy']:.1f}%")
        sub.configure(text="全部练习平均")

        timeline = list(self.app.history.timeline(limit=20, mode=mode))
        points = []
        for row in timeline:
            stamp = str(row.get("ts", ""))[5:16].replace("T", " ")
            row_mode = str(row.get("mode", ""))
            raw = float(row.get("cpm") or 0)
            if mode and mode != "all":
                num, u = E.speed_for(mode, raw)
            else:
                num, u = raw, "字符/分"
            points.append({"label": stamp, "value": num, "unit": u})
        self.chart.set_points(points)
        trend_avg, trend_unit = E.speed_for(self.mode or "all", s["avg_cpm"])
        self.trend_hint.configure(
            text=f"最近 {len(points)} 次 · 平均 {trend_avg:.0f} {trend_unit}"
            if points else "暂无数据")

        by_mode = self.app.history.by_mode()
        items = []
        for row in by_mode:
            key = str(row.get("mode", ""))
            num, _u = E.speed_for(key, float(row.get("avg_cpm") or 0))
            items.append({"label": MODE_NAMES.get(key, key or "其他"),
                          "value": num,
                          "color": MODE_COLORS.get(key, T.BORDER_HI)})
        self.mode_chart.set_items(items)

        days = self.app.history.daily(14)
        self.day_chart.set_items([{"label": str(d.get("day", ""))[5:],
                                   "value": d.get("n", 0),
                                   "color": T.CYAN if d.get("n") else T.BORDER} for d in days])

        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.app.history.recent(limit=120, mode=mode)
        for row in rows:
            key = str(row.get("mode", ""))
            num, u = E.speed_for(key, float(row.get("cpm") or 0))
            stamp = str(row.get("ts", ""))[:16].replace("T", " ")
            self.tree.insert("", "end", tags=(str(row.get("grade", "") or ""),), values=(
                stamp,
                row.get("lesson_title", ""),
                MODE_NAMES.get(key, key),
                f"{num:.0f} {u}",
                f"{float(row.get('accuracy') or 0):.0f}%",
                row.get("grade", ""),
            ))
        self.count_hint.configure(text=f"共 {len(rows)} 条")
