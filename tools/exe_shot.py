"""开发用：启动打包后的 exe，等窗口出现，截图并关闭。"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "dist" / "风火轮打字.exe"


def find_window(title_part: str) -> int | None:
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        if title_part in buf.value:
            found.append(hwnd)
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return found[0] if found else None


def capture_window(hwnd: int):
    """用 PrintWindow 抓窗口内容，即使窗口被别的程序挡住也能截到。"""
    from ctypes import wintypes

    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    ok = user32.PrintWindow(hwnd, mem_dc, 2)  # PW_RENDERFULLCONTENT

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    info = BitmapInfoHeader()
    info.biSize = ctypes.sizeof(BitmapInfoHeader)
    info.biWidth = width
    info.biHeight = -height
    info.biPlanes = 1
    info.biBitCount = 32
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(info), 0)
    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1).convert("RGB")
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hdc)
    if not ok:
        print("PrintWindow returned 0, image may be blank")
    return image


def main() -> int:
    if not EXE.exists():
        print("exe missing:", EXE)
        return 1
    data = ROOT / "_preview_data" / "exe"
    data.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LOCALAPPDATA=str(data))
    proc = subprocess.Popen([str(EXE)], env=env)
    hwnd = None
    for _ in range(40):
        time.sleep(0.5)
        hwnd = find_window("风火轮打字")
        if hwnd:
            break
        if proc.poll() is not None:
            print("exe exited early, code", proc.returncode)
            return 1
    if not hwnd:
        print("window not found; killing")
        proc.kill()
        return 1
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    try:
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(2.0)
    rect = ctypes.wintypes.RECT() if hasattr(ctypes, "wintypes") else None
    from ctypes import wintypes

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    print("window rect", bbox)
    out = ROOT / "_shots" / "00_exe.png"
    capture_window(hwnd).save(out)
    print("saved", out)
    user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("exit code", proc.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
