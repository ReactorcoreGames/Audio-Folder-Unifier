"""Quick checks for core scan / measure / normalize on generated sample files.

Run from the project root: python test/check_core.py
Plain asserts; prints one line per check. Needs ffmpeg + ffprobe on PATH.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")   # log details contain "→"; the Windows console is cp1252

from core.measure import FFmpegError, find_quiet, measure_loudness, measure_rms_peak, probe
from core.naming import output_name, own_output_base
from core.normalize import TARGET_RMS_PEAK_DB, TRUE_PEAK_CEILING_DB, normalize_file, rms_gain
from core.scan import scan_folder
from utils.ffmpeg import Cancelled, FFmpegRunner

runner = FFmpegRunner()


def ok(msg):
    print(f"  ok  {msg}")


def gen(path: Path, source: str, seconds: float, rate: int = 44100):
    """source is an lavfi graph, e.g. "sine=f=440,volume=-30dB"."""
    proc = runner.run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i", f"{source}",
                       "-t", str(seconds), "-ar", str(rate), str(path)])
    assert proc.returncode == 0, proc.stderr[-500:]


def check_naming():
    print("naming")
    assert output_name(Path("explosion.wav"), "sfx", None, "keep") == "explosion_sfx.wav"
    assert output_name(Path("explosion.wav"), "sfx", "ps1", "all") == "explosion_sfx_ps1_x.wav"
    assert output_name(Path("explosion.wav"), "sfx", None, "ends") == "explosion_sfx_t.wav"
    assert output_name(Path("narration.mp3"), "voice", "none", "keep", "ogg") == "narration_voice.ogg"
    assert own_output_base(Path("explosion_sfx_ps1_x.wav")) == "explosion"
    assert own_output_base(Path("explosion_music_t.wav")) == "explosion"
    assert own_output_base(Path("my_music.mp3")) == "my"
    assert own_output_base(Path("explosion.wav")) is None
    assert own_output_base(Path("boss_ps1.wav")) is None   # effect tag without a category tag
    ok("output names and own-suffix detection")


def check_scan(tmp: Path):
    print("scan")
    root = tmp / "scan_in"
    out = root / "unified"
    for rel in ["a.wav", "B.mp3", "notes.txt", "door.wav", "door_sfx.wav", "lib_sfx.wav",
                "sub/c.flac", "unified/a_sfx.wav"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"")
    flat = scan_folder(root, out, recursive=False)
    assert [p.name for p in flat.files] == ["a.wav", "B.mp3", "door.wav", "lib_sfx.wav"], flat.files
    assert [p.name for p in flat.skipped_own] == ["door_sfx.wav"]
    ok("non-recursive: audio only, earlier output skipped, library _sfx kept")
    deep = scan_folder(root, out, recursive=True)
    assert [p.relative_to(root).as_posix() for p in deep.files][-1] == "sub/c.flac"
    assert not any("unified" in p.parts for p in deep.files)
    ok("recursive: subfolder found, output folder inside input skipped")


def check_math():
    print("gain math")
    assert rms_gain(-33.0, -30.0) == 20.0
    assert rms_gain(-30.0, -3.0) == 2.0          # clamped by the -1 dB ceiling
    assert rms_gain(None, None) == 0.0
    peaks = {Path(f"f{i}"): v for i, v in enumerate([-12, -13, -14, -15, -30, None])}
    assert find_quiet(peaks) == {Path("f4")}
    assert find_quiet(dict(list(peaks.items())[:4])) is None
    ok("RMS gain, ceiling clamp, quiet detection")


def check_normalize(tmp: Path):
    print("normalize (generated samples)")
    src, out = tmp / "src", tmp / "out"
    src.mkdir()
    blip, tone, silent, bad = src / "blip.wav", src / "tone.wav", src / "silent.wav", src / "bad.wav"
    gen(blip, "sine=f=1000,volume=-30dB", 0.2)
    gen(tone, "sine=f=440,volume=-30dB", 8)
    gen(silent, "anullsrc=r=44100:cl=mono", 5)
    bad.write_bytes(b"RIFF this is not really a wav file" * 10)

    r = normalize_file(blip, out / "blip_sfx.wav", "sfx", runner)
    rms, _ = measure_rms_peak(out / "blip_sfx.wav", runner)
    assert r.method == "rms" and abs(rms - TARGET_RMS_PEAK_DB) < 0.3, (r, rms)
    ok(f"short blip, sfx: {r.detail}, RMS peak now {rms:.1f}")

    r = normalize_file(blip, out / "blip_music.wav", "music", runner)
    assert r.fell_back and r.method == "rms", r
    ok("short blip, music: fell back to the RMS-peak method")

    for fmt in ("wav", "mp3"):
        dest = out / f"tone_music.{fmt}"
        r = normalize_file(tone, dest, "music", runner)
        lufs = measure_loudness(dest, runner, -14, 11, -1)["measured_I"]
        rate = probe(dest, runner).sample_rate
        assert r.method == "loudnorm" and abs(lufs + 14) < 0.5, (r, lufs)
        assert rate == 44100, rate
        ok(f"long tone, music -> .{fmt}: {r.detail}, now {lufs:.1f} LUFS at {rate} Hz")

    # Clipped into a square wave it measures above 0 LUFS, which loudnorm's 2nd pass rejects
    hot = src / "hot.wav"
    gen(hot, "sine=f=1000,volume=30dB,aformat=channel_layouts=stereo", 5)   # +2.7 LUFS
    dest = out / "hot_voice.wav"
    r = normalize_file(hot, dest, "voice", runner)
    lufs = measure_loudness(dest, runner, -16, 11, -1.5)["measured_I"]
    assert abs(lufs + 16) < 1.0, (r, lufs)
    ok(f"clipped file above 0 LUFS, voice: {r.detail}, now {lufs:.1f} LUFS")

    # A float temp with overs, as an effect leaves it: the ceiling must see above 0 dBFS
    over = src / "over.wav"
    # quiet tone + one +6 dBFS spike, so the ceiling (not the RMS target) sets the gain
    proc = runner.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                       r"aevalsrc=0.03*sin(2*PI*440*t)+if(between(t\,0.5\,0.5005)\,2\,0):s=44100:d=1",
                       "-c:a", "pcm_f32le", str(over)])
    assert proc.returncode == 0, proc.stderr[-300:]
    dest = out / "over_sfx.wav"
    normalize_file(over, dest, "sfx", runner)
    peak = measure_rms_peak(dest, runner)[1]
    assert peak <= TRUE_PEAK_CEILING_DB + 0.2, peak
    ok(f"float file peaking at +6 dBFS: output peak {peak:.1f} dB, under the ceiling")

    for cat in ("sfx", "ambient"):
        dest = out / f"silent_{cat}.wav"
        r = normalize_file(silent, dest, cat, runner)
        assert r.silent and dest.exists(), r
        ok(f"silent file, {cat}: {r.detail}")

    try:
        normalize_file(bad, out / "bad_sfx.wav", "sfx", runner)
        raise AssertionError("corrupt file should fail")
    except FFmpegError as e:
        assert not (out / "bad_sfx.wav").exists()
        ok(f"corrupt file: FFmpegError ({e}), no output left")

    runner.cancel()
    try:
        normalize_file(tone, out / "never.wav", "music", runner)
        raise AssertionError("cancelled runner should raise")
    except Cancelled:
        ok("cancelled runner raises Cancelled")
    finally:
        runner.reset()


def check_real_files(tmp: Path):
    """The author's samples, if present: mp3/ogg inputs, mixed rates, a cover-art check."""
    folder = Path(__file__).resolve().parent / "testfiles"
    found = scan_folder(folder, None, recursive=False).files if folder.is_dir() else []
    if not found:
        return
    print("normalize (test/testfiles, music category -> .ogg)")
    for path in found:
        dest = tmp / "real" / output_name(path, "music", None, False, "ogg")
        r = normalize_file(path, dest, "music", runner)
        note = "  (too short, RMS peak)" if r.fell_back else ""
        ok(f"{path.name}: {r.detail}{note}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="afu_check_") as d:
        tmp = Path(d)
        check_naming()
        check_scan(tmp)
        check_math()
        check_normalize(tmp)
        check_real_files(tmp)
    print("all checks passed")
