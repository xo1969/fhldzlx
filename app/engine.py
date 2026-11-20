"""打字核心引擎：与界面无关的纯逻辑，便于单元测试。

英文模式：逐键捕获（严格模式下打错不前进，可退格）。
中文模式：输入框文本与目标行逐字比对（兼容输入法整段上屏），一行完成自动进入下一行。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

# 字符状态
PENDING, OK, BAD = 0, 1, 2


def now() -> float:
    return time.perf_counter()


class StatsMixin:
    """计时、暂停与速度/正确率快照。"""

    def _init_stats(self) -> None:
        self._t0: float | None = None
        self._paused_at: float | None = None
        self._paused_total = 0.0
        self.keystrokes = 0
        self.correct_keystrokes = 0
        self.errors = 0
        self.finished = False
        self._last_key_at: float | None = None
        self.intervals: list[float] = []

    # -- 计时 -------------------------------------------------------
    def start(self) -> None:
        if self._t0 is None:
            self._t0 = now()

    def pause(self) -> None:
        if self._t0 is not None and self._paused_at is None and not self.finished:
            self._paused_at = now()

    def resume(self) -> None:
        if self._paused_at is not None:
            self._paused_total += now() - self._paused_at
            self._paused_at = None

    @property
    def paused(self) -> bool:
        return self._paused_at is not None

    @property
    def elapsed(self) -> float:
        if self._t0 is None:
            return 0.0
        end = self._paused_at if self._paused_at is not None else now()
        return max(0.0, end - self._t0 - self._paused_total)

    # -- 统计 -------------------------------------------------------
    @property
    def minutes(self) -> float:
        return max(self.elapsed, 0.001) / 60.0

    def _note_key(self) -> None:
        t = now()
        if self._last_key_at is not None and not self.paused:
            gap = t - self._last_key_at
            if 0 < gap < 3.0:
                self.intervals.append(gap)
                if len(self.intervals) > 60:
                    del self.intervals[: len(self.intervals) - 60]
        self._last_key_at = t

    @property
    def cpm(self) -> float:
        if self.elapsed < 0.2:
            return 0.0
        return self.done_chars / self.minutes

    @property
    def wpm(self) -> float:
        return self.cpm / 5.0

    @property
    def accuracy(self) -> float:
        if self.keystrokes <= 0:
            return 100.0
        return self.correct_keystrokes / self.keystrokes * 100.0

    @property
    def peak_cpm(self) -> float:
        """按最近 10 次击键的间隔估算峰值速度。"""
        if len(self.intervals) < 5:
            return 0.0
        recent = self.intervals[-10:]
        avg_gap = sum(recent) / len(recent)
        if avg_gap <= 0:
            return 0.0
        return 60.0 / avg_gap

    def snapshot(self) -> dict:
        return {
            "cpm": self.cpm,
            "wpm": self.wpm,
            "accuracy": self.accuracy,
            "elapsed": self.elapsed,
            "keystrokes": self.keystrokes,
            "errors": self.errors,
            "done": self.done_chars,
            "total": self.total_chars,
            "progress": self.progress,
        }

    @property
    def progress(self) -> float:
        total = self.total_chars
        return 0.0 if total <= 0 else min(1.0, self.done_chars / total)


# ---------------------------------------------------------------- 结果对象

@dataclass
class KeyResult:
    """一次按键处理后的增量信息，供界面局部刷新。"""

    index: int = 0            # 当前字符下标
    kind: str = "none"        # ok | bad | back | none | reset
    line: int = 0             # 当前行号（中文模式）
    line_completed: bool = False
    finished: bool = False


# ---------------------------------------------------------------- 英文

class EnglishSession(StatsMixin):
    """英文连续打字。text 为整篇目标文本。"""

    def __init__(self, text: str, strict: bool = True):
        self.text = text
        self.strict = strict
        self.states = [PENDING] * len(text)
        self.pos = 0
        self.bad_index: int | None = None
        self.ok_count = 0
        self.bad_count = 0
        self._newlines = text.count("\n")
        self._init_stats()
        self._advance_newlines()
        if not text or self.pos >= len(text):
            self.finished = True

    # -- 属性 -------------------------------------------------------
    @property
    def total_chars(self) -> int:
        return max(0, len(self.text) - self._newlines)

    def _advance_newlines(self) -> None:
        """跳过目标文本里的换行：代码练习等按行显示的文本不需要手动敲回车。"""
        while self.pos < len(self.text) and self.text[self.pos] == "\n":
            self.states[self.pos] = OK
            self.pos += 1

    @property
    def done_chars(self) -> int:
        return self.ok_count

    @property
    def progress(self) -> float:
        total = self.total_chars
        return 0.0 if total <= 0 else min(1.0, self.done_chars / total)

    @property
    def done(self) -> bool:
        if self.finished:
            return True
        if not self.text:
            return True
        return self.pos >= len(self.text)

    @property
    def current_line(self) -> int:
        return 0

    # -- 输入 -------------------------------------------------------
    def handle_key(self, ch: str) -> KeyResult:
        if self.finished:
            return KeyResult(index=self.pos, kind="none", finished=True)
        if not ch:
            return KeyResult(index=self.pos, kind="none")
        self.start()
        self.resume()
        self._advance_newlines()
        res = KeyResult(index=self.pos, kind="none")

        if ch in ("\r", "\n"):
            # 目标在换行处时，回车也可以主动跳过
            if self.pos < len(self.text) and self.text[self.pos] == "\n":
                self._advance_newlines()
                res.kind = "ok"
                res.index = self.pos
                res.line_completed = True
            return res

        if ch == "\b":
            if self.pos > 0:
                # 先跨过自动跳过的换行，再撤销上一行最后一个字符
                while self.pos > 0 and self.text[self.pos - 1] == "\n":
                    self.pos -= 1
                    self.states[self.pos] = PENDING
                if self.pos > 0:
                    self.pos -= 1
                    if self.states[self.pos] == OK:
                        self.ok_count -= 1
                    elif self.states[self.pos] == BAD:
                        self.bad_count -= 1
                    self.states[self.pos] = PENDING
                self.bad_index = None
                res.kind = "back"
                res.index = self.pos
                self._note_key()
            return res

        if self.pos >= len(self.text):
            return res

        self.keystrokes += 1
        self._note_key()
        expected = self.text[self.pos]
        if ch == expected:
            self.states[self.pos] = OK
            self.ok_count += 1
            self.correct_keystrokes += 1
            self.pos += 1
            self._advance_newlines()
            self.bad_index = None
            res.kind = "ok"
        else:
            self.errors += 1
            if self.strict:
                self.bad_index = self.pos
                res.kind = "bad"
            else:
                self.states[self.pos] = BAD
                self.bad_count += 1
                self.pos += 1
                self._advance_newlines()
                self.bad_index = self.pos - 1
                res.kind = "bad"

        if self.done:
            self.finished = True
            res.line_completed = True
            res.finished = True
        res.index = self.pos
        return res

    def skip_char(self) -> KeyResult:
        """跳过当前字符（输入法无法输入的字符等）。"""
        self._advance_newlines()
        if self.pos >= len(self.text):
            return KeyResult(index=self.pos)
        self.states[self.pos] = OK
        self.ok_count += 1
        self.pos += 1
        self._advance_newlines()
        if self.done:
            self.finished = True
        return KeyResult(index=self.pos, kind="ok", finished=self.finished)


# ---------------------------------------------------------------- 中文

class ChineseSession(StatsMixin):
    """中文逐行打字：一行打完自动换行，兼容输入法整段上屏。"""

    def __init__(self, lines: list[str]):
        self.lines = [ln for ln in (lines or []) if ln]
        self.line_index = 0
        self.buf = ""
        self.line_count = len(self.lines)
        self._init_stats()
        if not self.lines:
            self.finished = True
        self.completed_chars = 0  # 已完成行的字符总数

    # -- 属性 -------------------------------------------------------
    @property
    def total_chars(self) -> int:
        return sum(len(ln) for ln in self.lines)

    @property
    def current_line(self) -> int:
        return min(self.line_index, max(0, len(self.lines) - 1))

    @property
    def line_text(self) -> str:
        if not self.lines:
            return ""
        return self.lines[min(self.line_index, len(self.lines) - 1)]

    @property
    def matched(self) -> int:
        """当前行已正确匹配的前缀长度。"""
        line = self.line_text
        n = 0
        limit = min(len(self.buf), len(line))
        while n < limit and self.buf[n] == line[n]:
            n += 1
        return n

    @property
    def done_chars(self) -> int:
        if self.finished:
            return self.total_chars
        return self.completed_chars + self.matched

    @property
    def progress(self) -> float:
        total = self.total_chars
        return 0.0 if total <= 0 else min(1.0, self.done_chars / total)

    @property
    def line_progress(self) -> float:
        line = self.line_text
        return 0.0 if not line else min(1.0, self.matched / len(line))

    # -- 输入 -------------------------------------------------------
    def update_input(self, text: str) -> KeyResult:
        """输入框内容变化后调用；返回需要刷新的行信息。"""
        if self.finished:
            return KeyResult(index=0, line=self.current_line, finished=True)
        prev = self.buf
        self.buf = text
        res = KeyResult(index=self.matched, line=self.current_line)
        if text and not text.startswith(prev[: len(text)]) and text != prev:
            pass  # 选择替换等异常情况：只按最终前缀计算
        # 新增字符计数
        if len(text) > len(prev):
            self.start()
            self.resume()
            line = self.line_text
            for i in range(len(prev), len(text)):
                ch = text[i]
                self.keystrokes += 1
                self._note_key()
                if i < len(line) and ch == line[i] and (i == 0 or text[:i] == line[:len(text[:i])]):
                    self.correct_keystrokes += 1
                else:
                    self.errors += 1
        res.index = self.matched

        # 整行完成 -> 自动进入下一行
        if self.line_text and self.buf == self.line_text:
            self.completed_chars += len(self.line_text)
            self.line_index += 1
            self.buf = ""
            res.line_completed = True
            res.index = 0
            res.line = self.current_line
            if self.line_index >= len(self.lines):
                self.finished = True
                self.completed_chars = self.total_chars
                res.finished = True
        return res

    def skip_line(self) -> KeyResult:
        """跳过当前行（不计入正确字符）。"""
        if self.finished:
            return KeyResult(finished=True)
        self.line_index += 1
        self.buf = ""
        res = KeyResult(index=0, line=self.current_line, kind="reset", line_completed=True)
        if self.line_index >= len(self.lines):
            self.finished = True
            res.finished = True
            self.completed_chars = self.total_chars
        return res

    def jump_line(self, index: int) -> KeyResult:
        """跳转到指定行（点击行号）。"""
        if not self.lines:
            return KeyResult()
        index = max(0, min(index, len(self.lines) - 1))
        self.completed_chars = sum(len(ln) for ln in self.lines[:index])
        self.line_index = index
        self.buf = ""
        if self.finished and index < len(self.lines):
            self.finished = False
        return KeyResult(index=0, line=index, kind="reset")


# ---------------------------------------------------------------- 评级

GRADE_TABLE = {
    # 英文按字符/分钟（1 词≈5 字符）：S≥250(50 WPM)、A≥190、B≥140、C≥90
    "en": [(250, "S", "神速"), (190, "A", "优秀"), (140, "B", "良好"), (90, "C", "及格"), (0, "D", "加油")],
    # 中文按字/分钟：S≥100、A≥75、B≥52、C≥32
    "cn": [(100, "S", "神速"), (75, "A", "优秀"), (52, "B", "良好"), (32, "C", "及格"), (0, "D", "加油")],
}


def grade_for(mode: str, cpm: float) -> tuple[str, str]:
    table = GRADE_TABLE.get("cn" if str(mode).startswith("cn") else "en")
    for threshold, letter, label in table:
        if cpm >= threshold:
            return letter, label
    return "D", "加油"


def speed_label(mode: str) -> str:
    return "字/分" if str(mode).startswith("cn") else "WPM"


def speed_for(mode: str, cpm: float) -> tuple[float, str]:
    """把统一的「字符/分钟」换算成该模式习惯的展示数值与单位。"""
    m = str(mode or "")
    if m.startswith("cn"):
        return cpm, "字/分"
    if m == "num":
        return cpm, "字符/分"
    if m == "en":
        return cpm / 5.0, "WPM"
    return cpm, "字符/分"


def format_clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
