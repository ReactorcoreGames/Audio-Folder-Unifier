"""Measure every Session 5 output and build the listening files.

    python test/session5_runs.py      (first)
    python test/session5_report.py [folder in shots/, default session5] [earlier round to compare]

shots/session5/report.md    peak / clip / true peak / loudness of every output, per run
shots/session5/listen/      back-to-back comparison files for the listening tests
"""

import re
import subprocess
import sys
from pathlib import Path
from statistics import median

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from core.formats import AUDIO_EXTS  # noqa: E402
from core.measure import measure_rms_peak, probe  # noqa: E402
from core.silence import (HOP_SIZE_MS, MAX_SIL_KEPT_MS, MIN_INTERVAL_MS, MIN_LENGTH_MS,  # noqa: E402
                          Slicer, load_pcm, silence_threshold)
from utils.ffmpeg import FFmpegRunner  # noqa: E402

OUT = ROOT / "shots" / (sys.argv[1] if len(sys.argv) > 1 else "session5")
BEFORE = ROOT / "shots" / sys.argv[2] if len(sys.argv) > 2 else None
LISTEN = OUT / "listen"
SAMPLES = ROOT / "test" / "session5_samples"
runner = FFmpegRunner()
CLIP = 0.9999      # a sample at or above this is counted as clipped


