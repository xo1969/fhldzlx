"""开发期冒烟测试：不启动窗口，检查模块导入与基础逻辑。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, content, db, engine, audio  # noqa: E402


def test_engine_en():
    s = engine.EnglishSession("hello world", strict=True)
    for ch in "hello":
        s.handle_key(ch)
    assert s.pos == 5, s.pos
    assert s.done_chars == 5
    # 错误按键不前进
    r = s.handle_key("x")
    assert r.kind == "bad" and s.pos == 5
    # 退格
    s.handle_key("\b")
    assert s.pos == 4
    assert s.errors == 1
    for ch in "o world":
        s.handle_key(ch)
    assert s.finished, "should finish"
    assert s.accuracy < 100
    print("  en strict ok:", round(s.cpm, 1), "cpm", round(s.accuracy, 1), "%")


def test_engine_en_nonstrict():
    s = engine.EnglishSession("abc", strict=False)
    s.handle_key("a")
    s.handle_key("x")   # 错误前进
    assert s.pos == 2 and s.bad_count == 1
    s.handle_key("\b")
    s.handle_key("b")
    s.handle_key("c")
    assert s.finished, "non-strict finish after fixing"
    print("  en non-strict ok")


def test_engine_cn():
    s = engine.ChineseSession(["你好世界。", "第二行。"])
    r = s.update_input("你好")
    assert s.matched == 2 and not r.line_completed
    r = s.update_input("你好世界。")
    assert r.line_completed and s.line_index == 1 and s.buf == ""
    assert s.completed_chars == 5
    s.update_input("第二")
    assert s.done_chars == 5 + 2
    s.update_input("第二行。")
    assert s.finished
    print("  cn ok: done", s.done_chars, "/", s.total_chars, "acc", round(s.accuracy, 1))


def test_engine_cn_error():
    s = engine.ChineseSession(["abcdef"])
    s.update_input("ab")
    s.update_input("abX")   # 错一个字
    assert s.matched == 2
    assert s.errors == 1
    s.update_input("abc")   # 退格重打
    assert s.matched == 3
    print("  cn error ok")


def test_db():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        h = db.History(Path(tmp) / "t.db")
        h.add(mode="en", lesson_title="t", chars=100, correct=100, wrong=0,
              keystrokes=100, seconds=60, cpm=100, wpm=20, accuracy=100, grade="S")
        h.add(mode="en", lesson_title="t", chars=50, correct=50, wrong=2,
              keystrokes=52, seconds=60, cpm=50, wpm=10, accuracy=96, grade="B")
        s = h.summary()
        assert s["count"] == 2 and abs(s["avg_cpm"] - 75) < 0.01, s
        assert abs(s["best_cpm"] - 100) < 0.01
        assert len(h.recent(5)) == 2
        assert len(h.timeline(5)) == 2
        assert len(h.daily(7)) == 7
        assert 0 <= h.rank(100, "en") <= 100
        h.close()
        print("  db ok", s)


def test_content():
    print("  corpus:", content.corpus_stats())
    for cat in ("en", "cn", "num"):
        lessons = content.lessons_of(cat)
        assert lessons, cat
        for lesson in lessons:
            for length in ("short", "medium", "long"):
                plan = content.build_practice(lesson, length, seed=1)
                if plan["engine"] == "cn":
                    assert plan["lines"], lesson["id"]
                    text = "".join(plan["lines"])
                else:
                    assert plan["text"].strip(), lesson["id"]
                    text = plan["text"]
                assert len(text) > 20, (lesson["id"], length, len(text))
    custom = content.build_custom("这是一段自定义中文文本。\n第二行内容。")
    assert custom and custom["engine"] == "cn" and len(custom["lines"]) == 2, custom
    custom2 = content.build_custom("Hello there. How are you?")
    assert custom2 and custom2["engine"] == "en", custom2
    print("  content ok:", len(content.ALL_LESSONS), "lessons")


def test_audio_assets():
    click = audio.make_click_wav()
    assert click[:4] == b"RIFF" and len(click) > 1000
    print("  audio wav ok:", len(click), "bytes")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(name)
            fn()
    print("ALL SMOKE TESTS PASSED")
