"""Quick checks for core effects / silence / pipeline on generated sample files.

Run from the project root: python test/check_pipeline.py
Plain asserts; prints one line per check. Needs ffmpeg + ffprobe on PATH.
"""

import sys
import tempfile
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")   # log lines contain "→"; the Windows console is cp1252

from core.effects import BY_TAG, EFFECTS, NO_EFFECT, apply_effect, describe, dropdown_rows, filter_chain
from core.measure import measure_rms_peak, probe
from core.naming import EFFECT_TAGS
from core.normalize import TARGET_RMS_PEAK_DB
from core.pipeline import Settings, check_output_dir, run_batch, scan
from core.silence import Slicer, _get_rms_strided, get_rms, remove_silence, silence_threshold
from utils.ffmpeg import FFmpegRunner

runner = FFmpegRunner()
SR = 44100


def ok(msg):
    print(f"  ok  {msg}")


def tone(seconds, level=0.3, freq=440.0):
    t = np.arange(int(SR * seconds)) / SR
    return (level * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(seconds):
    return np.zeros(int(SR * seconds), np.float32)


def write(path: Path, audio):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, SR)


def check_effects(tmp: Path):
    print("effects")
    assert tuple(BY_TAG) == EFFECT_TAGS
    rows = dropdown_rows()
    assert rows[0][1] == NO_EFFECT and sum(1 for _, tag in rows if tag is None) == 3
    assert [tag for _, tag in rows if tag][1:7] == ["nes", "snes", "ps1", "n64", "saturn", "ps2"]
    for e in EFFECTS:
        assert len(e.description) <= 300, (e.tag, len(e.description))
    assert len(describe(NO_EFFECT)) <= 300
    ok("registry matches naming.EFFECT_TAGS, ladder order, 3 headers, descriptions ≤300 chars")

    src = tmp / "fx_src.wav"
    write(src, np.stack([tone(1.5), tone(1.5, 0.2, 660)], axis=1))
    for e in EFFECTS:
        dest = tmp / f"fx_{e.tag}.wav"
        apply_effect(src, dest, e.tag, SR, runner)
        info = probe(dest, runner)
        assert info.sample_rate == SR and info.channels == 2, (e.tag, info)
        assert 1.45 < info.duration < 2.7, (e.tag, info.duration)   # aecho adds its longest delay as a tail
        assert np.isfinite(sf.read(str(dest))[0]).all(), e.tag
    ok(f"all {len(EFFECTS)} chains run in FFmpeg, keep rate, channels and length (+ echo tails), no NaN")
    # Unpatched, vibrato's first samples differed run to run and were sometimes NaN
    runs = set()
    for _ in range(8):
        apply_effect(src, tmp / "fx_again.wav", "tape", SR, runner)
        runs.add((tmp / "fx_again.wav").read_bytes())
    assert len(runs) == 1, f"tape gave {len(runs)} different results"
    ok("vibrato chains give the same result every run")
    chain = filter_chain("n64", 24000, -6.5)
    assert chain.startswith("volume=-6.50dB,aresample=44100,") and chain.endswith(",aresample=24000"), chain
    ok("level first, Group A works at 44.1 kHz and returns to the source rate")


