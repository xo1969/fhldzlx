"""风火轮打字 —— 主窗口与页面调度。"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk

from . import audio
from . import config as CFG
from . import content as C
from . import theme as T
from . import widgets as W
from .db import History
from .music_ui import MusicBar
from .screens.home import HomeScreen
from .screens.practice import PracticeScreen
from .screens.settings import SettingsScreen
from .screens.stats import StatsScreen

NAV = [("home", "首页", "⌂"), ("stats", "统计", "▤"), ("settings", "设置", "⚙")]


def enable_dpi_awareness() -> None:
    """Windows 高分屏下避免界面被系统拉伸发虚。"""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _set_app_id() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{CFG.APP_EN}.Typing.1")
    except Exception:
        pass


class NavItem(tk.Frame):
    """左侧导航项：图标 + 文字 + 激活时的橙色竖条。"""

    def __init__(self, master, key: str, icon: str, text: str, command):
        super().__init__(master, bg=T.PANEL, height=T.px(42), cursor="hand2")
        self.pack_propagate(False)
        self.key = key
        self.command = command
        self.active = False
        self.bar = tk.Frame(self, bg=T.PANEL, width=T.px(3))
        self.bar.pack(side="left", fill="y", pady=T.px(7))
        self.inner = tk.Frame(self, bg=T.PANEL)
        self.inner.pack(side="left", fill="both", expand=True, padx=T.px(12))
        self.icon_label = W.label(self.inner, icon, size=12, color=T.MUTED, bg=T.PANEL)
        self.icon_label.pack(side="left", padx=(0, T.px(10)))
        self.text_label = W.label(self.inner, text, size=10, color=T.TEXT_SOFT, bg=T.PANEL)
        self.text_label.pack(side="left")
        for item in (self, self.inner, self.icon_label, self.text_label):
            item.bind("<Button-1>", self._click)
            item.bind("<Enter>", self._enter)
            item.bind("<Leave>", self._leave)

    def _click(self, _event=None):
        self.command(self.key)

    def _paint(self, bg: str, color: str) -> None:
        for widget in (self, self.inner):
            widget.configure(bg=bg)
        self.icon_label.configure(bg=bg, fg=color)
        self.text_label.configure(bg=bg, fg=color)

    def _enter(self, _event=None):
        if not self.active:
            self._paint(T.CARD, T.TEXT)

    def _leave(self, _event=None):
        if not self.active:
            self._paint(T.PANEL, T.TEXT_SOFT)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.bar.configure(bg=T.ORANGE if active else T.PANEL)
        if active:
            self._paint(T.CARD, T.ORANGE)
        else:
            self._paint(T.PANEL, T.TEXT_SOFT)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"{CFG.APP_NAME} · 中英文打字练习")
        root.configure(bg=T.BG)
        self.settings = CFG.Settings()
        T.init(root, float(self.settings.get("ui_scale", 1.0)))
        T.setup_ttk(root)
        self.history = History(CFG.user_dir() / "history.db")
        self.sounds = audio.SoundBank(float(self.settings.get("sound_volume", 0.45)))
        self.player = audio.MusicPlayer(self.settings, on_change=self._on_music_change)
        self.player.set_volume(float(self.settings.get("music_volume", 0.45)), persist=False)
        self.screens: dict[str, tk.Frame] = {}
        self.current_name = ""
        self._toast_label: tk.Label | None = None
        self._toast_job = None

        self._build_shell()
        self._build_sidebar()
        self._build_music_bar()
        self._build_screens()
        self.show("home")
        self._restore_geometry()
        self._bind_shortcuts()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._tick()
        root.after(700, self._autoplay_music)

    # ------------------------------------------------------------ 界面缩放
    def apply_ui_scale(self, scale: float) -> None:
        """切换整个界面的字号/间距缩放，立即重建界面（当前页保留）。"""
        try:
            scale = max(0.85, min(1.30, round(float(scale), 2)))
        except (TypeError, ValueError):
            return
        if abs(scale - T.get_scale()) < 0.01:
            return
        if self.current_name == "practice":
            self.toast("练习中不能调整界面大小，退出本局后再试")
            return
        self.settings["ui_scale"] = scale
        self.settings.save()
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        name = self.current_name or "home"
        self._dismiss_toast()
        geom = self.root.geometry()
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.screens = {}
        self.nav_items = {}
        self.music_bar = None  # type: ignore[assignment]
        self.current_name = None
        T.init(self.root, float(self.settings.get("ui_scale", 1.0)))
        T.setup_ttk(self.root)
        self._build_shell()
        self._build_sidebar()
        self._build_music_bar()
        self._build_screens()
        self.show(name)
        self.root.minsize(T.px(1020), T.px(660))
        try:
            width = int(geom.split("+")[0].split("x")[0])
            height = int(geom.split("+")[0].split("x")[1])
        except (IndexError, ValueError):
            width = height = 0
        try:
            width = max(width, T.px(1020) + T.px(16))
            height = max(height, T.px(660) + T.px(48))
            self.root.geometry(f"{width}x{height}")
        except tk.TclError:
            pass

    # ------------------------------------------------------------ 布局
    def _build_shell(self) -> None:
        self.shell = tk.Frame(self.root, bg=T.BG)
        self.shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(self.shell, bg=T.PANEL, width=T.px(188))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Frame(self.shell, bg=T.BORDER, width=1).pack(side="left", fill="y")
        self.right = tk.Frame(self.shell, bg=T.BG)
        self.right.pack(side="left", fill="both", expand=True)
        # stack 不在这里 pack：必须等音乐条先占据底部，否则内容页会把音乐条挤成 0 高
        self.stack = tk.Frame(self.right, bg=T.BG)

    def _build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=T.PANEL, height=T.px(96))
        brand.pack(fill="x", pady=(T.px(10), 0))
        brand.pack_propagate(False)
        emblem = tk.Canvas(brand, width=T.px(46), height=T.px(46), bg=T.PANEL,
                           highlightthickness=0, bd=0)
        emblem.pack(side="left", padx=(T.px(16), T.px(10)))
        emblem.create_oval(1, 1, T.px(45), T.px(45),
                           fill=T.mix(T.PANEL, T.ORANGE, 0.24),
                           outline=T.mix(T.PANEL, T.ORANGE, 0.7))
        emblem.create_text(T.px(23), T.px(24), text="风", fill=T.ORANGE,
                           font=T.font(17, bold=True, cn=True))
        text_box = tk.Frame(brand, bg=T.PANEL)
        text_box.pack(side="left")
        W.label(text_box, CFG.APP_NAME, size=13, bold=True, bg=T.PANEL).pack(anchor="w")
        W.label(text_box, CFG.APP_EN.upper(), size=7, color=T.MUTED, bg=T.PANEL).pack(
            anchor="w")

        self.nav_items: dict[str, NavItem] = {}
        nav_box = tk.Frame(self.sidebar, bg=T.PANEL)
        nav_box.pack(fill="x", pady=(T.px(10), 0))
        for key, text, icon in NAV:
            item = NavItem(nav_box, key, icon, text, self.show)
            item.pack(fill="x", padx=T.px(10), pady=T.px(2))
            self.nav_items[key] = item

        footer = tk.Frame(self.sidebar, bg=T.PANEL)
        footer.pack(side="bottom", fill="x", pady=T.px(14), padx=T.px(16))
        self.music_hint = W.label(footer, "♫ 背景音乐未设置", size=8, color=T.DIM,
                                  bg=T.PANEL, wraplength=T.px(150))
        self.music_hint.pack(anchor="w")
        help_btn = W.Button(footer, "F1 帮助", command=lambda: self.show_help(),
                            kind="link", size="xs", bg=T.PANEL)
        help_btn.pack(anchor="w", pady=(T.px(2), 0))
        W.label(footer, f"v{CFG.VERSION}", size=7, color=T.DIM, bg=T.PANEL).pack(
            anchor="w", pady=(T.px(4), 0))

    def _build_music_bar(self) -> None:
        self.music_bar = MusicBar(self.right, self)
        self.music_bar.pack(side="bottom", fill="x")
        self.stack.pack(fill="both", expand=True)

    def _build_screens(self) -> None:
        for cls in (HomeScreen, PracticeScreen, StatsScreen, SettingsScreen):
            screen = cls(self, self.stack)
            self.screens[screen.name] = screen

    # ------------------------------------------------------------ 导航
    def show(self, name: str) -> None:
        if name not in self.screens:
            return
        if name == self.current_name:
            screen = self.screens[name]
            if screen.winfo_ismapped():
                if hasattr(screen, "refresh"):
                    screen.refresh()
                return
        if self.current_name:
            old = self.screens[self.current_name]
            old.on_hide()
            old.pack_forget()
        screen = self.screens[name]
        screen.pack(fill="both", expand=True)
        screen.on_show()
        self.current_name = name
        for key, item in self.nav_items.items():
            item.set_active(key == name)
        if name == "practice":
            self.music_hint.configure(text="Esc 返回首页")
        else:
            self.music_hint.configure(text=self._music_hint_text())

    # ------------------------------------------------------------ 练习
    def start_practice(self, lesson_id: str | None = None, plan: dict | None = None,
                       category: str | None = None) -> None:
        if plan is None:
            lesson = None
            if lesson_id:
                lesson = C.get_lesson(lesson_id)
            elif category:
                lesson = C.random_lesson(category, None)
            if lesson is None:
                lesson = C.random_lesson()
            if lesson is None:
                self.toast("没有可用的练习内容")
                return
            plan = C.build_practice(lesson, str(self.settings.get("practice_length", "medium")))
        if not plan or not plan.get("total"):
            self.toast("这门课程的语料还没准备好")
            return
        self.show("practice")
        self.screens["practice"].load_plan(plan)

    def random_practice(self, category: str | None = None) -> None:
        self.start_practice(category=category or str(self.settings.get("last_category", "en")))

    def refresh_screens(self) -> None:
        for name in ("home", "stats"):
            screen = self.screens.get(name)
            if screen is not None and name == self.current_name and hasattr(screen, "refresh"):
                screen.refresh()

    # ------------------------------------------------------------ 辅助
    def _music_hint_text(self) -> str:
        name = self.player.current_name
        if not name:
            return "♫ 背景音乐未设置"
        state = "▶" if self.player.playing else ("⏸" if self.player.paused else "♫")
        return f"{state} {name}"

    def _on_music_change(self) -> None:
        try:
            self.music_bar.refresh()
            if self.current_name != "practice":
                self.music_hint.configure(text=self._music_hint_text())
        except Exception:
            pass

    def _tick(self) -> None:
        try:
            self.player.tick()
            if self.player.playing:
                self.music_bar.refresh()
        except Exception:
            pass
        self.root.after(500, self._tick)

    def _autoplay_music(self) -> None:
        if not self.player.playlist:
            return
        if not self.settings.get("music_enabled", True):
            return
        if self.player.available and not self.player.playing:
            self.player.play_index()

    def toast(self, message: str, ms: int = 2200) -> None:
        if self._toast_job:
            try:
                self.root.after_cancel(self._toast_job)
            except Exception:
                pass
            self._toast_job = None
        if self._toast_label is not None:
            self._toast_label.destroy()
        label = tk.Label(self.root, text=message, fg=T.TEXT, bg=T.PANEL_2,
                         font=T.font(10), padx=T.px(18), pady=T.px(9),
                         bd=0, highlightthickness=1, highlightbackground=T.BORDER_HI)
        label.place(relx=0.5, rely=1.0, y=-T.px(88), anchor="s")
        label.lift()
        self._toast_label = label
        self._toast_job = self.root.after(ms, self._dismiss_toast)

    def _dismiss_toast(self) -> None:
        self._toast_job = None
        if self._toast_label is not None:
            self._toast_label.destroy()
            self._toast_label = None

    def show_help(self):
        from .help_ui import open_help
        return open_help(self)

    # ------------------------------------------------------------ 窗口
    def _restore_geometry(self) -> None:
        geometry = str(self.settings.get("window_geometry") or "")
        self.root.minsize(T.px(1020), T.px(660))
        if geometry and "x" in geometry:
            try:
                self.root.geometry(geometry)
                if str(self.settings.get("window_state", "normal")) == "zoomed":
                    self.root.state("zoomed")
                return
            except Exception:
                pass
        width, height = T.px(1220), T.px(800)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - T.px(20))
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Key-1>", lambda e: self.show("home"))
        self.root.bind("<Control-Key-2>", lambda e: self.show("stats"))
        self.root.bind("<Control-Key-3>", lambda e: self.show("settings"))
        self.root.bind("<F1>", lambda e: self.show_help())
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.root.bind(seq, lambda e: self._zoom_ui(+0.1))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.root.bind(seq, lambda e: self._zoom_ui(-0.1))
        self.root.bind("<Control-Key-0>", lambda e: self.apply_ui_scale(1.0))

    def _zoom_ui(self, delta: float) -> None:
        self.apply_ui_scale(T.get_scale() + delta)

    def close(self) -> None:
        try:
            state = self.root.state()
            self.settings["window_state"] = "zoomed" if state == "zoomed" else "normal"
            if state == "normal":
                self.settings["window_geometry"] = self.root.geometry()
        except Exception:
            pass
        self.settings.save()
        try:
            self.player.close()
        except Exception:
            pass
        try:
            self.history.close()
        except Exception:
            pass
        self.root.destroy()


def main() -> None:
    enable_dpi_awareness()
    _set_app_id()
    root = tk.Tk()
    root.withdraw()
    App(root)
    root.deiconify()
    icon = CFG.assets_dir() / "logo.png"
    if icon.exists():
        try:
            photo = tk.PhotoImage(file=str(icon))
            root.iconphoto(True, photo)
            root._icon_ref = photo  # type: ignore[attr-defined]
        except Exception:
            pass
    ico = CFG.assets_dir() / "icon.ico"
    if ico.exists() and sys.platform.startswith("win"):
        try:
            root.iconbitmap(str(ico))
        except Exception:
            pass
    root.mainloop()


if __name__ == "__main__":
    main()