def measure(path: Path) -> dict:
    """Sample peak and clipped-sample count from the decoded PCM, true peak and integrated
    loudness from ebur128, RMS peak from astats (the program's own measurement)."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(pcm, dtype=np.float32))
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                          "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", err)
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    rms, _ = measure_rms_peak(path, runner)
    peak = float(x.max()) if x.size else 0.0
    return {
        "dur": x.size and probe(path, runner).duration,
        "peak": 20 * np.log10(peak) if peak > 0 else float("-inf"),
        "clipped": int((x >= CLIP).sum()),
        "tp": float(tp[-1]) if tp else float("-inf"),
        "lufs": float(lufs[-1]) if lufs else float("-inf"),
        "rms": rms if rms is not None else float("-inf"),
    }


def fmt(v, nd=1):
    return "silent" if v == float("-inf") else f"{v:.{nd}f}"


def audio_files(folder: Path):
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTS)


def table(rows, ceiling=-1.0):
    lines = ["| File | Length s | Sample peak dBFS | Clipped samples | True peak dBTP | LUFS | RMS peak dBFS | |",
             "|---|---|---|---|---|---|---|---|"]
    flags = 0
    for name, m in rows:
        bad = m["clipped"] > 0 or m["tp"] > ceiling + 0.3
        flags += bad
        lines.append(f"| {name} | {m['dur']:.1f} | {fmt(m['peak'])} | {m['clipped']} | {fmt(m['tp'])} "
                     f"| {fmt(m['lufs'])} | {fmt(m['rms'])} | {'**CHECK**' if bad else 'ok'} |")
    return lines, flags


def spread(rows, key, min_dur=0.0):
    vals = [m[key] for _, m in rows if m[key] != float("-inf") and m["dur"] >= min_dur]
    return f"{max(vals) - min(vals):.1f} dB across {len(vals)} files" if len(vals) > 1 else "n/a"


def concat(parts: list[Path], out: Path, gap=0.7, max_s=None):
    """Back to back with a short gap, all at 44.1 kHz stereo so any mix of inputs joins.
    max_s cuts each part to its first seconds."""
    args, chains = [], []
    for i, p in enumerate(parts):
        args += ["-i", str(p)]
        trim = f"atrim=end={max_s}," if max_s else ""
        chains.append(f"[{i}:a:0]{trim}aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                      f"apad=pad_dur={gap}[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(parts))) + \
        f"concat=n={len(parts)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", graph, "-map", "[out]",
                    "-c:a", "pcm_s16le", str(out)], check=True)


def build_listening():
    LISTEN.mkdir(exist_ok=True)
    fx = {d.name.split("_", 1)[1]: d for d in (OUT / "3_effects").iterdir() if d.is_dir()}
    sources = {"speech": "speech", "music": "music", "rifleshot": "heavybeamrifleshot",
               "transform24k": "Transform your audio into hellish masterpieces"}

    def pick(tag, stem):
        return next(fx[tag].glob(f"{stem}_sfx*"))

    order = []
    for key, stem in sources.items():
        sets = {"1_ladder": ["none", "nes", "snes", "ps1", "n64", "saturn", "ps2"],
                "2_n64_saturn_ps2": ["none", "n64", "saturn", "ps2"],
                "3_gritty_brutal": ["none", "gritty", "brutal", "nes"]}
        for name, tags in sets.items():
            out = LISTEN / f"{name}_{key}.wav"
            concat([pick(t, stem) for t in tags], out)
            order.append((out.name, " → ".join("original" if t == "none" else t for t in tags)))
    # Every dropdown entry in order, the first 6 s of each
    tags = [d.name.split("_", 1)[1] for d in sorted((OUT / "3_effects").iterdir()) if d.is_dir()]
    for key in ("speech", "music", "rifleshot"):
        out = LISTEN / f"0_tour_{key}.wav"
        concat([pick(t, sources[key]) for t in tags], out, max_s=6)
        order.insert(0, (out.name, "every entry in dropdown order, 6 s each: " + ", ".join(tags)))
    if BEFORE:
        # Each effect that changed: as it was in the earlier round, then as it is now
        old = {d.name.split("_", 1)[1]: d for d in (BEFORE / "3_effects").iterdir() if d.is_dir()}
        both = [t for t in tags if t in old and t != "none"
                and pick(t, sources["speech"]).read_bytes() != next(old[t].glob(f"{sources['speech']}_sfx*")).read_bytes()]
        for key in ("speech", "music", "rifleshot"):
            out = LISTEN / f"0_before_after_{key}.wav"
            parts = []
            for t in both:
                parts += [next(old[t].glob(f"{sources[key]}_sfx*")), pick(t, sources[key])]
            concat(parts, out, max_s=6)
            order.insert(0, (out.name, f"each effect before, then after ({BEFORE.name} → {OUT.name}): "
                             + ", ".join(both)))
    return order


def silence_cuts():
    """What "Remove silent parts" took out of chillnew.mp3: timestamps, and the cut audio
    on its own (boosted so it can be heard) in listen/4_chillnew_removed_parts.wav."""
    src = SAMPLES / "chillnew.mp3"
    info = probe(src, runner)
    rms, _ = measure_rms_peak(src, runner)
    audio = load_pcm(src, info, runner)
    sr = info.sample_rate
    slicer = Slicer(sr=sr, threshold=silence_threshold(rms), min_length=MIN_LENGTH_MS,
                    min_interval=MIN_INTERVAL_MS, hop_size=HOP_SIZE_MS, max_sil_kept=MAX_SIL_KEPT_MS)
    chunks = [c for c in slicer.slice(audio) if c.shape[-1]]
    # The chunks are views of `audio`, so their memory offset over the sample stride gives their start
    base, item = audio.ctypes.data, audio.strides[-1]
    kept = [((c.ctypes.data - base) // item, (c.ctypes.data - base) // item + c.shape[-1]) for c in chunks]
    total = audio.shape[-1]
    cuts, pos = [], 0
    for a, b in kept:
        if a > pos:
            cuts.append((pos, a))
        pos = b
    if pos < total:
        cuts.append((pos, total))
    pieces = [audio[..., a:b] for a, b in cuts]
    removed = np.concatenate(pieces, axis=-1)
    loudest = float(np.abs(removed).max())
    boost = 20 * np.log10(0.5 / loudest)   # loudest cut sample to -6 dBFS
    import soundfile as sf
    sf.write(str(LISTEN / "4_chillnew_removed_parts.wav"), (removed * 10 ** (boost / 20)).T, sr,
             subtype="PCM_16")
    cut_peaks = [20 * np.log10(max(float(np.abs(p).max()), 1e-9)) for p in pieces]
    return cuts, sr, boost, cut_peaks, silence_threshold(rms), 20 * np.log10(loudest)


def main():
    rep = ["# Session 5 results", "",
           "Every output measured from the decoded audio. **CHECK** = any sample at full scale "
           f"(≥ {CLIP}) or a true peak more than 0.3 dB over the -1 dBTP ceiling.", ""]
    total_flags = 0

    rep += ["## Inputs (test/session5_samples)", ""]
    inputs = []
    for p in audio_files(SAMPLES):
        try:
            inputs.append((p.name, measure(p)))
        except subprocess.CalledProcessError:
            rep.append(f"- {p.name}: can't be decoded (the corrupt test file)")
    lines, _ = table(inputs)
    rep += ["", *lines, "", f"RMS peak spread before: {spread(inputs, 'rms')}; "
            f"LUFS spread (≥3 s): {spread(inputs, 'lufs', 3.0)}", ""]

    runs = [d for d in sorted(OUT.iterdir()) if d.is_dir() and d.name[0] in "12"]
    runs += sorted(d for d in (OUT / "3_effects").iterdir() if d.is_dir())
    for d in runs:
        rows = [(p.name, measure(p)) for p in audio_files(d)]
        lines, flags = table(rows)
        total_flags += flags
        log = (d / "_log.txt").read_text(encoding="utf-8")
        summary = next((l for l in reversed(log.splitlines()) if "succeeded" in l), "?")
        rep += [f"## {d.relative_to(OUT).as_posix()}", "", f"Window: {summary}. "
                f"RMS peak spread: {spread(rows, 'rms')}; LUFS spread (≥3 s): {spread(rows, 'lufs', 3.0)}; "
                f"flagged: {flags}", "", *lines, ""]
        print(f"{d.relative_to(OUT).as_posix()}: {len(rows)} files, {flags} flagged", flush=True)

    order = build_listening()
    rep += ["## Listening files (listen/)", "", "Each is the clips back to back, 0.7 s apart:", ""]
    rep += [f"- `{name}`: {what}" for name, what in order]

    cuts, sr, boost, peaks, thr, loudest = silence_cuts()
    secs = sum(b - a for a, b in cuts) / sr
    rep += ["", "## chillnew.mp3, Remove silent parts", "",
            f"Threshold used: {thr:.1f} dBFS. {len(cuts)} cuts, {secs:.1f} s removed in total. "
            f"Loudest removed sample: {loudest:.1f} dBFS. `listen/4_chillnew_removed_parts.wav` "
            f"is all of it back to back, boosted {boost:+.1f} dB so it can be heard.", "",
            "| # | From | To | Length s | Peak dBFS |", "|---|---|---|---|---|"]
    mmss = lambda s: f"{int(s // 60)}:{s % 60:04.1f}"
    rep += [f"| {i + 1} | {mmss(a / sr)} | {mmss(b / sr)} | {(b - a) / sr:.1f} | {pk:.1f} |"
            for i, ((a, b), pk) in enumerate(zip(cuts, peaks))]

    rep[3:3] = [f"**Flagged outputs: {total_flags}.**", ""]
    (OUT / "report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"flagged {total_flags}; {OUT / 'report.md'}")


if __name__ == "__main__":
    main()
