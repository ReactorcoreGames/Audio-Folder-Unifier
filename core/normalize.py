"""Step 4: bring a file to its category's level and encode the output.

Sound effects (and anything under 3 s) get a static gain from the RMS peak; voice, music and
ambient get two-pass EBU loudnorm. Values from docs/presets.md.
"""

from dataclasses import dataclass
from pathlib import Path

from core.formats import encode_args
from core.measure import FFmpegError, ProbeInfo, measure_loudness, measure_rms_peak, probe, run_checked
from utils.ffmpeg import Cancelled, FFmpegRunner

TARGET_RMS_PEAK_DB = -13.0    # loudest ~50 ms window lands here for every file
TRUE_PEAK_CEILING_DB = -1.0   # gain is clamped so samples never exceed this
SHORT_FILE_SECONDS = 3.0      # loudnorm needs several seconds; shorter files use RMS peak

# Category tag → loudnorm targets (I, LRA, TP), or None for the RMS-peak method
LOUDNORM_TARGETS = {
    "sfx": None,
    "voice": (-16.0, 11.0, -1.5),
    "music": (-14.0, 11.0, -1.0),
    "ambient": (-20.0, 15.0, -1.5),
}

# The ranges loudnorm's second pass accepts. A file clipped hard enough measures above
# 0 LUFS (a mastered track pushed 12 dB into clipping: +0.2), and the pass refuses to start
MEASURED_RANGES = {
    "measured_I": (-99.0, 0.0),
    "measured_TP": (-99.0, 99.0),
    "measured_LRA": (0.0, 99.0),
    "measured_thresh": (-99.0, 0.0),
    "offset": (-99.0, 99.0),
}


@dataclass
class NormalizeResult:
    method: str              # "rms" or "loudnorm"
    detail: str              # for the log: "+4.2 dB" or "-23.1 → -16 LUFS"
    silent: bool = False     # nothing to measure; written without a level change
    fell_back: bool = False  # loudnorm category, but too short, so RMS peak was used


def rms_gain(rms_peak: float | None, max_peak: float | None) -> float:
    """Gain that puts the RMS peak at the target without pushing the true peak past the
    ceiling. A silent file (rms_peak None) gets 0."""
    gain = 0.0 if rms_peak is None else TARGET_RMS_PEAK_DB - rms_peak
    if max_peak is not None:
        gain = min(gain, TRUE_PEAK_CEILING_DB - max_peak)
    return gain


def _encode(work: Path, output: Path, audio_filter: str, runner: FFmpegRunner) -> None:
    """-map 0:a:0 keeps only the audio: an mp3's cover art would otherwise become a video
    stream in the output (a Theora video inside an .ogg). A failed or stopped encode leaves
    a truncated file behind, so it's removed."""
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_checked(runner, [
            "ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(work), "-map", "0:a:0",
            "-af", audio_filter, *encode_args(output.suffix), str(output),
        ], "Writing the output")
    except (FFmpegError, Cancelled):
        try:
            output.unlink(missing_ok=True)
        except OSError:   # FFmpeg couldn't open it either; its own message says why
            pass
        raise


def normalize_file(work: Path, output: Path, category: str, runner: FFmpegRunner,
                   info: ProbeInfo | None = None) -> NormalizeResult:
    """Measure `work` (the original, or the result of silence removal / effects) and write
    the level-matched `output`. Raises FFmpegError or Cancelled."""
    if info is None:
        info = probe(work, runner)
    targets = LOUDNORM_TARGETS[category]
    fell_back = targets is not None and info.duration < SHORT_FILE_SECONDS

    if targets is None or fell_back:
        rms_peak, max_peak = measure_rms_peak(work, runner)
        gain = rms_gain(rms_peak, max_peak)
        _encode(work, output, f"volume={gain:.2f}dB", runner)
        detail = "silent, left as is" if rms_peak is None else f"{gain:+.1f} dB"
        return NormalizeResult("rms", detail, silent=rms_peak is None, fell_back=fell_back)

    target_i, target_lra, target_tp = targets
    measured = measure_loudness(work, runner, target_i, target_lra, target_tp)
    if measured is None:
        _encode(work, output, "volume=0dB", runner)
        return NormalizeResult("loudnorm", "silent, left as is", silent=True)
    # loudnorm works at 192 kHz internally and outputs that; resample back to the source rate
    second_pass = ":".join(
        [f"loudnorm=I={target_i}", f"LRA={target_lra}", f"TP={target_tp}"]
        + [f"{key}={min(max(value, MEASURED_RANGES[key][0]), MEASURED_RANGES[key][1])}"
           for key, value in measured.items()]
    )
    _encode(work, output, f"{second_pass},aresample={info.sample_rate or 48000}", runner)
    return NormalizeResult("loudnorm", f"{measured['measured_I']:.1f} → {target_i:g} LUFS")
