"""音频：背景音乐播放器（pygame 优先，Windows MCI 兜底）与键盘音效。

设计原则：
* 没有 pygame 也能跑（纯 tkinter + winmm）；两者都不可用时静默降级，不影响打字练习。
* 背景音乐支持 mp3 / wav / ogg / flac（pygame）以及 mp3 / wav / wma（MCI）。
"""
from __future__ import annotations

import ctypes
import io
import math
import os
import random
import struct
import wave
from ctypes import wintypes
from pathlib import Path

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".wma", ".opus", ".aif", ".aiff"}
MCI_EXTS = {".mp3", ".wav", ".wma", ".mid", ".midi"}

# ---------------------------------------------------------------- 波形工具


def _wav_bytes(samples: list[float], rate: int = 44100, stereo: bool = True) -> bytes:
    """把 -1..1 的浮点采样编码为 16bit WAV 字节。"""
    frames = bytearray()
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32000)
        packed = struct.pack("<h", v)
        frames += packed
        if stereo:
            frames += packed
    channels = 2 if stereo else 1
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _click_wave(rate: int = 44100) -> list[float]:
    """短促的机械键盘敲击感：噪声 + 快速衰减。"""
    n = int(rate * 0.045)
    out = []
    rng = random.Random(7)
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 90)
        noise = (rng.random() * 2 - 1) * 0.55
        tone = math.sin(2 * math.pi * 1750 * t) * 0.45 + math.sin(2 * math.pi * 620 * t) * 0.25
        out.append((noise + tone) * env * 0.5)
    return out


def _error_wave(rate: int = 44100) -> list[float]:
    n = int(rate * 0.16)
    out = []
    for i in range(n):
        t = i / rate
        env = math.exp(-t * 16) * min(1.0, t * 60)
        v = math.sin(2 * math.pi * 190 * t) * 0.5 + math.sin(2 * math.pi * 95 * t) * 0.3
        out.append(v * env * 0.55)
    return out


def _finish_wave(rate: int = 44100) -> list[float]:
    notes = [523.25, 659.25, 783.99, 1046.5]
    out: list[float] = []
    for idx, freq in enumerate(notes):
        dur = 0.16 if idx < 3 else 0.5
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            env = min(1.0, t * 120) * math.exp(-t * (7 if idx < 3 else 3.2))
            v = math.sin(2 * math.pi * freq * t) * 0.5 + math.sin(2 * math.pi * freq * 2 * t) * 0.12
            out.append(v * env * 0.42)
    # 尾巴淡出
    tail = int(rate * 0.12)
    out.extend([0.0] * tail)
    return out


def make_click_wav() -> bytes:
    return _wav_bytes(_click_wave())


def make_error_wav() -> bytes:
    return _wav_bytes(_error_wave())


def make_finish_wav() -> bytes:
    return _wav_bytes(_finish_wave())


# ---------------------------------------------------------------- 音效

class SoundBank:
    """键音。pygame.mixer 优先；没有时退回 winsound（临时 WAV 文件 + 异步播放）。"""

    def __init__(self, volume: float = 0.45):
        self.volume = max(0.0, min(1.0, float(volume)))
        self.backend = "none"
        self._pygame = None
        self._sounds: dict[str, object] = {}
        self._winsound = None
        self._wav_files: dict[str, str] = {}
        self._wavs = {
            "click": make_click_wav(),
            "error": make_error_wav(),
            "finish": make_finish_wav(),
        }

        try:
            import pygame
            if not pygame.mixer.get_init():
                # 首次使用时主动初始化混音器（否则按键音会静默失败）
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if pygame.mixer.get_init():
                pygame.mixer.set_num_channels(16)
                self._pygame = pygame.mixer
                self.backend = "pygame"
                for key, data in self._wavs.items():
                    # 交给 pygame 解析 WAV 头并自动转换成当前混音器格式
                    self._sounds[key] = self._pygame.Sound(file=io.BytesIO(data))
                self.apply_volume()
        except Exception:
            self._pygame = None
            self._sounds.clear()
            self.backend = "none"

        if self.backend == "none":
            try:
                import tempfile
                import winsound

                folder = Path(tempfile.gettempdir()) / "firewheel_typing_sfx"
                folder.mkdir(parents=True, exist_ok=True)
                for key, data in self._wavs.items():
                    path = folder / f"{key}.wav"
                    if not path.exists() or path.read_bytes() != data:
                        path.write_bytes(data)
                    self._wav_files[key] = str(path)
                self._winsound = winsound
                self.backend = "winsound"
            except Exception:
                self._winsound = None

    def apply_volume(self) -> None:
        if self.backend == "pygame":
            base = {"click": 0.9, "error": 1.0, "finish": 1.0}
            for key, snd in self._sounds.items():
                try:
                    snd.set_volume(max(0.0, min(1.0, self.volume * base.get(key, 1.0))))
                except Exception:
                    pass

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
        self.apply_volume()

    def play(self, key: str = "click") -> None:
        if self.volume <= 0.001:
            return
        if self.backend == "pygame":
            snd = self._sounds.get(key)
            if snd is not None:
                try:
                    snd.play()
                except Exception:
                    pass
        elif self.backend == "winsound" and self._winsound is not None:
            # winsound 的 SND_MEMORY 与 SND_ASYNC 不能同时使用，改用临时文件异步播放
            path = self._wav_files.get(key)
            if path:
                try:
                    self._winsound.PlaySound(
                        path,
                        self._winsound.SND_FILENAME | self._winsound.SND_ASYNC
                        | self._winsound.SND_NODEFAULT,
                    )
                except Exception:
                    pass

    @property
    def available(self) -> bool:
        return self.backend != "none"


