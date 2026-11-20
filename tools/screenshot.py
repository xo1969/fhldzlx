"""开发用：启动界面、灌入示例数据并逐屏截图到 _shots/。"""
from __future__ import annotations

import os
import sys
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SHOTS = ROOT / "_shots"
PREVIEW = ROOT / "_preview_data"

os.environ["LOCALAPPDATA"] = str(PREVIEW / "local")
SHOTS.mkdir(exist_ok=True)
(PREVIEW / "local").mkdir(parents=True, exist_ok=True)

from PIL import ImageGrab  # noqa: E402

from app import audio  # noqa: E402
from app import engine as E  # noqa: E402
from app.main import App, enable_dpi_awareness  # noqa: E402

# (mode, lesson_id, title, chars, cpm, acc, grade, days_ago, minute)
SAMPLES = [
    ("en", "en_words_1", "常用单词 · 入门", 236, 214, 96.4, "A", 11, 21),
    ("en", "en_home_row", "基准键位", 252, 238, 98.1, "A", 9, 20),
    ("cn", "cn_sentences", "中文句子 · 日常", 118, 72, 95.3, "A", 8, 19),
    ("en", "en_sentences", "英文句子 · 日常", 204, 196, 94.2, "A", 6, 22),
    ("num", "num_digits", "数字键位", 188, 205, 97.5, "A", 5, 18),
    ("cn", "cn_phrases", "常用词组", 96, 61, 96.8, "B", 4, 20),
    ("en", "en_quotes", "名人名言", 178, 188, 96.9, "A", 3, 21),
    ("cn", "cn_poems", "古诗 · 经典", 82, 48, 92.4, "C", 2, 15),
    ("en", "en_articles", "英文短文 · 科技", 246, 172, 91.5, "C", 1, 16),
    ("cn", "cn_articles", "中文文章 · 阅读", 132, 66, 94.0, "B", 0, 20),
]


def seed_history(app) -> None:
    app.history.clear(None)
    for mode, lesson_id, title, chars, cpm, acc, grade, days, minute in SAMPLES:
        when = (datetime.now() - timedelta(days=days)).replace(
            hour=minute, minute=18, second=0, microsecond=0)
        app.history.add(
            mode=mode, lesson_id=lesson_id, lesson_title=title, chars=chars,
            correct=int(chars * acc / 100), wrong=max(0, chars - int(chars * acc / 100)),
            keystrokes=chars + 8, seconds=round(chars / cpm * 60, 1), cpm=cpm, wpm=cpm / 5,
            accuracy=acc, grade=grade, ts=when.isoformat(timespec="seconds"),
        )
    app.settings["last_session"] = {
        "lesson_id": "en_articles", "title": "英文短文 · 科技", "mode": "en", "cpm": 172,
    }
    app.settings["last_lesson"] = {"en": "en_articles", "cn": "cn_articles", "num": "num_digits"}
    app.settings.save()


def seed_music(app) -> None:
    folder = PREVIEW / "music"
    folder.mkdir(parents=True, exist_ok=True)
    names = ["云海之上（示例）", "风火轮（示例）", "莲花坞（示例）"]
    paths = []
    for i, name in enumerate(names):
        path = folder / f"{name}.wav"
        if not path.exists():
            data = audio.make_click_wav()
            data = data[:44] + data[44:] * (60 + i * 20)
            path.write_bytes(data)
        paths.append(str(path))
    app.player.add_files(paths)
    app.player.index = 0
    app.music_bar.refresh()


def main() -> None:
    enable_dpi_awareness()
    root = tk.Tk()
    app = App(root)
    root.attributes("-topmost", True)
    root.lift()
    root.update_idletasks()
    root.update()
    time.sleep(0.6)

    seed_history(app)
    seed_music(app)
    app.screens["home"].refresh()
    app.screens["stats"].refresh()

    def grab(name: str) -> None:
        root.update_idletasks()
        root.update()
        time.sleep(0.45)
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        w, h = root.winfo_width(), root.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img.save(SHOTS / f"{name}.png")
        print("shot", name, img.size)

    grab("01_home")

    app.show("stats")
    grab("02_stats")

    app.show("settings")
    grab("03_settings")

    app.start_practice(lesson_id="en_home_row")
    practice = app.screens["practice"]
    for ch in practice.session.text[:24]:
        practice._handle(ch)
    practice.session._t0 = E.now() - 6.3          # 24 字 / 6.3 秒 ≈ 228 cpm ≈ 46 WPM
    practice._update_stats()
    grab("04_practice_en")

    app.start_practice(lesson_id="cn_sentences")
    practice = app.screens["practice"]
    practice.cn_entry_var.set(practice.session.lines[0][:6])
    practice.session._t0 = E.now() - 6.0          # 6 字 / 6 秒 ≈ 60 字/分
    practice._update_stats()
    grab("05_practice_cn")

    app.start_practice(lesson_id="en_words_1")
    practice = app.screens["practice"]
    text = practice.session.text
    for ch in text[:-1]:
        practice._handle(ch)
    practice.session._t0 = E.now() - (len(text) / 270.0 * 60)   # ≈ 54 WPM
    practice._handle(text[-1])                     # 最后一字触发结算
    root.update()
    time.sleep(0.3)
    grab("06_result")

    def grab_window(win, name: str) -> None:
        win.update_idletasks()
        win.update()
        time.sleep(0.4)
        win.update()
        img = ImageGrab.grab(bbox=(win.winfo_rootx(), win.winfo_rooty(),
                                   win.winfo_rootx() + win.winfo_width(),
                                   win.winfo_rooty() + win.winfo_height()))
        img.save(SHOTS / f"{name}.png")
        print("shot", name, img.size)

    app.show("home")
    dialog = app.music_bar.open_playlist()
    grab_window(dialog, "07_playlist")
    dialog.close()

    box = app.screens["home"]._custom()
    box.text.insert("1.0", "风火轮转，键指生花。\n"
                           "每天练习十分钟，速度和准确率都会慢慢变好。\n"
                           "Practice makes progress, not perfect.")
    box._update_count()
    grab_window(box, "08_custom")
    box.destroy()

    help_box = app.show_help()
    grab_window(help_box, "09_help")
    help_box.close()

    root.attributes("-topmost", False)
    root.destroy()


if __name__ == "__main__":
    main()
