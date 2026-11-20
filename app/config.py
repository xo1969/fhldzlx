"""风火轮打字 —— 全局配置、路径与设置持久化。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "风火轮打字"
APP_EN = "Firewheel"
DATA_DIR = "FirewheelTyping"
VERSION = "1.0.0"
TAGLINE = "风火轮转，键指生花"

# ---------------------------------------------------------------- 路径


def resource_dir() -> Path:
    """程序资源目录（源码运行 = 项目根目录；打包运行 = 解包临时目录）。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return Path(base)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """可执行文件所在目录（用于放启动脚本、示例音乐等）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return resource_dir() / "assets"


def user_dir() -> Path:
    """用户数据目录：设置、历史成绩、导入的音乐清单。"""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    candidates = []
    if base:
        candidates.append(Path(base) / DATA_DIR)
    candidates.append(app_dir() / "userdata")
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return path
        except Exception:
            continue
    return Path.cwd()


# ---------------------------------------------------------------- 设置

DEFAULT_SETTINGS: dict = {
    "font_scale": 1.0,          # 目标文本字号倍率
    "target_font_size": 26,     # 英文目标字号（中文自动 +4）
    "ui_scale": 1.0,            # 整个界面（字体与间距）缩放：0.9 / 1.0 / 1.1 / 1.2
    "music_volume": 0.45,
    "music_enabled": True,      # 首次进入练习自动播放
    "music_loop_mode": "list",  # list | one | shuffle
    "playlist": [],             # 绝对路径列表
    "playlist_index": 0,
    "sound_enabled": True,      # 击键音效
    "sound_volume": 0.45,
    "strict_mode": True,        # 严格模式：打错不前进
    "show_keyboard": True,      # 显示虚拟键盘
    "practice_length": "medium",  # short | medium | long
    "last_category": "en",      # 首页选中的分类
    "last_lesson": {"en": "en_home_row", "cn": "cn_sentences", "num": "num_digits"},
    "last_session": {},         # 最近一次练习 {lesson_id, title, mode, cpm}
    "window_geometry": "",
    "window_state": "normal",
    "hide_nav_hints": False,
    "playlist_panel_open": False,
}

LENGTH_PRESETS = {
    "short": {"en": 240, "cn": 160, "label": "短"},
    "medium": {"en": 460, "cn": 300, "label": "中"},
    "long": {"en": 760, "cn": 520, "label": "长"},
}


class Settings:
    """简单的 JSON 设置存储，读取时始终带默认值兜底。"""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else user_dir() / "settings.json"
        self.data: dict = dict(DEFAULT_SETTINGS)
        self.data["playlist"] = []
        self.data["last_lesson"] = dict(DEFAULT_SETTINGS["last_lesson"])
        self.data["last_session"] = {}
        self.load()

    # -- 读写 -------------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if key in DEFAULT_SETTINGS:
                        if key == "last_lesson" and isinstance(value, dict):
                            merged = dict(DEFAULT_SETTINGS["last_lesson"])
                            merged.update({k: v for k, v in value.items() if isinstance(v, str)})
                            self.data[key] = merged
                        elif key == "last_session" and isinstance(value, dict):
                            merged = dict(DEFAULT_SETTINGS["last_session"])
                            merged.update({k: v for k, v in value.items()
                                           if isinstance(v, (str, int, float))})
                            self.data[key] = merged
                        elif key == "playlist" and isinstance(value, list):
                            self.data[key] = [p for p in value if isinstance(p, str)]
                        elif isinstance(value, type(DEFAULT_SETTINGS[key])) or value is None:
                            self.data[key] = value
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    # -- 访问 -------------------------------------------------------
    def __getitem__(self, key: str):
        return self.data.get(key, DEFAULT_SETTINGS.get(key))

    def __setitem__(self, key: str, value) -> None:
        self.data[key] = value

    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULT_SETTINGS.get(key, default))

    def update(self, **kwargs) -> None:
        self.data.update(kwargs)

    # -- 便捷 -------------------------------------------------------
    @property
    def target_font_size(self) -> int:
        base = int(self.data.get("target_font_size", 26))
        scale = float(self.data.get("font_scale", 1.0))
        return max(14, min(56, int(round(base * scale))))

    def practice_chars(self) -> int:
        preset = LENGTH_PRESETS.get(str(self.data.get("practice_length")), LENGTH_PRESETS["medium"])
        return preset
