"""成绩数据库：SQLite 保存每一次练习，提供汇总、排行与趋势数据。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .config import user_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    mode         TEXT NOT NULL,
    lesson_id    TEXT,
    lesson_title TEXT,
    chars        INTEGER NOT NULL DEFAULT 0,
    correct      INTEGER NOT NULL DEFAULT 0,
    wrong        INTEGER NOT NULL DEFAULT 0,
    keystrokes   INTEGER NOT NULL DEFAULT 0,
    seconds      REAL NOT NULL DEFAULT 0,
    cpm          REAL NOT NULL DEFAULT 0,
    wpm          REAL NOT NULL DEFAULT 0,
    accuracy     REAL NOT NULL DEFAULT 0,
    grade        TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_ts ON sessions(ts);
CREATE INDEX IF NOT EXISTS idx_sessions_mode ON sessions(mode);
"""


class History:
    """练习历史。所有方法都在调用线程内同步执行（界面为单线程 Tk）。"""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else user_dir() / "history.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ------------------------------------------------------------------
    def add(self, *, mode: str, lesson_id: str = "", lesson_title: str = "",
            chars: int = 0, correct: int = 0, wrong: int = 0, keystrokes: int = 0,
            seconds: float = 0.0, cpm: float = 0.0, wpm: float = 0.0,
            accuracy: float = 100.0, grade: str = "", ts: str | None = None) -> int:
        ts = ts or datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO sessions (ts, mode, lesson_id, lesson_title, chars, correct, wrong,"
            " keystrokes, seconds, cpm, wpm, accuracy, grade)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, mode, lesson_id, lesson_title, int(chars), int(correct), int(wrong),
             int(keystrokes), float(seconds), round(float(cpm), 2), round(float(wpm), 2),
             round(float(accuracy), 2), grade),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # ------------------------------------------------------------------
    def recent(self, limit: int = 20, mode: str | None = None) -> list[dict]:
        sql = "SELECT * FROM sessions"
        args: list = []
        if mode:
            sql += " WHERE mode = ?"
            args.append(mode)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        return [dict(row) for row in self.conn.execute(sql, args)]

    def summary(self, mode: str | None = None) -> dict:
        where, args = ("WHERE mode = ?", [mode]) if mode else ("", [])
        row = self.conn.execute(
            f"SELECT COUNT(*) AS n, COALESCE(SUM(seconds),0) AS secs, COALESCE(SUM(chars),0) AS chars,"
            f" COALESCE(AVG(cpm),0) AS avg_cpm, COALESCE(MAX(cpm),0) AS best_cpm,"
            f" COALESCE(AVG(accuracy),0) AS avg_acc, COALESCE(AVG(seconds),0) AS avg_secs"
            f" FROM sessions {where}", args).fetchone()
        data = dict(row) if row else {}
        return {
            "count": int(data.get("n") or 0),
            "seconds": float(data.get("secs") or 0),
            "chars": int(data.get("chars") or 0),
            "avg_cpm": float(data.get("avg_cpm") or 0),
            "best_cpm": float(data.get("best_cpm") or 0),
            "avg_accuracy": float(data.get("avg_acc") or 0),
            "avg_seconds": float(data.get("avg_secs") or 0),
            "avg_wpm": float(data.get("avg_cpm") or 0) / 5,
            "best_wpm": float(data.get("best_cpm") or 0) / 5,
        }

    def best(self, mode: str, field: str = "cpm") -> float:
        if field not in ("cpm", "wpm", "accuracy"):
            field = "cpm"
        row = self.conn.execute(
            f"SELECT COALESCE(MAX({field}),0) AS v FROM sessions WHERE mode = ?", (mode,)).fetchone()
        return float(row["v"]) if row else 0.0

    def by_mode(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT mode, COUNT(*) AS n, AVG(cpm) AS avg_cpm, MAX(cpm) AS best_cpm,"
            " AVG(accuracy) AS avg_acc FROM sessions GROUP BY mode ORDER BY n DESC").fetchall()
        return [dict(r) for r in rows]

    def timeline(self, limit: int = 20, mode: str | None = None) -> list[dict]:
        rows = self.recent(limit, mode)
        return list(reversed(rows))

    def daily(self, days: int = 14) -> list[dict]:
        """最近 N 天每天的平均速度与练习次数（用于趋势图）。"""
        today = datetime.now().date()
        start = today - timedelta(days=days - 1)
        rows = self.conn.execute(
            "SELECT substr(ts,1,10) AS day, AVG(cpm) AS avg_cpm, COUNT(*) AS n"
            " FROM sessions WHERE substr(ts,1,10) >= ? GROUP BY day", (start.isoformat(),)).fetchall()
        found = {r["day"]: r for r in rows}
        out = []
        for i in range(days):
            day = (start + timedelta(days=i)).isoformat()
            row = found.get(day)
            out.append({"day": day,
                        "avg_cpm": float(row["avg_cpm"]) if row else 0.0,
                        "n": int(row["n"]) if row else 0})
        return out

    def rank(self, cpm: float, mode: str) -> float:
        """本次速度击败了历史多少比例的练习（0~100）。"""
        row = self.conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN cpm < ? THEN 1 ELSE 0 END),0) AS lower"
            " FROM sessions WHERE mode = ?", (float(cpm), mode)).fetchone()
        if not row or row["n"] <= 0:
            return 0.0
        return row["lower"] / row["n"] * 100.0

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
        return int(row["n"]) if row else 0

    def clear(self, mode: str | None = None) -> None:
        if mode:
            self.conn.execute("DELETE FROM sessions WHERE mode = ?", (mode,))
        else:
            self.conn.execute("DELETE FROM sessions")
        self.conn.commit()

    def delete(self, session_id: int) -> None:
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (int(session_id),))
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