def check_silence(tmp: Path):
    print("silence")
    rng = np.random.default_rng(1)
    for n in (100, 4000, 123457, 882 * 1024 * 3 + 17):   # the last spans several RMS blocks
        y = rng.standard_normal(n).astype(np.float32)
        for frame, hop in ((3528, 882), (2048, 512), (7, 3)):
            padded = np.pad(y, (frame // 2, frame // 2))
            if padded.shape[-1] >= frame:
                assert np.allclose(get_rms(y, frame_length=frame, hop_length=hop),
                                   _get_rms_strided(padded, frame, hop), atol=1e-5)
    ok("low-memory get_rms matches slicer2.py's strided version")

    s = Slicer(SR, -40, 3000, 300, 20, 500)
    assert len(s.slice(np.concatenate([silence(0.8), tone(0.3), silence(1.5)]))) == 1
    ok("(why min_length is 300) the prototype's 3000 leaves a 2.6 s padded blip untouched")

    blip = tmp / "sil_blip.wav"
    write(blip, np.stack([np.concatenate([silence(0.8), tone(0.3), silence(1.5)])] * 2, axis=1))
    before, after = remove_silence(blip, tmp / "sil_blip_out.wav", probe(blip, runner), runner)
    out = sf.read(str(tmp / "sil_blip_out.wav"))[0]
    assert before > 2.5 and after < 1.0 and out.ndim == 2, (before, after, out.shape)
    ok(f"padded stereo blip: {before:.2f} → {after:.2f} s, still stereo")

    pauses = tmp / "sil_pauses.wav"
    write(pauses, np.concatenate([tone(1), silence(0.4), tone(1), silence(2), tone(1)]))
    before, after = remove_silence(pauses, tmp / "sil_pauses_out.wav", probe(pauses, runner), runner)
    assert 3.6 < after < 4.1, after   # the 0.4 s pause survives, the 2 s one shrinks to ~0.5
    ok(f"short pause kept, long pause shortened: {before:.1f} → {after:.1f} s")

    edges = tmp / "sil_edges.wav"
    write(edges, np.concatenate([silence(1.5), tone(1), silence(2), tone(1), silence(1.5)]))
    before, after = remove_silence(edges, tmp / "sil_edges_out.wav", probe(edges, runner), runner,
                                   ends_only=True)
    assert 4.1 < after < 4.4, after   # 4 s of sound and pause, plus 0.1 s kept at each end
    ok(f"trim the start and end: {before:.1f} → {after:.1f} s, the 2 s pause inside kept")

    quiet = tmp / "sil_quiet.wav"   # soft passage at -46 dBFS in a quiet file isn't silence
    write(quiet, np.concatenate([tone(2, 0.05), tone(2, 0.005), tone(2, 0.05)]))
    rms_peak = measure_rms_peak(quiet, runner)[0]
    assert silence_threshold(rms_peak) < -50 and silence_threshold(-8.0) == -40.0
    before, after = remove_silence(quiet, tmp / "sil_quiet_out.wav", probe(quiet, runner), runner, rms_peak)
    assert after > before - 0.1, (before, after)
    ok(f"quiet file's soft passage kept (threshold {silence_threshold(rms_peak):.0f} dB)")

    empty = tmp / "sil_empty.wav"
    write(empty, silence(4))
    before, after = remove_silence(empty, tmp / "sil_empty_out.wav", probe(empty, runner), runner)
    assert after > 0 and (tmp / "sil_empty_out.wav").exists()
    ok(f"all-silent file still written ({after:.1f} s)")


def make_folder(root: Path):
    write(root / "blip.wav", np.concatenate([silence(0.5), tone(0.3, 0.05), silence(1.0)]))
    write(root / "tone.wav", tone(6, 0.1))
    write(root / "loud.wav", tone(1, 0.9))
    write(root / "mid.wav", tone(1, 0.3))
    write(root / "whisper.wav", tone(1, 0.003))
    write(root / "sub" / "deep.wav", tone(4, 0.2, 220))
    write(root / "silent.wav", silence(2))
    (root / "corrupt.wav").write_bytes(b"RIFF nope" * 20)


def check_pipeline(tmp: Path):
    print("pipeline (generated folder)")
    root = tmp / "batch_in"
    make_folder(root)
    out = root / "unified"
    assert check_output_dir(out) is None
    settings = Settings(root, out, include_subfolders=True, category="sfx", effect="brutal",
                        silence="all")
    report = scan(settings, runner)
    assert len(report.files) == 8 and report.quiet is not None
    assert [p.name for p in report.quiet] == ["whisper.wav"], report.quiet
    assert root / "corrupt.wav" in report.unreadable
    ok(report.summary())

    lines = []
    summary = run_batch(settings, report, runner, lines.append)
    assert (summary.succeeded, summary.failed, summary.stopped) == (7, 1, False), lines
    assert (out / "sub" / "deep_sfx_brutal_x.wav").exists()
    assert not list(Path(tempfile.gettempdir()).glob("afu_*/0"))
    for name in ("blip", "tone", "loud", "whisper"):
        rms = measure_rms_peak(out / f"{name}_sfx_brutal_x.wav", runner)[0]
        assert abs(rms - TARGET_RMS_PEAK_DB) < 0.5, (name, rms)
    ok("brutal + silence, sfx: every output at the target RMS peak (effect measured, not the original)")
    assert lines[-1] == "7 succeeded, 1 failed" and any("corrupt.wav: FAILED" in s for s in lines)
    ok(f"corrupt file logged, batch went on: {lines[-1]}")

    again = scan(settings, runner)
    assert len(again.files) == 8   # unified/ inside the input is never scanned
    ok("re-scan skips the output folder")

    quiet_lines = []
    quiet_settings = Settings(root, tmp / "quiet_out", category="music", quiet_only=True)
    s = run_batch(quiet_settings, scan(quiet_settings, runner), runner, quiet_lines.append)
    assert s.succeeded == 1 and (tmp / "quiet_out" / "whisper_music.wav").exists(), quiet_lines
    ok("quiet-only processes just the flagged file")

    clash = tmp / "clash_in"
    write(clash / "door.wav", tone(1))
    write(clash / "door.flac", tone(1))
    clash_lines = []
    clash_settings = Settings(clash, tmp / "clash_out", output_format="mp3")
    s = run_batch(clash_settings, scan(clash_settings, runner), runner, clash_lines.append)
    assert (s.succeeded, s.failed) == (1, 1) and "same output name" in "".join(clash_lines)
    ok("two inputs with the same output name: second one refused, not overwritten")


def check_cancel(tmp: Path):
    print("cancel")
    root = tmp / "cancel_in"
    for i in range(4):
        write(root / f"long{i}.wav", tone(60, 0.1))
    settings = Settings(root, tmp / "cancel_out", category="music", effect="tape")
    report = scan(settings, runner)
    lines = []
    timer = threading.Timer(1.5, runner.cancel)
    timer.start()
    summary = run_batch(settings, report, runner, lines.append)
    timer.cancel()
    runner.reset()
    assert summary.stopped and summary.succeeded < 4, lines
    leftovers = [p.name for p in (tmp / "cancel_out").rglob("*")] if (tmp / "cancel_out").exists() else []
    assert len(leftovers) == summary.succeeded, leftovers   # no half-written file
    ok(f"stopped mid-batch: {lines[-1]}, no half-written output")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="afu_check_") as d:
        tmp = Path(d)
        check_effects(tmp)
        check_silence(tmp)
        check_pipeline(tmp)
        check_cancel(tmp)
    print("all checks passed")
