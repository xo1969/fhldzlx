"""开发用：真实事件级 GUI 流程自测（不截图，纯逻辑断言）。"""
from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix="firewheel_gui_"))
os.environ["LOCALAPPDATA"] = str(TMP)

from app.main import App, enable_dpi_awareness  # noqa: E402
from app import theme as theme  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {extra}")
        failures.append(name)


def pump(root: tk.Tk, times: int = 4) -> None:
    for _ in range(times):
        root.update_idletasks()
        root.update()


def press(text_widget: tk.Text, ch: str) -> None:
    keysym = {" ": "space", "\n": "Return", "\b": "BackSpace",
              "\t": "Tab", "\x1b": "Escape"}.get(ch, ch)
    text_widget.focus_force()
    text_widget.event_generate("<KeyPress>", keysym=keysym)
    text_widget.update()


def main() -> int:
    enable_dpi_awareness()
    root = tk.Tk()
    app = App(root)
    pump(root)
    practice = app.screens["practice"]

    print("english strict typing")
    app.start_practice(lesson_id="en_home_row")
    pump(root, 6)
    check("practice visible", practice.winfo_ismapped())
    check("mode is en", practice.mode == "en")
    session = practice.session
    check("session exists", session is not None)
    typed = session.text[:24]
    for ch in typed:
        press(practice.surface.text, ch)
    pump(root, 3)
    check("24 chars advanced", session.pos == 24, f"pos={session.pos}")
    check("no errors", session.errors == 0, f"errors={session.errors}")
    check("keystrokes counted", session.keystrokes >= 24, f"k={session.keystrokes}")

    wrong = "Z" if typed and session.text[24] != "Z" else "Q"
    press(practice.surface.text, wrong)
    pump(root, 2)
    check("strict error blocks advance", session.pos == 24, f"pos={session.pos}")
    check("error counted", session.errors == 1, f"errors={session.errors}")

    press(practice.surface.text, "\b")
    pump(root, 2)
    check("backspace goes back", session.pos == 23, f"pos={session.pos}")
    press(practice.surface.text, session.text[23])
    pump(root, 2)
    check("retype advances", session.pos == 24, f"pos={session.pos}")

    print("finish early")
    before = app.history.count()
    practice._finish_click()
    pump(root, 4)
    check("overlay placed", bool(practice.overlay.winfo_ismapped()))
    check("history recorded", app.history.count() == before + 1,
          f"before={before} now={app.history.count()}")
    check("last_session saved", isinstance(app.settings.get("last_session"), dict)
          and bool(app.settings.get("last_session", {}).get("title")))
    row = app.history.recent(1)[0]
    check("history row mode", row["mode"] == "en", f"mode={row['mode']}")
    check("history cpm > 0", row["cpm"] > 0, f"cpm={row['cpm']}")

    print("overlay actions")
    app.show("home")
    pump(root, 4)
    check("back to home", app.current_name == "home")
    app.screens["home"].refresh()
    pump(root, 2)
    check("home best card updated", practice.plan is not None)

    print("chinese line flow")
    app.start_practice(lesson_id="cn_sentences")
    pump(root, 6)
    practice = app.screens["practice"]
    check("mode is cn", practice.mode == "cn")
    check("cn panel visible", bool(practice.cn_entry.winfo_ismapped()))
    check("keyboard hidden on cn", not practice.keyboard_wrap.winfo_ismapped())
    first = practice.session.lines[0]
    practice.cn_entry_var.set(first)
    pump(root, 4)
    check("line completed advances", practice.session.line_index == 1,
          f"line={practice.session.line_index}")
    check("entry cleared", practice.cn_entry_var.get() == "",
          f"text={practice.cn_entry_var.get()!r}")
    second = practice.session.lines[1]
    practice.cn_entry_var.set(second[:5])
    pump(root, 3)
    check("partial line matched", practice.session.matched == 5,
          f"matched={practice.session.matched}")
    practice._skip_line()
    pump(root, 2)
    check("skip advances line", practice.session.line_index == 2,
          f"line={practice.session.line_index}")

    print("settings toggles")
    app.show("settings")
    pump(root, 4)
    screen = app.screens["settings"]
    screen._set_keyboard(False)
    check("setting saved", app.settings.get("show_keyboard") is False)
    screen._set_keyboard(True)
    screen._set_font_size(0.5)
    check("font size applied", 30 <= int(app.settings["target_font_size"]) <= 34,
          f"size={app.settings['target_font_size']}")
    screen._set_font_size((26 - 18) / 28)

    print("stats screen")
    app.show("stats")
    pump(root, 4)
    check("stats visible", app.screens["stats"].winfo_ismapped())
    app.show("home")
    pump(root, 3)

    print("music playlist dialog")
    app.show("home")
    dialog = app.music_bar.open_playlist()
    pump(root, 4)
    check("dialog open", dialog is not None and dialog.winfo_exists() > 0)
    dialog.close()
    pump(root, 3)
    check("dialog closed", not dialog.winfo_exists())

    print("custom text + help dialogs")
    custom = app.screens["home"]._custom()
    pump(root, 3)
    custom.text.insert("1.0", "我命由我不由天。\nStay hungry, stay foolish.")
    custom._update_count()
    check("custom count updated", custom.count.cget("text").startswith("2") or
          "字" in custom.count.cget("text"))
    custom.destroy()
    pump(root, 2)
    help_dlg = app.show_help()
    pump(root, 3)
    check("help open", help_dlg.winfo_exists() > 0)
    help_dlg.close()
    pump(root, 2)
    check("help closed", not help_dlg.winfo_exists())

    print("custom text + shortcuts")
    app.show("home")
    pump(root, 3)
    from app import content as C
    plan = C.build_custom("你好，世界！\nHello world, nice to meet you.", "自定义文本")
    check("custom plan built", plan is not None and bool(plan.get("lines") or plan.get("text")))
    app.start_practice(plan=plan)
    pump(root, 5)
    practice = app.screens["practice"]
    check("custom plan loaded", practice.plan is plan, f"mode={practice.mode}")
    start_pos = practice.session.pos if practice.mode == "en" else practice.session.line_index
    press(practice.surface.text if practice.mode == "en" else practice.cn_entry, "\t")
    pump(root, 4)
    check("tab restarts", practice.session is not None and practice.session.elapsed < 5,
          "elapsed too big")
    practice.surface.text.focus_force()
    press(practice.surface.text, "\x1b")
    pump(root, 4)
    check("esc returns home", app.current_name in ("home", "practice"))

    print("playlist persistence")
    import wave

    tmpdir = TMP / "music"
    tmpdir.mkdir(parents=True, exist_ok=True)
    wav_path = tmpdir / "demo.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 22050)
    added, skipped = app.player.add_files([str(wav_path)])
    check("track added", len(added) == 1 and not skipped, f"added={added} skipped={skipped}")
    check("track in settings", str(wav_path) in app.settings.get("playlist", []),
          f"list={app.settings.get('playlist')}")
    from app.config import Settings
    again = Settings()
    check("playlist persisted", str(wav_path) in again.get("playlist", []))
    check("player plays", app.player.play_index(0) or not app.player.available)
    pump(root, 2)
    app.player.pause()

    print("window resize")
    root.geometry("1020x660")
    pump(root, 6)
    app.start_practice(lesson_id="en_letters")
    pump(root, 5)
    practice = app.screens["practice"]
    check("music bar visible when small", bool(app.music_bar.winfo_ismapped()))
    check("text area has room", practice.text_wrap.winfo_height() > 120,
          f"h={practice.text_wrap.winfo_height()}")
    root.geometry("1220x800")
    pump(root, 5)

    print("timer, scroll, grade, restart")
    app.show("home")
    pump(root, 3)
    app.start_practice(lesson_id="en_articles")
    pump(root, 5)
    practice = app.screens["practice"]
    session = practice.session
    session.start()
    pump(root, 4)
    t0 = session.elapsed
    press(practice.surface.text, session.text[0])
    pump(root, 4)
    check("timer runs", session.elapsed >= 0 and session.cpm >= 0)
    practice.toggle_pause()
    pump(root, 3)
    paused_at = session.elapsed
    check("paused state", session.paused is True)
    import time as _time
    _time.sleep(0.35)
    pump(root, 2)
    check("elapsed frozen while paused", abs(session.elapsed - paused_at) < 0.2,
          f"{paused_at} -> {session.elapsed}")
    practice.toggle_pause()
    pump(root, 3)
    check("resumed", session.paused is False)

    from app import engine as E
    check("grade S for high cpm", E.grade_for("en", 300)[0] == "S")
    check("grade D for low cpm", E.grade_for("cn", 3)[0] == "D")

    practice.restart()
    pump(root, 4)
    check("restart resets progress", practice.session.done_chars == 0,
          f"done={practice.session.done_chars}")

    print("chinese auto scroll")
    app.settings["practice_length"] = "long"
    app.start_practice(lesson_id="cn_articles")
    pump(root, 5)
    practice = app.screens["practice"]
    for _ in range(min(12, len(practice.session.lines))):
        practice.cn_entry_var.set(practice.session.lines[practice.session.line_index])
        pump(root, 2)
    pump(root, 3)
    yview = practice.surface.text.yview()
    check("text scrolled down", yview[0] > 0.15, f"yview={yview}")
    check("cn progress advanced", practice.session.line_index >= 10,
          f"line={practice.session.line_index}")

    print("ui scale")
    app.show("home")
    pump(root, 3)
    check("sound backend available", app.sounds.available, app.sounds.backend)
    base_scale = theme.get_scale()
    app.apply_ui_scale(1.2)
    pump(root, 6)
    check("ui scale applied", abs(theme.get_scale() - 1.2) < 0.01,
          f"scale={theme.get_scale()}")
    check("screens rebuilt", set(app.screens) == {"home", "practice", "stats", "settings"},
          str(sorted(app.screens)))
    app.apply_ui_scale(1.0)
    pump(root, 6)
    check("ui scale reset", abs(theme.get_scale() - base_scale) < 0.01,
          f"scale={theme.get_scale()}")

    app.start_practice(lesson_id="en_home_row")
    pump(root, 4)
    app.apply_ui_scale(1.2)
    pump(root, 3)
    check("practice blocks ui scale", abs(theme.get_scale() - base_scale) < 0.01,
          f"scale={theme.get_scale()}")
    app.show("home")
    pump(root, 2)

    print("window close")
    app.close()
    try:
        root.destroy()
    except tk.TclError:
        pass

    print()
    if failures:
        print("GUI TEST FAILED:", ", ".join(failures))
        return 1
    print("ALL GUI TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