# ---------------------------------------------------------------- 音乐后端

class PygameBackend:
    name = "pygame"

    def __init__(self):
        import pygame
        self.pg = pygame
        self._path = ""
        self._length = 0.0
        self._paused = False

    def load(self, path: str) -> None:
        music = self.pg.mixer.music
        try:
            music.stop()
        except Exception:
            pass
        music.load(str(path))
        self._path = str(path)
        self._length = self._probe_length(path)

    def _probe_length(self, path: str) -> float:
        low = str(path).lower()
        if low.endswith(".wav"):
            try:
                with wave.open(str(path), "rb") as w:
                    rate = w.getframerate() or 44100
                    return w.getnframes() / float(rate)
            except Exception:
                return 0.0
        return 0.0

    def play(self, loop: bool = False) -> None:
        self.pg.mixer.music.play(-1 if loop else 0)
        self._paused = False

    def pause(self) -> None:
        self.pg.mixer.music.pause()
        self._paused = True

    def unpause(self) -> None:
        self.pg.mixer.music.unpause()
        self._paused = False

    def stop(self) -> None:
        try:
            self.pg.mixer.music.stop()
        except Exception:
            pass
        self._paused = False

    def set_volume(self, volume: float) -> None:
        try:
            self.pg.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        except Exception:
            pass

    @property
    def busy(self) -> bool:
        try:
            return bool(self.pg.mixer.music.get_busy())
        except Exception:
            return False

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def position(self) -> float:
        try:
            return self.pg.mixer.music.get_pos() / 1000.0
        except Exception:
            return 0.0

    @property
    def length(self) -> float:
        return self._length


class MCIBackend:
    """Windows MCI：支持 mp3 / wav / wma，无第三方依赖。"""

    name = "mci"

    def __init__(self):
        self.winmm = ctypes.WinDLL("winmm")
        self.winmm.mciSendStringW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                                             wintypes.UINT, wintypes.HWND]
        self.winmm.mciSendStringW.restype = wintypes.DWORD
        self.alias = "nzmusic"
        self._open = False
        self._length = 0.0
        self._paused = False
        self._volume = 1.0

    def _mci(self, cmd: str) -> tuple[int, str]:
        buf = ctypes.create_unicode_buffer(512)
        code = self.winmm.mciSendStringW(cmd, buf, 512, None)
        return int(code), buf.value.strip()

    def _close_alias(self) -> None:
        if self._open:
            self._mci(f"close {self.alias}")
            self._open = False

    def load(self, path: str) -> None:
        self._close_alias()
        ext = Path(path).suffix.lower()
        device = {".mp3": "mpegvideo", ".wma": "mpegvideo", ".mid": "sequencer",
                  ".midi": "sequencer"}.get(ext, "waveaudio")
        code, _ = self._mci(f'open "{path}" type {device} alias {self.alias}')
        if code != 0:
            code, _ = self._mci(f'open "{path}" alias {self.alias}')
        if code != 0:
            raise OSError(f"MCI 无法打开音频文件（错误码 {code}）")
        self._open = True
        code, value = self._mci(f"status {self.alias} length")
        try:
            self._length = int(value) / 1000.0 if code == 0 and value.isdigit() else 0.0
        except Exception:
            self._length = 0.0
        self._mci(f"setaudio {self.alias} volume to {int(self._volume * 1000)}")

    def play(self, loop: bool = False) -> None:
        if not self._open:
            return
        self._mci(f"seek {self.alias} to start")
        self._mci(f"play {self.alias}" + (" repeat" if loop else ""))
        self._paused = False

    def pause(self) -> None:
        if self._open:
            self._mci(f"pause {self.alias}")
            self._paused = True

    def unpause(self) -> None:
        if self._open:
            self._mci(f"resume {self.alias}")
            self._paused = False

    def stop(self) -> None:
        if self._open:
            self._mci(f"stop {self.alias}")
            self._mci(f"seek {self.alias} to start")
            self._paused = False

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        if self._open:
            self._mci(f"setaudio {self.alias} volume to {int(self._volume * 1000)}")

    @property
    def busy(self) -> bool:
        if not self._open:
            return False
        code, value = self._mci(f"status {self.alias} mode")
        return code == 0 and value in ("playing", "paused")

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def position(self) -> float:
        if not self._open:
            return 0.0
        code, value = self._mci(f"status {self.alias} position")
        try:
            return int(value) / 1000.0 if code == 0 and value.isdigit() else 0.0
        except Exception:
            return 0.0

    @property
    def length(self) -> float:
        return self._length


