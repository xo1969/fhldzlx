"""课程与文本装配：把 content_data 里的原始素材组装成一次练习的内容。

英文练习 = 一段连续文本（按长度截断到完整单词）
中文练习 = 若干短行（逐行输入，一行打完自动换行）
"""
from __future__ import annotations

import random
import re

from .config import LENGTH_PRESETS

try:  # 语料可能尚未生成：用兜底数据保证程序可运行
    from . import content_data as D
except Exception:  # pragma: no cover
    D = None


# ---------------------------------------------------------------- 兜底语料

def _fallback(name: str):
    data = {
        "EN_ALPHABET_DRILLS": ["asdf jkl; asdf jkl;", "qwer uiop qwer uiop", "zxcv m,./ zxcv m,./"],
        "EN_WORDS_1": ["time", "home", "water", "music", "light", "start", "green", "happy"],
        "EN_WORDS_2": ["because", "morning", "computer", "practice", "keyboard", "student"],
        "EN_SENTENCES": ["Practice makes perfect.", "The quick brown fox jumps over the lazy dog."],
        "EN_PARAGRAPHS": ["Typing well is a small skill with a large reward. It lets your "
                          "thoughts reach the page without a pause, and it turns a slow task "
                          "into a quiet pleasure. Keep your wrists light and your eyes ahead."],
        "EN_QUOTES": ["Practice makes perfect.", "Where there is a will there is a way."],
        "EN_NUMBERS": ["1234 5678 90", "314 271 141", "12+34=46"],
        "EN_SYMBOLS": ["()[]{} <> -=+_", "!@#$%^&*", "*/\\|'\";:"],
        "EN_CODE": ["def hello():", "    print('hi')", "for i in range(3):"],
        "CN_COMMON_CHARS": "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成",
        "CN_PHRASES": ["学习", "计算机", "风和日丽", "坚持不懈"],
        "CN_SENTENCES": ["今天天气很好，我们一起练习打字。", "熟能生巧，坚持就是胜利。"],
        "CN_ARTICLES": ["哪吒踏着风火轮飞过东海，浪花在他脚下翻涌。他大声说：" + "我命由我不由天。"],
        "CN_IDIOMS": ["一心一意", "持之以恒", "日新月异", "精益求精"],
        "CN_POEMS": ["床前明月光，疑是地上霜。举头望明月，低头思故乡。"],
    }
    return data.get(name, [])


def _source(name: str, default=None):
    if D is not None:
        value = getattr(D, name, None)
        if value:
            return value
    return _fallback(name) if default is None else default


# ---------------------------------------------------------------- 文本清洗

_CN_RE = re.compile(r"[\u4e00-\u9fff]")
_SENT_SPLIT_CN = re.compile(r"(?<=[。！？!?；;])")
_SENT_SPLIT_EN = re.compile(r"(?<=[.!?])\s+")
_SPACE_RE = re.compile(r"[ \t\u00a0]+")

_TRANS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
}


def normalize_text(text: str) -> str:
    """统一引号/破折号等常见“打不出来”的字符，压缩空白。"""
    if not text:
        return ""
    for src, dst in _TRANS.items():
        text = text.replace(src, dst)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def is_chinese(text: str) -> bool:
    return bool(_CN_RE.search(text or ""))


def split_chinese_lines(text: str, max_len: int = 34) -> list[str]:
    """把中文文本切成适合逐行输入的短行，尽量在标点处断开。"""
    text = normalize_text(text).strip()
    if not text:
        return []
    parts: list[str] = []
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        pieces = [p.strip() for p in _SENT_SPLIT_CN.split(chunk) if p.strip()]
        buf = ""
        for piece in pieces:
            if len(piece) > max_len:
                if buf:
                    parts.append(buf)
                    buf = ""
                for i in range(0, len(piece), max_len):
                    parts.append(piece[i:i + max_len])
            elif buf and len(buf) + len(piece) > max_len:
                parts.append(buf)
                buf = piece
            else:
                buf += piece
        if buf:
            parts.append(buf)
    return [p for p in parts if p]


def split_english_lines(text: str) -> str:
    """英文：规整空白，保持连续文本（交给界面自动换行）。"""
    text = normalize_text(text)
    text = _SPACE_RE.sub(" ", text.replace("\n", " "))
    return text.strip()


def _chunk_chars(chars: str, size: int = 20) -> list[str]:
    chars = "".join(ch for ch in chars if not ch.isspace())
    return [chars[i:i + size] for i in range(0, len(chars), size)]


