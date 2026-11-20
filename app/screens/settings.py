"""设置页：练习偏好、声音、数据与关于。"""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

from .. import config as CFG
from .. import theme as T
from .. import widgets as W
from ..music_ui import LOOP_MODES
from .base import BaseScreen

LENGTHS = [("short", "短"), ("medium", "中"), ("long", "长")]
UI_SCALES = [("0.9", "紧凑"), ("1", "标准"), ("1.1", "大"), ("1.2", "超大")]
CARET_STYLES = [("bar", "竖线"), ("block", "方框"), ("underline", "下划线")]
FONT_CANDIDATES = [
    "Cascadia Mono", "Cascadia Code", "Consolas", "Courier New", "Lucida Console",
    "JetBrains Mono", "Fira Code", "Source Code Pro", "Segoe UI",
    "Microsoft YaHei", "Microsoft YaHei UI", "DengXian", "SimHei",
    "KaiTi", "FangSong", "SimSun", "Noto Sans Mono CJK SC", "Sarasa Mono SC",
]
SHORTCUTS = [
    ("Tab", "英文模式：重新开始本局"),
    ("F5", "中文模式：重新开始本局"),
    ("Esc", "退出练习，返回首页"),
    ("Backspace", "英文模式：退格重打"),
    ("空格", "英文模式：照常输入空格"),
    ("Enter", "代码练习：换行自动跳过，按 Enter 也可前进"),
]


