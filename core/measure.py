"""Measurements via ffprobe/ffmpeg: duration and format, RMS peak, EBU loudness.

Every call goes through utils.ffmpeg.FFmpegRunner so Stop can kill it mid-file.
"""

import json
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

from utils.ffmpeg import FFmpegRunner

QUIET_MARGIN_DB = 10.0     # flagged when this far below the folder's median RMS peak
QUIET_MIN_FILES = 5        # fewer files than this: no meaningful median, no flagging
LOUDNORM_SILENCE_LUFS = -70.0  # loudnorm's own gate; anything at or below is silence to it


class FFmpegError(Exception):
    """An ffmpeg/ffprobe call failed. str() is a short reason; .stderr_tail is for the log."""

    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr_tail = "\n".join(stderr.strip().splitlines()[-8:])


def run_checked(runner: FFmpegRunner, args: list[str], what: str, binary_stdout: bool = False):
    proc = runner.run(args, binary_stdout=binary_stdout)
    if proc.returncode != 0:
        raise FFmpegError(f"{what} failed", proc.stderr)
    return proc


@dataclass
class ProbeInfo:
    duration: float      # seconds; 0.0 if the container doesn't say
    sample_rate: int
    channels: int


def probe(path: Path, runner: FFmpegRunner) -> ProbeInfo:
    """Raises FFmpegError for files ffprobe can't read or that have no audio stream."""
    proc = run_checked(runner, [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels,duration:format=duration",
        "-of", "json", str(path),
    ], "Reading the file")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams") or []
    if not streams:
        raise FFmpegError("No audio found in the file", proc.stderr)
    stream = streams[0]

    def _num(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    duration = _num(data.get("format", {}).get("duration")) or _num(stream.get("duration"))
    return ProbeInfo(duration, int(_num(stream.get("sample_rate"))), int(_num(stream.get("channels"))))


def measure_rms_peak(path: Path, runner: FFmpegRunner) -> tuple[float | None, float | None]:
    """(rms_peak_db, max_peak_db), as audio_unifier.py's measure(). rms_peak is the loudest
    ~50 ms window across all channels; None means the file is silent. max_peak is the higher
    of the sample peak and the true peak (between samples), so the ceiling holds after
    playback and lossy encoding. Not volumedetect: it converts to 16-bit and can't see the
    overs above 0 dBFS that an effect leaves in a float temp file."""
    proc = run_checked(runner, [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", "astats,ebur128=peak=true:framelog=quiet", "-f", "null", "-",
    ], "Measuring")
    err = proc.stderr

    def highest(pattern):
        found = [float(v) for v in re.findall(pattern, err, re.MULTILINE) if v != "-inf"]
        return max(found) if found else None

    rms_peak = highest(r"RMS peak dB:\s*(-?[\d.]+|-inf)")
    peaks = [p for p in (highest(r"Peak level dB:\s*(-?[\d.]+|-inf)"),
                         highest(r"^\s+Peak:\s*(-?[\d.]+|-inf)\s*dBFS")) if p is not None]
    return rms_peak, max(peaks) if peaks else None


def measure_loudness(path: Path, runner: FFmpegRunner, target_i: float, target_lra: float,
                     target_tp: float) -> dict | None:
    """Loudnorm first pass. Returns the measured values to feed into the second pass
    (measured_I/TP/LRA/thresh, offset), or None if the file is silent to loudnorm."""
    proc = run_checked(runner, [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", f"loudnorm=I={target_i}:LRA={target_lra}:TP={target_tp}:print_format=json",
        "-f", "null", "-",
    ], "Measuring loudness")
    err = proc.stderr
    start, end = err.rfind("{"), err.rfind("}")
    if start < 0 or end < start:
        raise FFmpegError("Loudness measurement gave no result", err)
    stats = json.loads(err[start:end + 1])
    measured = {
        "measured_I": float(stats["input_i"]),
        "measured_TP": float(stats["input_tp"]),
        "measured_LRA": float(stats["input_lra"]),
        "measured_thresh": float(stats["input_thresh"]),
        "offset": float(stats["target_offset"]),
    }
    if not all(math.isfinite(v) for v in measured.values()) or measured["measured_I"] <= LOUDNORM_SILENCE_LUFS:
        return None
    return measured


def find_quiet(rms_peaks: dict[Path, float | None]) -> set[Path] | None:
    """Files whose RMS peak is more than QUIET_MARGIN_DB below the folder median. Relative,
    so a folder of deliberately quiet ambience doesn't flag everything. Silent files (None)
    are left out: there's nothing to fix. Returns None when there are too few files to judge."""
    measured = {p: v for p, v in rms_peaks.items() if v is not None}
    if len(measured) < QUIET_MIN_FILES:
        return None
    median = statistics.median(measured.values())
    return {p for p, v in measured.items() if v < median - QUIET_MARGIN_DB}
