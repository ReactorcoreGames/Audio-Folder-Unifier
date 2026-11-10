"""Render the YouTube trailer (see trailer.md). Run trailer/make_audio.py and trailer/window_shots.py first.

    python trailer/render.py [--shorts] [--draft]

--shorts renders 9:16 instead of 16:9; --draft renders 480p. Output: trailer/trailer_16x9.mp4,
trailer/trailer_shorts.mp4 (with a _draft suffix for drafts).
"""

import argparse
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "test"))
from promo_images import ART, INK, INPUT, NEON, SOFT, WHITE, cover_crop, darken, font  # noqa: E402

HERE = ROOT / "trailer"
WORK = HERE / "work"
MUSIC = HERE / "Sunday Drive - Silent Partner.mp3"
FPS = 30
RATE = 44100

# Music grid (trailer.md): 86.13 BPM, first bar line at 2.18 s
BEAT = 60 / 86.13
BAR = 4 * BEAT


def bar(n):
    return 2.18 + n * BAR


END = bar(16) + 1.45            # about 48.2 s
FADE_OUT = 3.2                  # music and picture fade over the last seconds

SOUNDS = [  # (file stem in work/before, label shown)
    ("1_explosion", "explosion-2.ogg"),
    ("2_raven", "raven-2.ogg"),
    ("3_glass", "glass-breaking-2.ogg"),
    ("4_coin", "gold-1.ogg"),
    ("5_dinosaur", "dinosaur-1.wav"),
]
BEFORE_GAIN_DB = -6             # the raw set is lowered together; the gaps stay true
BEFORE_AT = [bar(1) + BEAT * (1 + 2 * i) for i in range(5)]
AFTER_AT = [bar(5) + BEAT * (1 + 2 * i) for i in range(5)]
LANE_SPAN = 1.45                # seconds shown across a sound lane

RUNGS = [  # (tag, pill label, tagline); the ladder shows all six, four get played
    ("nes", "NES", "Thin, buzzy and crunchy"),
    ("snes", "SNES", None),
    ("ps1", "PS1", "Grainy, with early-3D reverb"),
    ("n64", "N64", None),
    ("saturn", "SATURN", "Dreamy, floating echoes"),
    ("ps2", "PS2", "Bright, with a fizzy grain"),
]
PLAYED = [r for r in RUNGS if r[2]]
RUNG_AT = [bar(8 + i) + 0.35 for i in range(len(PLAYED))]
VOICE_SPAN = 2.5

EFFECT_WAVES = [
    ("Sounds like it's coming from", ["A RADIO", "A TELEPHONE", "A MEGAPHONE", "UNDERWATER",
                                      "A CASSETTE", "VINYL", "ANOTHER ROOM"]),
    ("Rough it up", ["GRITTY", "BRUTAL"]),
    ("Polish & finish", ["PODCAST", "PUNCHY", "WARM", "BRIGHT"]),
]
CLICK_AT = bar(4) + BEAT

DIM = "#5F8C8C"
DITHER = np.random.default_rng(0)
GHOST = (120, 160, 160, 150)


# ---------------------------------------------------------------- audio

def load(path, channels=2):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", str(channels),
                          "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels)


def db(x):
    return 10 ** (x / 20)


def after_file(stem):
    return WORK / "after" / f"{stem}_sfx.wav"


def rung_file(tag):
    return WORK / f"ladder_{tag}" / f"line_voice_{tag}.wav"


def music_gain(t):
    """Duck under the demos (trailer.md), full for titles, then the end fade."""
    keys = [(0, 0), (bar(1) - 0.3, 0), (bar(1), -14), (bar(4) - 0.4, -14), (bar(4), -7),
            (bar(5) - 0.3, -7), (bar(5), -14), (bar(8) - 0.3, -14), (bar(8), -12),
            (bar(12) - 0.3, -12), (bar(12) + 0.4, 0), (END, 0)]
    g = db(np.interp(t, [k[0] for k in keys], [k[1] for k in keys]))
    return g * np.clip((END - t) / FADE_OUT, 0, 1)


def click():
    t = np.arange(int(0.04 * RATE)) / RATE
    rng = np.random.default_rng(1)
    s = (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 160) + rng.normal(0, 0.3, t.size) * np.exp(-t * 900))
    return np.repeat((s * db(-16)).astype(np.float32)[:, None], 2, 1)


