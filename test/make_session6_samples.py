"""Build the Session 6 edge-case folders in test/session6_samples/ (gitignored).

    python test/make_session6_samples.py

    big/      600 short files in 6 subfolders: tones, noise and tones with gaps, 0.2-6 s,
              -40 to -6 dB, as WAV / MP3 / OGG / FLAC (the "very large batch")
    small/    40 files of 2-3 s (Stop and restart, the From folder vanishing mid-run)
    names/    awkward filenames: unicode, emoji, commas, quotes, %, a leading dash
    tree/     files at three depths (output inside input, with subfolders)
Seeded, so every build is the same. Skips folders that already exist.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test" / "session6_samples"
SR = 44100
FORMATS = [("wav", {}), ("mp3", {}), ("ogg", {}), ("flac", {})]

NAMES = ["über café.wav", "日本語 テスト.mp3", "a, b, c.wav", "it's [1] {x} 100%.ogg",
         "emoji 🎵 song.flac", "semi;colon=eq'q.wav", "-dash start.wav", "  two  spaces .wav",
         "%d percent %03d.mp3", "back`tick $var &amp.wav", "Ünï cödé, ñ (copy).m4a"]


def clip(rng, seconds, kind, level_db):
    n = max(1, int(SR * seconds))
    t = np.arange(n) / SR
    if kind == "noise":
        y = rng.standard_normal(n) * 0.3
    else:
        y = np.sin(2 * np.pi * rng.uniform(120, 2000) * t)
        if kind == "gaps":   # 0.7 s of sound, 0.8 s of silence, repeated
            y *= (t % 1.5) < 0.7
    y *= 10 ** (level_db / 20) / max(np.abs(y).max(), 1e-9)
    stereo = rng.random() < 0.5
    return np.stack([y, y * 0.8], axis=1) if stereo else y


def write(path: Path, audio):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".m4a":   # libsndfile can't write AAC
        wav = path.with_suffix(".tmp.wav")
        sf.write(str(wav), audio, SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), str(path)], check=True)
        wav.unlink()
    else:
        sf.write(str(path), audio.astype(np.float32), SR)


def build(name, make):
    folder = OUT / name
    if folder.exists():
        print(f"{name}/ exists, skipped")
        return
    make(folder, np.random.default_rng(len(name)))
    print(f"{name}/: {sum(1 for p in folder.rglob('*') if p.is_file())} files")


def make_big(folder, rng):
    for i in range(600):
        ext = FORMATS[i % 4][0]
        kind = ("tone", "noise", "gaps")[i % 3]
        seconds = rng.uniform(0.2, 6.0)
        write(folder / f"set {i // 100 + 1}" / f"clip_{i:03d}_{kind}.{ext}",
              clip(rng, seconds, kind, rng.uniform(-40, -6)))


def make_small(folder, rng):
    for i in range(40):
        write(folder / f"take_{i:02d}.{FORMATS[i % 4][0]}",
              clip(rng, rng.uniform(2.0, 3.0), ("tone", "gaps")[i % 2], rng.uniform(-30, -10)))


def make_names(folder, rng):
    for i, name in enumerate(NAMES):
        write(folder / name, clip(rng, 4.0, "tone", -6 - 2 * i))


def make_tree(folder, rng):
    for rel in ["top_a.wav", "top_b.mp3", "sub1/mid_a.wav", "sub1/mid_b.ogg",
                "sub2/deeper/low_a.flac", "sub2/deeper/low_b.wav"]:
        write(folder / rel, clip(rng, 2.5, "tone", rng.uniform(-30, -10)))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    build("big", make_big)
    build("small", make_small)
    build("names", make_names)
    build("tree", make_tree)


if __name__ == "__main__":
    main()