def create_music_backend():
    """优先 pygame（格式支持更全），退回 Windows MCI。"""
    try:
        import pygame
        if pygame.mixer.get_init():
            return PygameBackend()
    except Exception:
        pass
    try:
        return MCIBackend()
    except Exception:
        return None


# ---------------------------------------------------------------- 播放器

class MusicPlayer:
    """播放列表管理 + 自动切歌。tick() 由界面定时器驱动。"""

    def __init__(self, settings, on_change=None):
        self.settings = settings
        self.on_change = on_change or (lambda: None)
        self.backend = create_music_backend()
        self.playing = False
        self.paused = False
        self.error = ""
        self.current_path = ""
        self._pending_next = False
        self.playlist: list[str] = []
        self.index = 0
        self._load_playlist()

    # -- 列表 -------------------------------------------------------
    def _load_playlist(self) -> None:
        raw = self.settings.get("playlist") or []
        self.playlist = [str(p) for p in raw if isinstance(p, str) and Path(p).is_file()]
        try:
            self.index = int(self.settings.get("playlist_index") or 0)
        except Exception:
            self.index = 0
        if self.playlist:
            self.index %= len(self.playlist)
        else:
            self.index = 0

    def _persist(self) -> None:
        self.settings["playlist"] = list(self.playlist)
        self.settings["playlist_index"] = int(self.index)
        self.settings.save()

    def tracks(self) -> list[Path]:
        return [Path(p) for p in self.playlist]

    @property
    def available(self) -> bool:
        return self.backend is not None

    @property
    def current_name(self) -> str:
        if not self.playlist:
            return ""
        return Path(self.playlist[self.index % len(self.playlist)]).stem

    @property
    def current_dir(self) -> str:
        if not self.playlist:
            return ""
        return str(Path(self.playlist[self.index % len(self.playlist)]).parent)

    def add_files(self, paths: list[str]) -> tuple[list[str], list[str]]:
        added, skipped = [], []
        existing = {os.path.normcase(os.path.abspath(p)) for p in self.playlist}
        for p in paths:
            if not p:
                continue
            path = os.path.abspath(p)
            if not os.path.isfile(path) or Path(path).suffix.lower() not in AUDIO_EXTS:
                skipped.append(path)
                continue
            key = os.path.normcase(path)
            if key in existing:
                skipped.append(path)
                continue
            existing.add(key)
            self.playlist.append(path)
            added.append(path)
        if added:
            self._persist()
            self.on_change()
        return added, skipped

    def add_folder(self, folder: str, recursive: bool = True) -> tuple[list[str], int]:
        files: list[str] = []
        try:
            base = Path(folder)
            it = base.rglob("*") if recursive else base.glob("*")
            for p in it:
                try:
                    if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                        files.append(str(p))
                except OSError:
                    continue
        except OSError:
            return [], 0
        files.sort(key=lambda s: s.lower())
        added, skipped = self.add_files(files)
        return added, len(files) - len(added)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.playlist):
            was_current = index == self.index
            del self.playlist[index]
            if not self.playlist:
                self.stop()
                self.index = 0
            else:
                if index < self.index:
                    self.index -= 1
                elif was_current and self.playing:
                    self.index %= len(self.playlist)
                    self.play_index(self.index)
                self.index %= len(self.playlist)
            self._persist()
            self.on_change()

    def remove_missing(self) -> int:
        before = len(self.playlist)
        self.playlist = [p for p in self.playlist if Path(p).is_file()]
        if self.playlist:
            self.index %= len(self.playlist)
        else:
            self.index = 0
        removed = before - len(self.playlist)
        if removed:
            self._persist()
            self.on_change()
        return removed

    def clear(self) -> None:
        self.stop()
        self.playlist = []
        self.index = 0
        self._persist()
        self.on_change()

    # -- 播放 -------------------------------------------------------
    def play_index(self, index: int | None = None) -> bool:
        if not self.playlist:
            self.error = "播放列表为空，请先添加音乐"
            self.on_change()
            return False
        if self.backend is None:
            self.error = "未找到可用的音频设备"
            self.on_change()
            return False
        if index is not None:
            self.index = int(index) % len(self.playlist)
        self.index %= len(self.playlist)
        path = self.playlist[self.index]
        try:
            loop_one = str(self.settings.get("music_loop_mode")) == "one"
            self.backend.load(path)
            self.backend.set_volume(float(self.settings.get("music_volume", 0.45)))
            self.backend.play(loop=loop_one)
        except Exception as exc:  # 损坏/不支持的音频
            self.error = f"无法播放：{Path(path).name}（{exc}）"
            self.playing = False
            self.on_change()
            return False
        self.error = ""
        self.playing = True
        self.paused = False
        self.current_path = path
        self._persist()
        self.on_change()
        return True

    def toggle(self) -> None:
        if not self.playlist:
            self.play_index()
            return
        if self.playing and not self.paused:
            self.pause()
        elif self.paused:
            self.resume()
        else:
            self.play_index(self.index)

    def pause(self) -> None:
        if self.backend and self.playing:
            self.backend.pause()
            self.paused = True
            self.on_change()

    def resume(self) -> None:
        if self.backend and self.paused:
            self.backend.unpause()
            self.paused = False
            self.on_change()

    def stop(self) -> None:
        if self.backend:
            try:
                self.backend.stop()
            except Exception:
                pass
        self.playing = False
        self.paused = False
        self.on_change()

    def next_track(self, auto: bool = False) -> None:
        if not self.playlist:
            return
        mode = str(self.settings.get("music_loop_mode"))
        if mode == "shuffle" and len(self.playlist) > 1:
            new = self.index
            while new == self.index:
                new = random.randrange(len(self.playlist))
            self.play_index(new)
            return
        if auto and mode == "one":
            self.play_index(self.index)
            return
        self.play_index((self.index + 1) % len(self.playlist))

    def prev_track(self) -> None:
        if not self.playlist:
            return
        if len(self.playlist) == 1:
            self.play_index(0)
            return
        self.play_index((self.index - 1) % len(self.playlist))

    def set_volume(self, volume: float, persist: bool = True) -> None:
        volume = max(0.0, min(1.0, float(volume)))
        self.settings["music_volume"] = round(volume, 3)
        if self.backend:
            try:
                self.backend.set_volume(volume)
            except Exception:
                pass
        if persist:
            self.settings.save()

    @property
    def volume(self) -> float:
        return float(self.settings.get("music_volume", 0.45))

    @property
    def position(self) -> float:
        return self.backend.position if self.backend and self.playing else 0.0

    @property
    def length(self) -> float:
        try:
            return float(self.backend.length) if self.backend else 0.0
        except Exception:
            return 0.0

    def tick(self) -> None:
        """由界面每 500ms 调用：曲目播完后自动切歌。"""
        if not self.playing or self.paused or self.backend is None:
            return
        try:
            if not self.backend.busy:
                self.next_track(auto=True)
        except Exception:
            pass

    def status_text(self) -> str:
        if not self.playlist:
            return "未添加背景音乐"
        if self.error:
            return self.error
        name = self.current_name
        if self.playing and not self.paused:
            return f"正在播放 · {name}"
        if self.paused:
            return f"已暂停 · {name}"
        return f"已就绪 · {name}"

    def close(self) -> None:
        try:
            self.stop()
            if self.backend is not None and hasattr(self.backend, "_close_alias"):
                self.backend._close_alias()
        except Exception:
            pass
