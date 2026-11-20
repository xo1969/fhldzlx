"""背景音乐界面：底部播放条 + 播放列表弹窗。"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import theme as T
from . import widgets as W

LOOP_MODES = [("list", "列表循环"), ("one", "单曲循环"), ("shuffle", "随机播放")]


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _short_dir(folder: Path, limit: int = 34) -> str:
    text = str(folder)
    if len(text) <= limit:
        return text
    return "…" + text[-(limit - 1):]


class MusicBar(tk.Frame):
    """底部常驻播放条：曲目信息 + 上一首/播放/下一首 + 音量 + 播放列表。"""

    def __init__(self, master, app, **kw):
        super().__init__(master, bg=T.PANEL, height=T.px(66), **kw)
        self.app = app
        self.player = app.player
        self.pack_propagate(False)

        top = tk.Frame(self, bg=T.PANEL)
        top.pack(fill="both", expand=True, padx=T.px(18), pady=T.px(8))
        self.progress_line = tk.Canvas(self, height=T.px(2), bg=T.PANEL, highlightthickness=0, bd=0)
        self.progress_line.place(x=0, rely=1.0, relwidth=1.0, anchor="sw")

        # 图标
        icon = tk.Canvas(top, width=T.px(38), height=T.px(38), bg=T.PANEL,
                         highlightthickness=0, bd=0)
        icon.pack(side="left", padx=(0, T.px(10)))
        self._icon = icon
        icon.create_oval(0, 0, T.px(38), T.px(38), fill=T.mix(T.PANEL, T.ORANGE, 0.2),
                         outline=T.mix(T.PANEL, T.ORANGE, 0.5))
        icon.create_text(T.px(19), T.px(19), text="♫", fill=T.ORANGE,
                         font=T.font(15, bold=True, family=T.FONT_SYM))

        # 文字
        self.text_box = tk.Frame(top, bg=T.PANEL)
        self.text_box.pack(side="left", fill="both", expand=True)
        self.title_label = W.label(self.text_box, "背景音乐", size=10, bold=True, color=T.TEXT)
        self.title_label.pack(anchor="w", pady=(T.px(2), 0))
        self.sub_label = W.label(self.text_box, "", size=9, color=T.DIM)
        self.sub_label.pack(anchor="w")

        # 控制键
        ctrl = tk.Frame(top, bg=T.PANEL)
        ctrl.pack(side="right", padx=(T.px(10), 0))
        self.btn_list = W.Button(ctrl, "播放列表", command=self.open_playlist, kind="ghost",
                                 size="sm", icon="☰", bg=T.PANEL)
        self.btn_list.pack(side="right", padx=(T.px(8), 0))
        self.btn_next = W.PlayerButton(ctrl, "next", command=self._next, size=30, bg=T.PANEL)
        self.btn_next.pack(side="right")
        self.btn_play = W.PlayerButton(ctrl, "play", command=self._toggle, size=38,
                                       primary=True, bg=T.PANEL)
        self.btn_play.pack(side="right", padx=T.px(6))
        self.btn_prev = W.PlayerButton(ctrl, "prev", command=self._prev, size=30, bg=T.PANEL)
        self.btn_prev.pack(side="right")

        # 音量
        vol = tk.Frame(top, bg=T.PANEL)
        vol.pack(side="right", padx=(0, T.px(14)))
        W.label(vol, "🔊", size=9, color=T.MUTED, bg=T.PANEL).pack(side="left", padx=(0, T.px(4)))
        self.volume = W.Slider(vol, value=self.player.volume, command=self._volume,
                               width=92, height=20, bg=T.PANEL)
        self.volume.pack(side="left")

        self.refresh()

    # -- 回调 -------------------------------------------------------
    def _toggle(self):
        self.player.toggle()
        self.refresh()

    def _next(self):
        self.player.next_track()
        self.refresh()

    def _prev(self):
        self.player.prev_track()
        self.refresh()

    def _volume(self, value: float):
        self.player.set_volume(value)

    def open_playlist(self):
        return PlaylistDialog(self.winfo_toplevel(), self.app, self)

    # -- 刷新 -------------------------------------------------------
    def refresh(self) -> None:
        p = self.player
        if not p.playlist:
            self.title_label.configure(text="背景音乐未设置")
            self.sub_label.configure(text="点击「播放列表」添加本地音乐，练习时更带感")
            self.btn_play.set_kind("play")
            self._draw_progress(0.0)
            return
        name = p.current_name
        self.title_label.configure(text=name)
        if p.error:
            sub = p.error
        elif p.playing and not p.paused:
            pos, length = p.position, p.length
            sub = f"正在播放 · {_fmt_time(pos)} / {_fmt_time(length)}" if length else "正在播放"
        elif p.paused:
            sub = "已暂停"
        else:
            sub = f"已就绪 · 共 {len(p.playlist)} 首"
        self.sub_label.configure(text=sub)
        self.btn_play.set_kind("pause" if (p.playing and not p.paused) else "play")
        length = p.length
        self._draw_progress((p.position / length) if length else 0.0)
        self.volume.set(p.volume)

    def _draw_progress(self, ratio: float) -> None:
        c = self.progress_line
        c.delete("all")
        w = c.winfo_width() or 1
        h = T.px(2)
        c.create_rectangle(0, 0, w, h, fill=T.PANEL, outline=T.PANEL)
        if ratio > 0:
            c.create_rectangle(0, 0, max(2, w * min(1.0, ratio)), h,
                               fill=T.mix(T.PANEL, T.ORANGE, 0.9), outline="")


class PlaylistDialog(tk.Toplevel):
    """播放列表管理：添加文件/文件夹、删除、清空、循环模式。"""

    def __init__(self, master, app, bar: MusicBar | None = None):
        super().__init__(master)
        self.app = app
        self.player = app.player
        self.bar = bar
        self.title("背景音乐")
        self.configure(bg=T.BG)
        self.resizable(False, False)
        w, h = T.px(620), T.px(560)
        self.geometry(f"{w}x{h}")
        self.transient(master.winfo_toplevel())
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self._build()
        self._center(master)
        self.refresh()
        self.bind("<Escape>", lambda e: self.close())

    def _center(self, master):
        self.update_idletasks()
        top = master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -- 界面 -------------------------------------------------------
    def _build(self):
        self.accent = tk.Frame(self, bg=T.ORANGE, height=T.px(3))
        self.accent.pack(fill="x")
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", padx=T.px(22), pady=(T.px(16), T.px(6)))
        W.label(head, "背景音乐", size=16, bold=True, color=T.TEXT).pack(side="left")
        self._count_label = W.label(head, f"共 {len(self.player.playlist)} 首", size=9,
                                    color=T.DIM, bg=T.BG)
        self._count_label.pack(side="left", padx=T.px(10), pady=(T.px(6), 0))
        close = W.Button(head, "关闭", command=self.close, kind="ghost", size="sm", bg=T.BG)
        close.pack(side="right")

        # 工具栏
        tools = tk.Frame(self, bg=T.BG)
        tools.pack(fill="x", padx=T.px(22), pady=(0, T.px(10)))
        W.Button(tools, "添加音乐", command=self._add_files, kind="primary", size="sm",
                 icon="＋", bg=T.BG).pack(side="left")
        W.Button(tools, "添加文件夹", command=self._add_folder, kind="soft", size="sm",
                 bg=T.BG).pack(side="left", padx=T.px(8))
        W.Button(tools, "移除选中", command=self._remove, kind="ghost", size="sm",
                 bg=T.BG).pack(side="left", padx=(T.px(8), 0))
        W.Button(tools, "清理失效", command=self._clean, kind="ghost", size="sm",
                 bg=T.BG).pack(side="left", padx=T.px(8))

        # 循环模式
        mode_row = tk.Frame(self, bg=T.BG)
        mode_row.pack(fill="x", padx=T.px(22), pady=(0, T.px(8)))
        W.label(mode_row, "循环方式", size=9, color=T.MUTED, bg=T.BG).pack(side="left",
                                                                           padx=(0, T.px(8)))
        self.mode_seg = W.Segmented(mode_row, LOOP_MODES,
                                    value=str(self.app.settings.get("music_loop_mode", "list")),
                                    command=self._set_mode, bg=T.BG, height=30, size=9)
        self.mode_seg.pack(side="left")
        W.Button(mode_row, "清空列表", command=self._clear, kind="danger", size="sm",
                 bg=T.BG).pack(side="right")

        # 列表
        wrap = tk.Frame(self, bg=T.BORDER)
        wrap.pack(fill="both", expand=True, padx=T.px(22), pady=(0, T.px(8)))
        self.list_frame = W.ScrollFrame(wrap, bg=T.CARD)
        self.list_frame.pack(fill="both", expand=True, padx=1, pady=1)
        self.rows_box = self.list_frame.body

        foot = tk.Frame(self, bg=T.BG)
        foot.pack(fill="x", padx=T.px(22), pady=(0, T.px(14)))
        self.hint = W.label(foot, "支持 mp3 / wav / ogg / flac / m4a，双击曲目立即播放",
                            size=8, color=T.DIM, bg=T.BG)
        self.hint.pack(side="left")
        self.vol_box = tk.Frame(foot, bg=T.BG)
        self.vol_box.pack(side="right")
        W.label(self.vol_box, "音量", size=8, color=T.DIM, bg=T.BG).pack(side="left",
                                                                        padx=(0, T.px(6)))
        self.volume = W.Slider(self.vol_box, value=self.player.volume, width=110, height=20,
                               command=lambda v: self.player.set_volume(v), bg=T.BG)
        self.volume.pack(side="left")

    # -- 操作 -------------------------------------------------------
    def _add_files(self):
        paths = filedialog.askopenfilenames(
            parent=self, title="选择音乐",
            filetypes=[("音频文件", "*.mp3 *.wav *.ogg *.flac *.m4a *.wma *.aac"),
                       ("所有文件", "*.*")])
        if not paths:
            return
        added, skipped = self.player.add_files(list(paths))
        self.refresh()
        if added and not self.player.playing:
            self.player.play_index(self.player.index)
        self._flash(f"已添加 {len(added)} 首" + (f"，跳过 {len(skipped)} 个" if skipped else ""))

    def _add_folder(self):
        folder = filedialog.askdirectory(parent=self, title="选择音乐文件夹")
        if not folder:
            return
        added, skipped = self.player.add_folder(folder)
        self.refresh()
        self._flash(f"从文件夹添加 {len(added)} 首" + (f"，跳过 {skipped} 个" if skipped else ""))

    def _selected_index(self) -> int | None:
        return getattr(self, "_sel", None)

    def _remove(self):
        idx = self._selected_index()
        if idx is None:
            self._flash("请先点击选中一首")
            return
        self.player.remove(idx)
        self._sel = None
        self.refresh()

    def _clean(self):
        removed = self.player.remove_missing()
        self.refresh()
        self._flash(f"清理了 {removed} 个失效文件" if removed else "没有失效文件")

    def _clear(self):
        if not self.player.playlist:
            return
        if messagebox.askyesno("清空列表", "确定清空全部背景音乐吗？（不会删除文件）", parent=self):
            self.player.clear()
            self._sel = None
            self.refresh()

    def _set_mode(self, value: str):
        self.app.settings["music_loop_mode"] = value
        self.app.settings.save()

    def _flash(self, text: str):
        self.hint.configure(text=text, fg=T.ORANGE)

    def _play_row(self, index: int):
        self.player.play_index(index)
        self._sel = index
        self.refresh()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    # -- 刷新 -------------------------------------------------------
    def refresh(self):
        W.clear(self.rows_box)
        tracks = self.player.tracks()
        if not tracks:
            empty = tk.Frame(self.rows_box, bg=T.CARD)
            empty.pack(fill="both", expand=True, pady=T.px(70))
            W.label(empty, "♪", size=26, color=T.BORDER_HI, bg=T.CARD).pack()
            W.label(empty, "还没有背景音乐", size=11, color=T.MUTED, bg=T.CARD).pack(pady=(T.px(6), 0))
            W.label(empty, "添加你喜欢的歌曲，练习时循环播放", size=9, color=T.DIM,
                    bg=T.CARD).pack()
        for idx, path in enumerate(tracks):
            self._make_row(idx, path)
        self.list_frame.attach(self.rows_box)
        self.list_frame._on_body()
        self.winfo_toplevel().after(30, self._sync_count)
        if self.volume:
            self.volume.set(self.player.volume)

    def _sync_count(self):
        try:
            self._count_label.configure(text=f"共 {len(self.player.playlist)} 首")
        except Exception:
            pass

    def _make_row(self, idx: int, path: Path):
        current = (idx == self.player.index)
        selected = (getattr(self, "_sel", None) == idx)
        bg = T.mix(T.CARD, T.ORANGE, 0.12) if current else (T.PANEL_2 if selected else T.CARD)
        row = tk.Frame(self.rows_box, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=T.px(12), pady=T.px(8))

        num = W.label(inner, "▶" if current else f"{idx + 1:02d}", size=9,
                      color=T.ORANGE if current else T.DIM, bg=bg, width=3)
        num.pack(side="left")
        info = tk.Frame(inner, bg=bg)
        info.pack(side="left", fill="x", expand=True)
        name = W.label(info, path.stem, size=10, bold=current,
                       color=T.TEXT if current else T.TEXT_SOFT, bg=bg)
        name.pack(anchor="w")
        sub = W.label(info, _short_dir(path.parent), size=8, color=T.DIM, bg=bg)
        sub.pack(anchor="w")
        status = W.label(inner, "播放中" if (current and self.player.playing and not self.player.paused)
                         else ("已暂停" if current and self.player.paused else ""),
                         size=8, color=T.ORANGE if current else T.DIM, bg=bg)
        status.pack(side="right")

        def on_enter(_e):
            if not current:
                for widget in (row, inner, info, name, sub, num, status):
                    widget.configure(bg=T.CARD_HOVER)

        def on_leave(_e):
            for widget in (row, inner, info, name, sub, num, status):
                widget.configure(bg=bg)

        def onclick(_e, index=idx):
            self._sel = index
            self.refresh()

        def on_double(_e, index=idx):
            self._play_row(index)

        for widget in (row, inner, info, name, sub, num, status):
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<Button-1>", onclick, add="+")
            widget.bind("<Double-Button-1>", on_double, add="+")
            widget.configure(cursor="hand2")

        tk.Frame(self.rows_box, bg=T.BORDER, height=1).pack(fill="x")