class SettingsScreen(BaseScreen):
    name = "settings"

    def __init__(self, app, master):
        super().__init__(app, master)
        self.scroll = W.ScrollFrame(self, bg=T.BG)
        self.scroll.pack(fill="both", expand=True)
        self.body = self.scroll.body
        self._build_header()
        self._build_practice()
        self._build_sound()
        self._build_data()
        self._build_shortcuts()
        self.scroll.attach()

    # ------------------------------------------------------------ 结构
    def _build_header(self) -> None:
        head = tk.Frame(self.body, bg=T.BG)
        head.pack(fill="x", padx=T.px(26), pady=(T.px(20), T.px(4)))
        W.label(head, "设置", size=22, bold=True, bg=T.BG).pack(anchor="w")
        W.label(head, "所有修改即时生效，并保存到本机", size=10, color=T.MUTED,
                bg=T.BG).pack(anchor="w", pady=(T.px(2), 0))

    def _section(self, title: str, subtitle: str = "") -> tk.Frame:
        card = W.Card(self.body)
        card.pack(fill="x", padx=T.px(26), pady=(T.px(12), 0))
        head = tk.Frame(card.body, bg=T.CARD)
        head.pack(fill="x", padx=T.px(18), pady=(T.px(14), T.px(4)))
        W.label(head, title, size=12, bold=True, bg=T.CARD).pack(side="left")
        if subtitle:
            W.label(head, subtitle, size=9, color=T.MUTED, bg=T.CARD).pack(
                side="left", padx=(T.px(10), 0))
        return card.body

    def _row(self, parent: tk.Frame, title: str, desc: str, factory, first: bool = False):
        """一行设置：左侧标题与说明，右侧由 factory(row) 现场创建控件。"""
        if not first:
            W.divider(parent, pady=0).pack(fill="x", padx=T.px(18))
        row = tk.Frame(parent, bg=T.CARD)
        row.pack(fill="x", padx=T.px(18), pady=T.px(10))
        left = tk.Frame(row, bg=T.CARD)
        left.pack(side="left", fill="x", expand=True)
        W.label(left, title, size=10, bg=T.CARD).pack(anchor="w")
        if desc:
            W.label(left, desc, size=8, color=T.DIM, bg=T.CARD).pack(anchor="w",
                                                                     pady=(T.px(1), 0))
        control = factory(row)
        if control is not None:
            control.pack(side="right", padx=(T.px(16), 0))
        return control

    def _slider_row(self, parent: tk.Frame, title: str, desc: str, value: float,
                    command, suffix: str = "", first: bool = False) -> tk.Widget:
        box: dict[str, tk.Widget] = {}

        def factory(row):
            holder = tk.Frame(row, bg=T.CARD)
            slider = W.Slider(holder, value=value, command=command, width=170, bg=T.CARD)
            slider.pack(side="left")
            value_label = W.label(holder, "", size=9, color=T.ORANGE, bg=T.CARD, width=5)
            value_label.pack(side="left", padx=(T.px(6), 0))

            def _sync(v: float) -> None:
                command(v)
                value_label.configure(text=f"{v * 100:.0f}{suffix}")

            slider.command = _sync
            _sync(value)
            box["slider"] = slider
            return holder

        self._row(parent, title, desc, factory, first=first)
        return box["slider"]

    # ------------------------------------------------------------ 分组
    def _build_practice(self) -> None:
        p = self._section("练习", "决定题量、难度与练字大小")
        s = self.app.settings
        self._row(
            p, "界面缩放", "整体放大字体与控件，改变后立即生效（Ctrl + 加号 / 减号）",
            lambda row: W.Segmented(row, UI_SCALES,
                                    value=f"{float(s.get('ui_scale', 1.0)):.2f}".rstrip("0").rstrip("."),
                                    command=self._set_ui_scale, bg=T.CARD, height=30),
            first=True)
        families = set(tkfont.families(self))
        font_options = [("", "默认（英文等宽 / 中文雅黑）")]
        font_options += [(name, name) for name in FONT_CANDIDATES if name in families]
        current_font = str(s.get("practice_font") or "")
        if current_font and current_font not in families:
            font_options.append((current_font, current_font))
        self._row(
            p, "练习字体", "只影响练习区的目标文字，下拉可选系统字体",
            lambda row: W.Dropdown(row, font_options, value=current_font,
                                   command=self._set_font_family, bg=T.CARD, width=200))
        self._row(
            p, "光标样式", "竖线更轻，方框更醒目，下划线更像纸面练习",
            lambda row: W.Segmented(row, CARET_STYLES,
                                    value=str(s.get("caret_style", "bar")),
                                    command=self._set_caret_style, bg=T.CARD, height=30))
        self._row(
            p, "光标平滑移动", "光标跟随字符位置做短距离滑动，而不是瞬间跳转",
            lambda row: W.Toggle(row, value=bool(s.get("caret_smooth", True)),
                                 command=self._set_caret_smooth, bg=T.CARD))
        self._row(
            p, "严格模式", "打错字不前进，必须先退格改正（推荐新手开启）",
            lambda row: W.Toggle(row, value=bool(s.get("strict_mode", True)),
                                 command=self._set_strict, bg=T.CARD))
        self._row(
            p, "每局长度", "短约 1 分钟，中约 2 分钟，长约 3 分钟",
            lambda row: W.Segmented(row, LENGTHS, value=str(s.get("practice_length", "medium")),
                                    command=self._set_length, bg=T.CARD, height=30))

        def font_row(row):
            holder = tk.Frame(row, bg=T.CARD)
            label = W.label(holder, "", size=9, color=T.GOLD, bg=T.CARD, width=4)
            label.pack(side="right", padx=(T.px(6), 0))
            slider = W.Slider(holder, value=self._font_to_value(s.target_font_size),
                              command=self._set_font_size, width=170, bg=T.CARD,
                              color=T.GOLD)
            slider.pack(side="left")
            self.font_label = label
            label.configure(text=f"{s.target_font_size}pt")
            return holder

        self._row(p, "目标文字大小", "字号越大越容易看清，适合投影或大屏", font_row)
        self._row(
            p, "显示虚拟键盘", "练习时在底部显示键位提示",
            lambda row: W.Toggle(row, value=bool(s.get("show_keyboard", True)),
                                 command=self._set_keyboard, bg=T.CARD))

    def _build_sound(self) -> None:
        p = self._section("声音", "背景音乐与按键音效")
        s = self.app.settings
        self._row(
            p, "按键音效", "敲对一声轻响，敲错一声提示",
            lambda row: W.Toggle(row, value=bool(s.get("sound_enabled", True)),
                                 command=self._set_sound_enabled, bg=T.CARD),
            first=True)
        self.sfx_slider = self._slider_row(
            p, "音效音量", "只影响击键提示音", float(s.get("sound_volume", 0.45)),
            self._set_sound_volume, suffix="%")
        self.music_slider = self._slider_row(
            p, "背景音乐音量", "播放条上的音量同步此设置", float(s.get("music_volume", 0.45)),
            self._set_music_volume, suffix="%")
        self._row(
            p, "音乐循环方式", "一首放完接着下一首，或单曲循环",
            lambda row: W.Segmented(row, LOOP_MODES, value=str(s.get("music_loop_mode", "list")),
                                    command=self._set_loop, bg=T.CARD, height=30))

    def _build_data(self) -> None:
        p = self._section("数据", "练习记录保存在本机，不联网")

        def dir_row(row):
            holder = tk.Frame(row, bg=T.CARD)
            W.Button(holder, "打开目录", command=self._open_data_dir, kind="soft", size="sm",
                     bg=T.CARD).pack(side="right")
            W.label(holder, str(CFG.user_dir()), size=9, color=T.MUTED,
                    bg=T.CARD).pack(side="left", padx=(0, T.px(12)))
            return holder

        self._row(p, "数据目录", "settings.json 与 history.db 都在这里", dir_row, first=True)

        def clear_row(row):
            holder = tk.Frame(row, bg=T.CARD)
            W.Button(holder, "清空全部记录", command=self._clear_all, kind="danger", size="sm",
                     bg=T.CARD).pack(side="right")
            W.label(holder, f"已记录 {self.app.history.count()} 次练习", size=9,
                    color=T.MUTED, bg=T.CARD).pack(side="left")
            return holder

        self._row(p, "清空练习记录", "只删除成绩历史，不影响设置与音乐列表", clear_row)

        def about_row(row):
            holder = tk.Frame(row, bg=T.CARD)
            W.label(holder, f"{CFG.APP_NAME} v{CFG.VERSION} · {CFG.TAGLINE}", size=9,
                    color=T.DIM, bg=T.CARD).pack(side="right")
            return holder

        self._row(p, "关于", "Python + tkinter 编写，单文件绿色版", about_row)

    def _build_shortcuts(self) -> None:
        p = self._section("快捷键", "练习页随时可用")
        table = tk.Frame(p, bg=T.CARD)
        table.pack(fill="x", padx=T.px(18), pady=(T.px(6), T.px(16)))
        for i, (key, desc) in enumerate(SHORTCUTS):
            col, row = i % 2, i // 2
            cell = tk.Frame(table, bg=T.CARD)
            cell.grid(row=row, column=col, sticky="w", padx=(0, T.px(30)),
                      pady=T.px(5))
            W.Pill(cell, key, fg=T.TEXT_SOFT, bg=T.CARD, size=8).pack(side="left")
            W.label(cell, desc, size=9, color=T.MUTED, bg=T.CARD).pack(
                side="left", padx=(T.px(8), 0))
        tk.Frame(self.body, bg=T.BG, height=T.px(18)).pack()

    # ------------------------------------------------------------ 回调
    def _save(self) -> None:
        self.app.settings.save()

    def _apply_practice_style(self) -> None:
        practice = self.app.screens.get("practice")
        if practice is not None and hasattr(practice, "apply_practice_style"):
            try:
                practice.apply_practice_style()
            except Exception:
                pass

    def _set_font_family(self, value: str) -> None:
        self.app.settings["practice_font"] = value
        self.app.settings.save()
        self._apply_practice_style()

    def _set_caret_style(self, value: str) -> None:
        self.app.settings["caret_style"] = value
        self.app.settings.save()
        self._apply_practice_style()

    def _set_caret_smooth(self, value: bool) -> None:
        self.app.settings["caret_smooth"] = bool(value)
        self.app.settings.save()
        self._apply_practice_style()

    def _set_strict(self, value: bool) -> None:
        self.app.settings["strict_mode"] = bool(value)
        self._save()

    def _set_length(self, value: str) -> None:
        self.app.settings["practice_length"] = value
        self._save()

    def _set_ui_scale(self, value: str) -> None:
        try:
            scale = float(value)
        except (TypeError, ValueError):
            return
        # 重建界面会销毁本页，延后到事件回调结束后再执行
        self.app.root.after(10, lambda: self.app.apply_ui_scale(scale))

    def _font_to_value(self, size: int) -> float:
        return max(0.0, min(1.0, (int(size) - 18) / 28))

    def _set_font_size(self, ratio: float) -> None:
        size = int(round(18 + ratio * 28))
        self.app.settings["target_font_size"] = size
        if getattr(self, "font_label", None) is not None:
            self.font_label.configure(text=f"{size}pt")
        self._save()

    def _set_keyboard(self, value: bool) -> None:
        self.app.settings["show_keyboard"] = bool(value)
        self._save()

    def _set_sound_enabled(self, value: bool) -> None:
        self.app.settings["sound_enabled"] = bool(value)
        self._save()

    def _set_sound_volume(self, value: float) -> None:
        self.app.settings["sound_volume"] = round(float(value), 3)
        self.app.sounds.set_volume(float(value))
        self._save()

    def _set_music_volume(self, value: float) -> None:
        self.app.settings["music_volume"] = round(float(value), 3)
        self.app.player.set_volume(float(value), persist=False)
        self._save()

    def _set_loop(self, value: str) -> None:
        self.app.settings["music_loop_mode"] = value
        self._save()

    def _open_data_dir(self) -> None:
        path = CFG.user_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            self.app.toast(f"数据目录：{path}")

    def _clear_all(self) -> None:
        if not messagebox.askyesno("清空记录", "确定要删除全部练习记录吗？此操作不可撤销。",
                                   parent=self.winfo_toplevel()):
            return
        self.app.history.clear(None)
        self.app.toast("已清空全部练习记录")
        self.app.refresh_screens()

    # ------------------------------------------------------------ 刷新
    def on_show(self) -> None:
        s = self.app.settings
        if getattr(self, "font_label", None) is not None:
            self.font_label.configure(text=f"{s.target_font_size}pt")
        self.sfx_slider.set(float(s.get("sound_volume", 0.45)))
        self.music_slider.set(float(s.get("music_volume", 0.45)))