def _english_piece(items: list[str], target: int, joiner: str = " ") -> str:
    """把若干素材拼成 ~target 字符的连续文本，结尾落在完整单词/句子处。"""
    if not items:
        return ""
    pool = list(items)
    out: list[str] = []
    total = 0
    while total < target and len(out) < 400:
        if not pool:
            pool = list(items)
        piece = pool.pop(0)
        piece = split_english_lines(piece) if "\n" in piece else _SPACE_RE.sub(" ", piece).strip()
        if not piece:
            continue
        if total + len(piece) > target + max(40, target // 3) and out:
            # 允许略微超出，但不要长太多
            break
        out.append(piece)
        total += len(piece) + len(joiner)
    text = joiner.join(out)
    return text.strip()


# ---------------------------------------------------------------- 课程定义

def _items(name: str) -> list[str]:
    raw = _source(name)
    return [str(x) for x in raw if str(x).strip()]


ALL_LESSONS: list[dict] = [
    # ------------------------------------------------------------ 英文
    {"id": "en_home_row", "category": "en", "engine": "en", "title": "基准键位",
     "desc": "ASDF JKL; 八个基准键，手指的家", "level": 1, "kind": "drill",
     "items": _items("EN_ALPHABET_DRILLS")[:24] or _items("EN_ALPHABET_DRILLS")},
    {"id": "en_letters", "category": "en", "engine": "en", "title": "字母综合",
     "desc": "26 个字母全键位循环练习", "level": 1, "kind": "drill",
     "items": _items("EN_ALPHABET_DRILLS")},
    {"id": "en_words_1", "category": "en", "engine": "en", "title": "常用单词",
     "desc": "三到五个字母的高频单词", "level": 2, "kind": "drill",
     "items": _items("EN_WORDS_1")},
    {"id": "en_words_2", "category": "en", "engine": "en", "title": "进阶单词",
     "desc": "六到十个字母的长单词", "level": 2, "kind": "drill",
     "items": _items("EN_WORDS_2")},
    {"id": "en_sentences", "category": "en", "engine": "en", "title": "英文短句",
     "desc": "带标点的完整句子，练习空格与大小写", "level": 2, "kind": "sentence",
     "items": _items("EN_SENTENCES")},
    {"id": "en_quotes", "category": "en", "engine": "en", "title": "名言谚语",
     "desc": "短小精悍的英文名言", "level": 3, "kind": "sentence",
     "items": _items("EN_QUOTES")},
    {"id": "en_articles", "category": "en", "engine": "en", "title": "英文文章",
     "desc": "成段落的长文，考验耐力", "level": 3, "kind": "article",
     "items": _items("EN_PARAGRAPHS")},
    {"id": "en_nezha", "category": "en", "engine": "en", "title": "哪吒传说",
     "desc": "用英文读哪吒的故事", "level": 3, "kind": "article",
     "items": (_items("EN_PARAGRAPHS")[:4] or _items("EN_PARAGRAPHS"))},

    # ------------------------------------------------------------ 数字符号
    {"id": "num_digits", "category": "num", "engine": "en", "title": "数字键位",
     "desc": "数字、小数与算式", "level": 1, "kind": "drill",
     "items": _items("EN_NUMBERS")},
    {"id": "num_symbols", "category": "num", "engine": "en", "title": "符号练习",
     "desc": "括号、运算符与标点", "level": 2, "kind": "drill",
     "items": _items("EN_SYMBOLS")},
    {"id": "num_code", "category": "num", "engine": "en", "title": "代码练习",
     "desc": "Python 代码片段，程序员专属", "level": 3, "kind": "code",
     "items": _items("EN_CODE"), "join": "\n"},

    # ------------------------------------------------------------ 中文
    {"id": "cn_chars", "category": "cn", "engine": "cn", "title": "常用单字",
     "desc": "400 个高频汉字，练熟输入法", "level": 1, "kind": "char",
     "items": _chunk_chars(_source("CN_COMMON_CHARS") if isinstance(_source("CN_COMMON_CHARS"), str)
                           else "".join(_source("CN_COMMON_CHARS")), 20)},
    {"id": "cn_phrases", "category": "cn", "engine": "cn", "title": "常用词组",
     "desc": "两到四字的日常词", "level": 1, "kind": "phrase",
     "items": _items("CN_PHRASES")},
    {"id": "cn_idioms", "category": "cn", "engine": "cn", "title": "四字成语",
     "desc": "成语连打，行云流水", "level": 2, "kind": "phrase",
     "items": _items("CN_IDIOMS")},
    {"id": "cn_sentences", "category": "cn", "engine": "cn", "title": "中文短句",
     "desc": "一句话一行，节奏轻快", "level": 2, "kind": "sentence",
     "items": _items("CN_SENTENCES")},
    {"id": "cn_poems", "category": "cn", "engine": "cn", "title": "古诗词",
     "desc": "唐诗名句，边练边背", "level": 2, "kind": "poem",
     "items": _items("CN_POEMS")},
    {"id": "cn_articles", "category": "cn", "engine": "cn", "title": "中文文章",
     "desc": "成段中文，练习长句连贯性", "level": 3, "kind": "article",
     "items": _items("CN_ARTICLES")},
    {"id": "cn_nezha", "category": "cn", "engine": "cn", "title": "哪吒闹海",
     "desc": "风火轮、混天绫，我命由我", "level": 3, "kind": "article",
     "items": (_items("CN_ARTICLES")[:4] or _items("CN_ARTICLES"))},
]

LESSON_MAP = {lesson["id"]: lesson for lesson in ALL_LESSONS}

CATEGORIES = [
    {"id": "en", "name": "英文打字", "subtitle": "字母 · 单词 · 句子 · 文章", "symbol": "A"},
    {"id": "cn", "name": "中文打字", "subtitle": "单字 · 词组 · 古诗 · 文章", "symbol": "中"},
    {"id": "num", "name": "数字符号", "subtitle": "数字 · 符号 · 代码", "symbol": "#"},
]

CATEGORY_NAMES = {c["id"]: c["name"] for c in CATEGORIES}


def lessons_of(category: str) -> list[dict]:
    return [lesson for lesson in ALL_LESSONS if lesson["category"] == category and lesson["items"]]


def get_lesson(lesson_id: str) -> dict | None:
    lesson = LESSON_MAP.get(lesson_id)
    if lesson and not lesson["items"]:
        return None
    return lesson


def random_lesson(category: str | None = None, level: int | None = None) -> dict:
    pool = [lesson for lesson in ALL_LESSONS if lesson["items"]]
    if category:
        pool = [lesson for lesson in pool if lesson["category"] == category]
    if level:
        pool = [lesson for lesson in pool if lesson["level"] == level]
    return random.choice(pool)


# ---------------------------------------------------------------- 组卷

def _cn_phrase_lines(items: list[str], target: int, per_line: int = 4) -> list[str]:
    pool = list(items)
    random.shuffle(pool)
    lines: list[str] = []
    total = 0
    guard = 0
    while total < target and guard < 200:
        guard += 1
        group = []
        while len(group) < per_line:
            if not pool:
                pool = list(items)
                random.shuffle(pool)
            group.append(pool.pop(0))
        line = "，".join(group) + "。"
        lines.append(line)
        total += len(line)
    return lines


def _cn_char_lines(items: list[str], target: int) -> list[str]:
    pool = list(items)
    random.shuffle(pool)
    lines: list[str] = []
    total = 0
    i = 0
    guard = 0
    while total < target and guard < 400:
        guard += 1
        if i >= len(pool):
            pool = list(items)
            random.shuffle(pool)
            i = 0
        if not pool:
            break
        line = pool[i]
        i += 1
        if not line.strip():
            continue
        lines.append(line)
        total += len(line)
    return lines


def _cn_sentence_lines(items: list[str], target: int) -> list[str]:
    pool = list(items)
    random.shuffle(pool)
    lines: list[str] = []
    total = 0
    i = 0
    guard = 0
    while total < target and guard < 400:
        guard += 1
        if i >= len(pool):
            pool = list(items)
            random.shuffle(pool)
            i = 0
        if not pool:
            break
        line = split_chinese_lines(pool[i], 60) or [pool[i]]
        for piece in line:
            lines.append(piece)
            total += len(piece)
            if total >= target:
                break
        i += 1
    return lines


def _cn_poem_lines(items: list[str], target: int) -> list[str]:
    pool = list(items)
    random.shuffle(pool)
    lines: list[str] = []
    total = 0
    i = 0
    guard = 0
    while total < target and guard < 200:
        guard += 1
        if i >= len(pool):
            pool = list(items)
            random.shuffle(pool)
            i = 0
        if not pool:
            break
        poem = normalize_text(pool[i]).strip()
        i += 1
        halves = [p for p in _SENT_SPLIT_CN.split(poem) if p.strip()]
        pairs = ["".join(halves[k:k + 2]) for k in range(0, len(halves), 2)]
        for pair in pairs:
            lines.append(pair)
            total += len(pair)
    return lines


def _cn_article_lines(items: list[str], target: int) -> list[str]:
    pool = list(items)
    random.shuffle(pool)
    lines: list[str] = []
    total = 0
    i = 0
    guard = 0
    while total < target and guard < 200:
        guard += 1
        if i >= len(pool):
            pool = list(items)
            random.shuffle(pool)
            i = 0
        if not pool:
            break
        article = pool[i]
        i += 1
        for line in split_chinese_lines(article, 36):
            lines.append(line)
            total += len(line)
            if total >= target:
                break
    return lines


def build_practice(lesson: dict, length: str = "medium", seed: int | None = None) -> dict:
    """组卷：返回 {'engine','mode','title','lesson_id','lines'/'text','total'}。"""
    if seed is not None:
        random.seed(seed)
    preset = LENGTH_PRESETS.get(length, LENGTH_PRESETS["medium"])
    items = [i for i in lesson.get("items") or [] if str(i).strip()]
    engine = lesson.get("engine", "en")
    category = lesson.get("category", engine)
    kind = lesson.get("kind", "sentence")

    if engine == "cn":
        target = preset["cn"]
        if kind == "char":
            lines = _cn_char_lines(items, target)
        elif kind == "phrase":
            lines = _cn_phrase_lines(items, target)
        elif kind == "poem":
            lines = _cn_poem_lines(items, target)
        elif kind == "article":
            lines = _cn_article_lines(items, target)
        else:
            lines = _cn_sentence_lines(items, target)
        lines = [ln for ln in lines if ln.strip()][:60]
        if not lines and items:
            lines = [items[0]]
        return {"engine": "cn", "mode": category, "title": lesson["title"],
                "lesson_id": lesson["id"], "lines": lines,
                "total": sum(len(ln) for ln in lines)}

    target = preset["en"]
    joiner = lesson.get("join", " ")
    if kind in ("drill", "sentence"):
        pool = list(items)
        random.shuffle(pool)
    else:
        pool = list(items)
        random.shuffle(pool)
    text = _english_piece(pool, target, joiner)
    if not text and items:
        text = str(items[0])
    if joiner == "\n":
        text = text.replace(" \n", "\n")
        total = len(text)
    else:
        total = len(text)
    return {"engine": "en", "mode": category, "title": lesson["title"],
            "lesson_id": lesson["id"], "text": text, "total": total}


def build_custom(raw: str, title: str = "自定义文本") -> dict | None:
    """把用户粘贴的文本变成一次练习。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    if is_chinese(raw):
        lines = split_chinese_lines(raw, 36)
        if not lines:
            return None
        return {"engine": "cn", "mode": "cn", "title": title, "lesson_id": "custom",
                "lines": lines[:80], "total": sum(len(ln) for ln in lines[:80])}
    text = split_english_lines(raw)
    if not text:
        return None
    return {"engine": "en", "mode": "en", "title": title, "lesson_id": "custom",
            "text": text[:2000], "total": len(text[:2000])}


def corpus_stats() -> dict:
    """语料统计，用于设置页「关于」。"""
    def count(name: str) -> int:
        value = _source(name, default=[])
        if isinstance(value, str):
            return len(value)
        try:
            return len(value)
        except TypeError:
            return 0

    cn_chars = _source("CN_COMMON_CHARS", default="")
    en_words = count("EN_WORDS_1") + count("EN_WORDS_2")
    cn_text = sum(len(x) for x in _source("CN_SENTENCES", default=[])) + \
        sum(len(x) for x in _source("CN_ARTICLES", default=[]))
    en_text = sum(len(x.split()) for x in _source("EN_PARAGRAPHS", default=[])) + \
        sum(len(x.split()) for x in _source("EN_SENTENCES", default=[]))
    return {"lessons": len([lesson for lesson in ALL_LESSONS if lesson["items"]]),
            "en_words": en_words, "en_text_words": en_text,
            "cn_chars": len(cn_chars) if isinstance(cn_chars, str) else 0,
            "cn_text": cn_text}