def build_mix(out):
    n = int(END * RATE)
    music = load(MUSIC)[:n]
    mix = np.zeros((n, 2), np.float32)
    mix[:len(music)] = music * music_gain(np.arange(len(music)) / RATE)[:, None]

    def place(sig, at):
        i = int(at * RATE)
        j = min(n, i + len(sig))
        mix[i:j] += sig[:j - i]

    for (stem, _), at in zip(SOUNDS, BEFORE_AT):
        place(load(WORK / "before" / f"{stem}.wav") * db(BEFORE_GAIN_DB), at)
    for (stem, _), at in zip(SOUNDS, AFTER_AT):
        place(load(after_file(stem)), at)
    for (tag, *_), at in zip(PLAYED, RUNG_AT):
        place(load(rung_file(tag)), at)
    place(click(), CLICK_AT)
    peak = np.abs(mix).max()
    if peak > db(-1):
        mix *= db(-1) / peak
    print(f"mix peak {20 * np.log10(peak):.1f} dBFS")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-i", "-",
                    "-c:a", "pcm_s16le", str(out)], input=mix.tobytes(), check=True)


def envelope(path, width, span, gain_db=0):
    """Max |sample| per pixel column over `span` seconds, scaled by gain_db; 0 dBFS = 1."""
    x = np.abs(load(path)).max(1) * db(gain_db)
    spp = span * RATE / width
    cols = min(width, int(len(x) / spp))
    return np.array([x[int(i * spp):int((i + 1) * spp)].max() for i in range(cols)])


# ---------------------------------------------------------------- drawing helpers

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def env(t, a, b, fi=0.3, fo=0.3):
    """0 outside [a, b], ramps in over fi and out over fo."""
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / fi if fi else 1, (b - t) / fo if fo else 1)


