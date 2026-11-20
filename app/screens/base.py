"""屏幕基类。"""
from __future__ import annotations

import tkinter as tk

from .. import theme as T


class BaseScreen(tk.Frame):
    name = ""

    def __init__(self, app, master):
        super().__init__(master, bg=T.BG)
        self.app = app

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass
