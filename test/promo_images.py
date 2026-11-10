"""Build promo/ from the raw window shots (python test/promo_shots.py first) and the icon art.

    python test/promo_images.py

promo/screenshot_N.jpg (1920x1080), promo/thumbnail.jpg (630x500), promo/cover.jpg (1280x720).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "shots" / "promo_raw"
OUT = ROOT / "promo"
ART = Image.open(ROOT / "assets" / "icon_og.jpg").convert("RGB")
FONTS = Path("C:/Windows/Fonts")

NEON = "#C8FF2E"
SOFT = "#E4FF9C"
WHITE = "#F2FBF7"
INK = "#0B2226"
INPUT = "#123A41"

SHOTS = [
    ("1_ps1_done", "Make a whole folder sound like it belongs together",
     "Every file at the same loudness, with the right method for sound effects, voice, music or ambience. Pick a folder, press Start. Your originals are never touched."),
    ("2_tape_mid", "19 effects to give every file the same character",
     "A radio, a telephone, a megaphone, underwater, an old cassette tape, vinyl, another room, gritty or brutal distortion, plus polish presets."),
    ("3_scanned", "A retro quality ladder: NES to PlayStation 2",
     "Push mismatched sounds through the same lo-fi texture so they finally match. It also spots the files that are unusually quiet."),
]

EFFECTS = ["NES", "SNES", "PS1", "N64", "SATURN", "PS2", "RADIO", "PHONE", "MEGAPHONE",
           "UNDERWATER", "CASSETTE", "VINYL", "GRITTY", "BRUTAL", "PODCAST", "PUNCHY"]


def font(size, name="seguibl.ttf"):
    return ImageFont.truetype(str(FONTS / name), size)


def cover_crop(img, w, h, focus_y=0.45):
    """Scale to cover w x h, crop around the horizontal centre and focus_y."""
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = min(max(0, round(img.height * focus_y - h / 2)), img.height - h)
    return img.crop((x, y, x + w, y + h))


def darken(img, amount):
    return Image.blend(img, Image.new("RGB", img.size, INPUT), amount)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def text_block(img, xy, text, fnt, fill, width, spacing=1.15, shadow=6):
    """Wrapped text with a soft dark shadow. Returns the y below the block."""
    draw = ImageDraw.Draw(img)
    x, y = xy
    step = round(fnt.size * spacing)
    lines = wrap(draw, text, fnt, width)
    if shadow:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for i, line in enumerate(lines):
            d.text((x + 3, y + 4 + i * step), line, font=fnt, fill=(5, 20, 24, 255))
        img.paste(layer.filter(ImageFilter.GaussianBlur(shadow)), (0, 0), layer.filter(ImageFilter.GaussianBlur(shadow)))
    for i, line in enumerate(lines):
        draw.text((x, y + i * step), line, font=fnt, fill=fill, stroke_width=max(1, fnt.size // 22), stroke_fill=INK)
    return y + len(lines) * step


def chips(img, x, y, width, words, fnt, gap=10):
    """Neon pill labels flowing left to right. Returns the y below them."""
    draw = ImageDraw.Draw(img)
    pad_x, h = round(fnt.size * 0.55), round(fnt.size * 1.5)
    cx = x
    for w in words:
        tw = draw.textlength(w, font=fnt)
        if cx + tw + 2 * pad_x > x + width:
            cx, y = x, y + h + gap
        draw.rounded_rectangle((cx, y, cx + tw + 2 * pad_x, y + h), radius=h // 2, fill=NEON, outline=INK, width=2)
        draw.text((cx + pad_x, y + h / 2), w, font=fnt, fill=INK, anchor="lm")
        cx += tw + 2 * pad_x + gap
    return y + h


def with_shadow(canvas, img, xy, blur=18):
    shadow = Image.new("RGBA", (img.width + 4 * blur, img.height + 4 * blur), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((2 * blur, 2 * blur, 2 * blur + img.width, 2 * blur + img.height), fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(shadow, (xy[0] - 2 * blur + 8, xy[1] - 2 * blur + 12), shadow)
    canvas.paste(img, xy)
    ImageDraw.Draw(canvas).rectangle((xy[0] - 1, xy[1] - 1, xy[0] + img.width, xy[1] + img.height), outline=NEON, width=2)


def save(img, name):
    """JPG unless PNG comes out smaller."""
    jpg, png = OUT / f"{name}.jpg", OUT / f"{name}.png"
    img.save(jpg, quality=90, optimize=True)
    img.save(png, optimize=True)
    keep, drop = (jpg, png) if jpg.stat().st_size <= png.stat().st_size else (png, jpg)
    drop.unlink()
    print(f"{keep.name}: {img.width}x{img.height}, {keep.stat().st_size // 1024} KB")


def screenshot(i, raw, title, sub):
    W, H = 1920, 1080
    bg = darken(cover_crop(ART, W, H).filter(ImageFilter.GaussianBlur(10)), 0.35)
    win = Image.open(RAW / f"{raw}.png").convert("RGB")
    wx, wy = W - win.width - 70, (H - win.height) // 2
    with_shadow(bg, win, (wx, wy))
    left, width = 80, wx - 80 - 70
    y = text_block(bg, (left, 150), title, font(76), NEON, width, spacing=1.12)
    y = text_block(bg, (left, y + 40), sub, font(38, "seguisb.ttf"), WHITE, width, spacing=1.3, shadow=4)
    chips(bg, left, y + 50, width, {1: EFFECTS[:9], 2: EFFECTS[6:], 3: EFFECTS[:6]}[i], font(26))
    text_block(bg, (left, H - 120), "Made by Reactorcore", font(30, "seguisb.ttf"), SOFT, width, shadow=3)
    save(bg, f"screenshot_{i}")


def thumbnail():
    W, H = 630, 500
    img = darken(cover_crop(ART, W, H, focus_y=0.5), 0.15)
    # dark bands top and bottom for the text
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    for y in range(H):
        a = max(0, 1 - y / 190) if y < H / 2 else max(0, (y - (H - 170)) / 170)
        d.line((0, y, W, y), fill=(11, 34, 38, round(220 * min(a, 1))))
    img.paste(band, (0, 0), band)
    text_block(img, (28, 14), "AUDIO FOLDER", font(68), WHITE, W, spacing=1.0, shadow=5)
    text_block(img, (28, 82), "UNIFIER", font(84), NEON, W, spacing=1.0, shadow=5)
    chips(img, 26, H - 118, W - 40, ["SAME LOUDNESS", "19 EFFECTS", "NES → PS2"], font(25), gap=8)
    text_block(img, (28, H - 64), "Every sound, one consistent set", font(36, "seguisb.ttf"), WHITE, W, shadow=4)
    save(img, "thumbnail")


def cover():
    W, H = 1280, 720
    img = darken(cover_crop(ART, W, H).filter(ImageFilter.GaussianBlur(14)), 0.45)
    art = ART.resize((720, 720), Image.LANCZOS)
    mask = Image.new("L", (720, 720), 255)
    fade = 260   # the art's left edge fades into the background
    for x in range(fade):
        ImageDraw.Draw(mask).line((x, 0, x, 720), fill=round(255 * x / fade))
    img.paste(art, (W - 720, 0), mask)
    left, width = 56, 700
    y = text_block(img, (left, 40), "AUDIO FOLDER", font(92), WHITE, width + 200, spacing=1.0)
    y = text_block(img, (left, y - 6), "UNIFIER", font(124), NEON, width, spacing=1.0)
    y = text_block(img, (left, y + 20), "Make a whole folder of audio sound like it belongs together", font(42, "seguisb.ttf"), WHITE, width - 40, spacing=1.2, shadow=4)
    chips(img, left, y + 30, width - 40, EFFECTS, font(28))
    save(img, "cover")


def main():
    OUT.mkdir(exist_ok=True)
    missing = [r for r, *_ in SHOTS if not (RAW / f"{r}.png").exists()]
    if missing:
        sys.exit(f"Run test/promo_shots.py first (missing {missing})")
    for i, (raw, title, sub) in enumerate(SHOTS, 1):
        screenshot(i, raw, title, sub)
    thumbnail()
    cover()


if __name__ == "__main__":
    main()