class Frame:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.portrait = H > W
        self.u = min(W, H) / 1080          # layout unit: 1 px at 1080p
        big = cover_crop(ART, int(W * 1.08), int(H * 1.08)).filter(ImageFilter.GaussianBlur(12 * self.u))
        self.bg = darken(big, 0.55)
        self.bg_px = np.asarray(self.bg, np.float32)
        art = ART.resize((int(420 * self.u),) * 2, Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", art.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *art.size), radius=int(60 * self.u), fill=255)
        art.putalpha(mask)
        self.icon = art
        self.windows = {n: Image.open(WORK / "window" / f"{n}.png").convert("RGBA")
                        for n in ("1_ready", "2_mid", "3_done")}

    def s(self, v):
        return round(v * self.u)

    @lru_cache(maxsize=None)
    def text(self, text, size, face="seguibl.ttf", fill=WHITE, shadow=6):
        """Pre-rendered text with an ink stroke and a soft shadow. Returns (image, pad)."""
        fnt = font(self.s(size), face)
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        l, t, r, b = tmp.textbbox((0, 0), text, font=fnt, stroke_width=max(1, fnt.size // 22))
        pad = self.s(shadow * 3)
        img = Image.new("RGBA", (r + 2 * pad, b + 2 * pad), (0, 0, 0, 0))
        if shadow:
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((pad + self.s(3), pad + self.s(4)), text, font=fnt, fill=(5, 20, 24, 230))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(self.s(shadow))))
        ImageDraw.Draw(img).text((pad, pad), text, font=fnt, fill=fill,
                                 stroke_width=max(1, fnt.size // 22), stroke_fill=INK)
        return img, pad

    @lru_cache(maxsize=None)
    def pill(self, text, size, on=True):
        fnt = font(self.s(size))
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = tmp.textlength(text, font=fnt)
        px, h = round(fnt.size * 0.55), round(fnt.size * 1.5)
        img = Image.new("RGBA", (int(tw + 2 * px) + 2, h + 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, tw + 2 * px, h), radius=h // 2, fill=NEON if on else INPUT,
                            outline=INK if on else DIM, width=max(1, self.s(2)))
        d.text((px, h / 2), text, font=fnt, fill=INK if on else DIM, anchor="lm")
        return img


def put(layer, img, x, y, a=1.0):
    """Alpha-composite img onto layer at (x, y), at opacity a. Clips at the edges."""
    if a <= 0:
        return
    x, y = int(x), int(y)
    if a < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    l, t = max(0, -x), max(0, -y)
    r, b = min(img.width, layer.width - x), min(img.height, layer.height - y)
    if r > l and b > t:
        layer.alpha_composite(img.crop((l, t, r, b)), (x + l, y + t))


def put_text(f, layer, spec, x, y, a=1.0, anchor="l", rise=1.0):
    """Text sprite at its top-left (anchor l), centre (c) or right (r); rise slides it up as it fades in."""
    img, pad = f.text(*spec) if isinstance(spec, tuple) else f.text(spec, 40)
    w = img.width - 2 * pad
    x = {"l": x, "c": x - w / 2, "r": x - w}[anchor]
    put(layer, img, x - pad, y - pad + f.s(30) * (1 - rise), a)
    return w


def wrap_lines(f, text, size, face, width):
    fnt = font(f.s(size), face)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def put_para(f, layer, text, size, x, y, width, a=1.0, face="seguibl.ttf", fill=WHITE, anchor="l",
             rise=1.0, spacing=1.15):
    """Wrapped text; returns the y below it."""
    for i, line in enumerate(wrap_lines(f, text, size, face, width)):
        put_text(f, layer, (line, size, face, fill), x, y + i * f.s(size * spacing), a, anchor, rise)
    return y + len(wrap_lines(f, text, size, face, width)) * f.s(size * spacing)


def draw_wave(d, x, ymid, env_, half, upto, color, min_h=1):
    for i in range(min(upto, len(env_))):
        h = max(min_h, env_[i] * half)
        d.line((x + i, ymid - h, x + i, ymid + h), fill=color)


# ---------------------------------------------------------------- layout

class Layout:
    """Pixel positions for 16:9 or 9:16."""

    def __init__(self, f):
        s, W, H = f.s, f.W, f.H
        self.margin = s(120) if not f.portrait else s(70)
        m = self.margin
        if not f.portrait:
            self.header_y, self.header_w = s(80), W - 2 * m
            self.lane_label_x, self.lane_x, self.lane_w = m + s(30), m + s(440), W - 2 * m - s(470)
            self.row_y0, self.row_h, self.row_gap, self.lane_half = s(215), s(118), s(20), s(50)
            self.caption_y = s(930)
        else:
            self.header_y, self.header_w = s(250), W - 2 * m
            self.lane_label_x, self.lane_x, self.lane_w = m + s(30), m + s(30), W - 2 * m - s(60)
            self.row_y0, self.row_h, self.row_gap, self.lane_half = s(560), s(205), s(28), s(62)
            self.caption_y = s(1760)

    def row(self, i):
        return self.row_y0 + i * (self.row_h + self.row_gap)


# ---------------------------------------------------------------- shots

def title_card(f, L, layer, t, t0, tagline, extra):
    """Icon + name + tagline (opening) or links (outro)."""
    s, W = f.s, f.W
    a_icon = ease((t - t0 - 0.2) / 0.9)
    icon = f.icon if not f.portrait else f.icon.resize((s(560), s(560)), Image.LANCZOS)
    iy = s(110) if not f.portrait else s(330)
    sc = 0.92 + 0.08 * a_icon
    ic = icon.resize((int(icon.width * sc), int(icon.height * sc)), Image.LANCZOS)
    put(layer, ic, (W - ic.width) / 2, iy + (icon.height - ic.height) / 2, a_icon)
    y = iy + icon.height + s(50)
    k = ease((t - t0 - 0.9) / 0.6)
    if not f.portrait:
        put_text(f, layer, ("AUDIO FOLDER UNIFIER", 104, "seguibl.ttf", NEON), W / 2, y, k, "c", k)
        y += s(140)
    else:
        put_text(f, layer, ("AUDIO FOLDER", 112, "seguibl.ttf", WHITE), W / 2, y, k, "c", k)
        put_text(f, layer, ("UNIFIER", 150, "seguibl.ttf", NEON), W / 2, y + s(125), k, "c", k)
        y += s(320)
    k = ease((t - t0 - 1.6) / 0.6)
    if tagline:
        put_para(f, layer, tagline, 52, W / 2, y, W - 2 * L.margin, k, "seguisb.ttf", WHITE, "c", k)
    for i, (spec, is_pill) in enumerate(extra):
        k = ease((t - t0 - 1.4 - 0.5 * i) / 0.6)
        if is_pill:
            p = f.pill(spec, 46)
            put(layer, p, (W - p.width) / 2, y + s(20) * (1 - k), k)
            y += p.height + s(28)
        else:
            put_text(f, layer, (spec, 50, "seguisb.ttf", WHITE), W / 2, y, k, "c", k)
            y += s(90)


def shot_title(f, L, layer, t):
    title_card(f, L, layer, t, 0.0, "Make a folder of sounds belong together.", [])


def lanes(f, L, layer, t, starts, envs, ghosts=None, appear_at=0.0):
    """The five sound rows; each one draws its waveform as it plays."""
    s = f.s
    d = ImageDraw.Draw(layer)
    for i, ((_, label), at) in enumerate(zip(SOUNDS, starts)):
        k = ease((t - appear_at - 0.12 * i) / 0.5)
        if k <= 0:
            continue
        y = L.row(i)
        playing = at <= t < at + len(envs[i]) / L.lane_w * LANE_SPAN + 0.1
        card = Image.new("RGBA", (f.W - 2 * L.margin, L.row_h), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=s(22), fill=(11, 34, 38, 215),
                             outline=NEON if playing else (95, 140, 140, 255), width=s(3) if playing else s(1))
        put(layer, card, L.margin + s(40) * (1 - k), y, k)
        if not f.portrait:
            label_y, ymid = y + L.row_h / 2 - s(22), y + L.row_h / 2
        else:
            label_y, ymid = y + s(16), y + s(125)
        put_text(f, layer, (label, 36, "seguisb.ttf", NEON if playing else WHITE, 0), L.lane_label_x, label_y, k)
        if k < 1:
            continue
        if ghosts:
            draw_wave(d, L.lane_x, ymid, ghosts[i], L.lane_half, len(ghosts[i]), GHOST)
        upto = int((t - at) / LANE_SPAN * L.lane_w)
        if upto > 0:
            draw_wave(d, L.lane_x, ymid, envs[i], L.lane_half, upto, NEON if playing else SOFT)


def shot_before(f, L, layer, t, data):
    t0 = bar(1)
    k = ease((t - t0) / 0.5)
    put_para(f, layer, "Sounds from everywhere…", 72, L.margin, L.header_y, L.header_w, k, fill=NEON, rise=k)
    lanes(f, L, layer, t, BEFORE_AT, data["before"], appear_at=t0 + 0.15)
    k = ease((t - bar(3)) / 0.5)
    put_para(f, layer, "…and every one a different volume.", 50, L.margin, L.caption_y, L.header_w, k,
             "seguisb.ttf", WHITE, rise=k)


def shot_click(f, L, layer, t):
    s, W, H = f.s, f.W, f.H
    t0 = bar(4)
    name = "1_ready" if t < CLICK_AT + 0.35 else "2_mid" if t < CLICK_AT + 1.2 else "3_done"
    win = f.windows[name]
    push = 1 + 0.04 * (t - t0) / BAR
    if not f.portrait:
        sc = s(880) / win.height * push
        wx, wy = W - L.margin - win.width * s(880) / win.height, s(100)
    else:
        sc = (W - 2 * L.margin) / win.width * push
        wx, wy = L.margin, s(640)
    img = win.resize((int(win.width * sc), int(win.height * sc)), Image.LANCZOS)
    k = ease((t - t0) / 0.4)
    put(layer, img, wx, wy, k)
    ImageDraw.Draw(layer).rectangle((wx - 2, wy - 2, wx + img.width + 1, wy + img.height + 1),
                                    outline=NEON, width=max(1, s(3)))
    # Flash a ring round Start when it's pressed (button at 205,697 - 437,743 in the 900x960 shot)
    ring = env(t, CLICK_AT - 0.15, CLICK_AT + 0.5, 0.1, 0.3)
    if ring:
        g = s(8) + s(10) * (1 - ring)
        box = (wx + 205 * sc - g, wy + 697 * sc - g, wx + 437 * sc + g, wy + 743 * sc + g)
        r = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(r).rounded_rectangle(box, radius=s(10), outline=NEON, width=s(6))
        put(layer, r, 0, 0, ring)
    if not f.portrait:
        tx, ty = L.margin, s(330)
        put_text(f, layer, ("Pick a folder.", 84, "seguibl.ttf", NEON), tx, ty, k, rise=k)
        k2 = ease((t - CLICK_AT + 0.2) / 0.5)
        put_text(f, layer, ("Press Start.", 84, "seguibl.ttf", WHITE), tx, ty + s(120), k2, rise=k2)
    else:
        put_text(f, layer, ("Pick a folder.", 96, "seguibl.ttf", NEON), W / 2, s(300), k, "c", k)
        k2 = ease((t - CLICK_AT + 0.2) / 0.5)
        put_text(f, layer, ("Press Start.", 96, "seguibl.ttf", WHITE), W / 2, s(430), k2, "c", k2)


def shot_after(f, L, layer, t, data):
    t0 = bar(5)
    k = ease((t - t0) / 0.5)
    put_para(f, layer, "The same sounds, one click later.", 72, L.margin, L.header_y, L.header_w, k,
             fill=NEON, rise=k)
    lanes(f, L, layer, t, AFTER_AT, data["after"], ghosts=data["before"], appear_at=t0 + 0.15)
    k = ease((t - bar(7)) / 0.5)
    put_para(f, layer, "Same loudness. Nothing to set up.", 50, L.margin, L.caption_y, L.header_w, k,
             "seguisb.ttf", WHITE, rise=k)


def shot_ladder(f, L, layer, t, data):
    s, W = f.s, f.W
    z = 1.3 if f.portrait else 1
    t0 = bar(8)
    k = ease((t - t0) / 0.5)
    y = put_para(f, layer, "…or give them one shared texture.", 72, L.margin, L.header_y, L.header_w, k,
                 fill=NEON, rise=k)
    # Which played rung is current
    cur = max([i for i, at in enumerate(RUNG_AT) if t >= at - 0.35] or [0])
    tag, label, tagline = PLAYED[cur]
    # The ladder: six pills, strongest first
    pills = [f.pill(lab, round(40 * z), on=(tg == tag)) for tg, lab, _ in RUNGS]
    gap = s(18)
    rows = [pills] if not f.portrait else [pills[:3], pills[3:]]
    py = y + s(40)
    for row in rows:
        total = sum(p.width for p in row) + gap * (len(row) - 1)
        px = (W - total) / 2
        for p in row:
            put(layer, p, px, py, k)
            px += p.width + gap
        py += row[0].height + gap
    hint = "strongest  ←  quality ladder  →  lightest"
    put_text(f, layer, (hint, round(30 * z), "seguisb.ttf", SOFT, 0), W / 2, py + s(6), k * 0.9, "c")
    # Current rung: name, flavour, and the voice line's waveform
    at = RUNG_AT[cur]
    kk = ease((t - (at - 0.35)) / 0.4)
    ny = py + s(90) if not f.portrait else py + s(150)
    put_text(f, layer, (label, round(120 * z), "seguibl.ttf", NEON), L.margin, ny, kk, rise=kk)
    put_text(f, layer, (tagline, round(50 * z), "seguisb.ttf", WHITE), L.margin, ny + s(150 * z), kk, rise=kk)
    lx, ly, lw = L.margin, ny + s(250 * z), W - 2 * L.margin
    lh = s(250) if not f.portrait else s(480)
    card = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, lw - 1, lh - 1), radius=s(26), fill=(11, 34, 38, 215),
                                           outline=NEON, width=s(2))
    put(layer, card, lx, ly, k)
    put_text(f, layer, ("“Unify your audio.”", round(34 * z), "seguisb.ttf", SOFT, 0), lx + s(30), ly + s(18), k)
    if k >= 1:
        e = data["ladder"][tag]
        width = lw - s(60)
        upto = int((t - at) / VOICE_SPAN * width)
        if upto > 0:
            draw_wave(ImageDraw.Draw(layer), lx + s(30), ly + lh / 2 + s(18), e, lh / 2 - s(50), upto, NEON)


def shot_effects(f, L, layer, t):
    s, W = f.s, f.W
    z = 1.3 if f.portrait else 1
    y = L.header_y + s(10)
    width = W - 2 * L.margin
    for i, (title, words) in enumerate(EFFECT_WAVES):
        k = ease((t - bar(12) - i * 2 * BEAT) / 0.5)
        put_text(f, layer, (title, round(46 * z), "seguisb.ttf", SOFT), L.margin, y, k, rise=k)
        y += s(80 * z)
        x, gap = L.margin, s(16)
        for j, w in enumerate(words):
            p = f.pill(w, round(40 * z))
            if x + p.width > L.margin + width:
                x, y = L.margin, y + p.height + gap
            kj = ease((t - bar(12) - i * 2 * BEAT - 0.06 * j) / 0.4)
            put(layer, p, x, y + s(24) * (1 - kj), kj)
            x += p.width + gap
        y += p.height + s(60 * z)
    k = ease((t - bar(13) - 2 * BEAT) / 0.5)
    y += s(20)
    y = put_para(f, layer, "19 effects in all.", round(80 * z), L.margin, y, width, k, fill=NEON, rise=k)
    put_para(f, layer, "Your original files are never touched.", round(50 * z), L.margin, y + s(10), width, k,
             "seguisb.ttf", WHITE, rise=k)


def shot_outro(f, L, layer, t):
    title_card(f, L, layer, t, bar(14), None,
               [("Windows  ·  Open source", False), ("reactorcore.itch.io", True)])


SHOTS = [  # (start, end, draw); shots fade in/out over 0.3 s
    (0.0, bar(1), lambda f, L, l, t, d: shot_title(f, L, l, t)),
    (bar(1), bar(4), shot_before),
    (bar(4), bar(5), lambda f, L, l, t, d: shot_click(f, L, l, t)),
    (bar(5), bar(8), shot_after),
    (bar(8), bar(12), shot_ladder),
    (bar(12), bar(14), lambda f, L, l, t, d: shot_effects(f, L, l, t)),
    (bar(14), END + 1, lambda f, L, l, t, d: shot_outro(f, L, l, t)),
]


def drift(px, dx, dy, W, H):
    """Crop W x H at a fractional offset, blending the four neighbouring whole-pixel crops.
    A whole-pixel crop steps once every few frames at this speed and reads as jitter (Pillow's
    affine transform does the same: it rounds pure translations). The background is so blurred
    that a 0.1 px move changes no 8-bit value either, until whole bands flip at once, so ±1 level
    of noise dithers the rounding; the encoder's grain tune keeps it."""
    x, y = int(dx), int(dy)
    fx, fy = dx - x, dy - y
    c = lambda i, j: px[y + j:y + j + H, x + i:x + i + W]
    top = c(0, 0) * (1 - fx) + c(1, 0) * fx
    bot = c(0, 1) * (1 - fx) + c(1, 1) * fx
    v = top * (1 - fy) + bot * fy
    v += (DITHER.random((H, W), np.float32) - DITHER.random((H, W), np.float32))[..., None]
    return np.clip(v + 0.5, 0, 255).astype(np.uint8)


def frame(f, L, t, data):
    W, H = f.W, f.H
    dx = (f.bg.width - W - 2) * min(t / END, 1)
    dy = (f.bg.height - H - 2) * (0.5 + 0.5 * np.sin(t / END * np.pi)) / 2
    canvas = Image.fromarray(drift(f.bg_px, dx, dy, W, H)).convert("RGBA")
    for a, b, draw in SHOTS:
        k = env(t, a, b, 0.0 if a == 0 else 0.3, 0.3)
        if k <= 0:
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw(f, L, layer, t, data)
        if k < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
        canvas.alpha_composite(layer)
    out = canvas.convert("RGB")
    fade = min(1.0, t / 0.5, (END - t) / 1.2)
    if fade < 1:
        out = Image.blend(Image.new("RGB", out.size, (0, 0, 0)), out, max(0.0, fade))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--still", type=float, nargs="*", help="only save stills at these times")
    a = ap.parse_args()
    W, H = (1080, 1920) if a.shorts else (1920, 1080)
    if a.draft:
        W, H = W * 4 // 9 // 2 * 2, H * 4 // 9 // 2 * 2
    f = Frame(W, H)
    L = Layout(f)
    data = {
        "before": [envelope(WORK / "before" / f"{st}.wav", L.lane_w, LANE_SPAN, BEFORE_GAIN_DB) for st, _ in SOUNDS],
        "after": [envelope(after_file(st), L.lane_w, LANE_SPAN) for st, _ in SOUNDS],
        "ladder": {tg: envelope(rung_file(tg), W - 2 * L.margin - f.s(60), VOICE_SPAN) for tg, _, tl in PLAYED},
    }
    name = "trailer_shorts" if a.shorts else "trailer_16x9"
    if a.still is not None:
        for t in a.still:
            frame(f, L, t, data).save(WORK / f"still_{name}_{t:05.2f}.png")
        return
    mix = WORK / "mix.wav"
    build_mix(mix)
    out = HERE / f"{name}{'_draft' if a.draft else ''}.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(mix),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-tune", "grain", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    total = int(END * FPS)
    for i in range(total):
        enc.stdin.write(frame(f, L, i / FPS, data).tobytes())
        if i % (FPS * 5) == 0:
            print(f"{i / FPS:5.1f} / {END:.1f} s", flush=True)
    enc.stdin.close()
    enc.wait()
    print(out)


if __name__ == "__main__":
    main()
