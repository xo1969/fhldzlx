"""帮助与快捷键浮层。"""
from __future__ import annotations

import os
import tkinter as tk

from . import config as CFG
from . import theme as T
from . import widgets as W

SHORTCUTS = [
    ("Tab / F5", "重开本局"),
    ("Esc", "返回首页"),
    ("Backspace", "英文模式退格修正"),
    ("Ctrl + 1 / 2 / 3", "首页 / 统计 / 设置"),
    ("Ctrl + 加号 / 减号", "放大 / 缩小整个界面"),
    ("Ctrl + 0", "界面缩放恢复标准"),
    ("F1", "打开本帮助"),
    ("Space", "输入空格（严格模式下也要打对）"),
    ("Enter", "代码练习：行末自动进入下一行，按 Enter 也可跳过"),
]

TIPS = [
    "英文练习直接敲键盘即可，目标文本会逐字变色；严格模式下打错不前进。",
    "中文练习在下方输入框输入高亮那一行，整行打对会自动换行，兼容输入法整段上屏。",
    "每个练习都按第一下击键开始计时，暂停时计时也会暂停。",
    "背景音乐可以用底部「播放列表」添加单曲或整个文件夹，会自动记住。",
    "设置页还能换练习字体、光标样式（竖线 / 方框 / 下划线），以及光标平滑移动。",
]


class HelpDialog(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("帮助 · 风火轮打字")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        self.geometry(f"{T.px(600)}x{T.px(700)}")
        self.transient(master.winfo_toplevel())
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self._build()
        self._center(master)
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _center(self, master):
        self.update_idletasks()
        top = master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build(self):
        tk.Frame(self, bg=T.ORANGE, height=T.px(3)).pack(fill="x")
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=T.px(24), pady=(T.px(16), T.px(2)))
        W.label(head, "帮助", size=18, bold=True, color=T.TEXT, bg=T.BG).pack(side="left")
        W.label(head, f"v{CFG.VERSION} · {CFG.TAGLINE}", size=9, color=T.DIM,
                bg=T.BG).pack(side="left", padx=T.px(10), pady=(T.px(4), 0))
        W.Button(head, "关闭", command=self.close, kind="ghost", size="sm",
                 bg=T.BG).pack(side="right")

        foot = tk.Frame(self, bg=T.BG)
        foot.pack(side="bottom", fill="x", padx=T.px(24), pady=(0, T.px(16)))
        W.label(foot, "数据目录：%LOCALAPPDATA%\\FirewheelTyping", size=8,
                color=T.DIM, bg=T.BG).pack(side="left")
        W.Button(foot, "打开目录", command=self._open_dir, kind="link", size="xs",
                 bg=T.BG).pack(side="left", padx=(T.px(8), 0))
        W.Button(foot, "开始练习", command=self._practice, kind="primary", size="md",
                 icon="▶", bg=T.BG).pack(side="right")

        body = W.ScrollFrame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=T.px(20), pady=(T.px(8), T.px(8)))
        box = body.body

        W.label(box, "怎么练", size=12, bold=True, color=T.ORANGE, bg=T.BG).pack(
            anchor="w", padx=T.px(6), pady=(T.px(4), T.px(6)))
        for tip in TIPS:
            row = tk.Frame(box, bg=T.BG)
            row.pack(fill="x", padx=T.px(6), pady=T.px(2))
            W.label(row, "·", size=10, color=T.ORANGE, bg=T.BG).pack(side="left", anchor="n")
            W.label(row, tip, size=9, color=T.TEXT_SOFT, bg=T.BG).pack(
                side="left", fill="x", padx=(T.px(4), 0))

        W.label(box, "快捷键", size=12, bold=True, color=T.ORANGE, bg=T.BG).pack(
            anchor="w", padx=T.px(6), pady=(T.px(14), T.px(6)))
        table = tk.Frame(box, bg=T.CARD)
        table.pack(fill="x", padx=T.px(6))
        for i, (key, desc) in enumerate(SHORTCUTS):
            if i:
                W.divider(table).pack(fill="x", padx=T.px(12))
            row = tk.Frame(table, bg=T.CARD)
            row.pack(fill="x", padx=T.px(14), pady=T.px(7))
            W.Pill(row, key, fg=T.ORANGE, fill=T.PANEL_2, size=8).pack(side="left")
            W.label(row, desc, size=9, color=T.TEXT_SOFT, bg=T.CARD).pack(
                side="left", padx=T.px(12))
        W.label(box, "", size=2, bg=T.BG).pack()

    def _open_dir(self):
        try:
            os.startfile(CFG.user_dir())
        except OSError:
            pass

    def _practice(self):
        self.close()
        self.app.start_practice()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


def open_help(app) -> HelpDialog:
    return HelpDialog(app.root, app)
