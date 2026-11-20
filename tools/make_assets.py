"""生成品牌资源：assets/logo.png 与 assets/icon.ico（风火轮主题）。"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG_TOP = (20, 27, 51)
BG_BOTTOM = (9, 12, 22)
ORANGE = (255, 143, 63)
ORANGE_HI = (255, 171, 99)
GOLD = (255, 201, 77)
TEXT = (238, 242, 255)
RED = (255, 77, 94)

SIZE = 512
CN_FONTS = [
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in CN_FONTS:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def vertical_gradient(size: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (1, size))
    px = img.load()
    for y in range(size):
        t = y / max(1, size - 1)
        px[0, y] = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
    return img.resize((size, size), Image.BILINEAR)


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * 4 - 1, size * 4 - 1), radius=radius * 4, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def radial_glow(size: int, color, max_alpha: int) -> Image.Image:
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    center = size / 2
    steps = 90
    for i in range(steps, 0, -1):
        t = i / steps
        radius = center * t
        alpha = int(max_alpha * (1 - t) ** 2.2)
        if alpha <= 0:
            continue
        draw.ellipse(
            (center - radius, center - radius, center + radius, center + radius),
            fill=(color[0], color[1], color[2], alpha))
    return glow.filter(ImageFilter.GaussianBlur(size * 0.02))


def build_logo(size: int = SIZE) -> Image.Image:
    base = vertical_gradient(size, BG_TOP, BG_BOTTOM).convert("RGBA")
    base.putalpha(rounded_mask(size, int(size * 0.22)))

    # 中心光晕
    glow = radial_glow(size, ORANGE, 150)
    base.alpha_composite(glow, (0, 0))

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    c = size / 2
    # 火焰圆环（由若干小段弧拼出渐变）
    ring_r = size * 0.335
    width = int(size * 0.026)
    segments = 120
    for i in range(segments):
        start = -90 + i * (360 / segments)
        end = start + (360 / segments) + 1.2
        t = i / segments
        color = (
            int(ORANGE[0] + (GOLD[0] - ORANGE[0]) * t),
            int(ORANGE[1] + (GOLD[1] - ORANGE[1]) * t),
            int(ORANGE[2] + (GOLD[2] - ORANGE[2]) * t),
            235,
        )
        draw.arc((c - ring_r, c - ring_r, c + ring_r, c + ring_r),
                 start=start, end=end, fill=color, width=width)
    # 内圈细线
    inner_r = size * 0.245
    draw.ellipse((c - inner_r, c - inner_r, c + inner_r, c + inner_r),
                 outline=(255, 180, 110, 55), width=max(1, int(size * 0.004)))

    # 星火
    for dx, dy, r, color in ((0.30, 0.20, 0.011, GOLD), (0.73, 0.30, 0.008, ORANGE_HI),
                             (0.68, 0.79, 0.010, RED), (0.24, 0.72, 0.007, ORANGE)):
        x, y, rr = size * dx, size * dy, size * r
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color + (170,))

    # 「风」字 + 橙色投影
    font = load_font(int(size * 0.42))
    text = "风"
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    tx = c - tw / 2 - box[0]
    ty = c - th / 2 - box[1]
    draw.text((tx + size * 0.008, ty + size * 0.010), text, font=font,
              fill=(255, 120, 40, 150))
    draw.text((tx, ty), text, font=font, fill=TEXT + (255,))

    # 底部混天绫弧线（平滑波浪，两端淡出）
    points = []
    ribbon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(ribbon)
    for i in range(80):
        t = i / 79
        x = size * 0.15 + t * size * 0.70
        taper = math.sin(math.pi * t) ** 0.6
        y = size * 0.845 + math.sin(t * math.pi * 2.2 + 0.4) * size * 0.045 * taper
        points.append((x, y))
    for width, alpha in ((int(size * 0.012), 46), (int(size * 0.006), 120)):
        rdraw.line(points, fill=(255, 96, 80, alpha), width=max(2, width), joint="curve")
    base.alpha_composite(ribbon, (0, 0))

    base.alpha_composite(layer, (0, 0))
    return base


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    logo = build_logo(SIZE)
    logo.save(ASSETS / "logo.png")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    logo.save(ASSETS / "icon.ico", sizes=sizes)
    print("assets/logo.png", logo.size)
    print("assets/icon.ico", sizes)


if __name__ == "__main__":
    main()
