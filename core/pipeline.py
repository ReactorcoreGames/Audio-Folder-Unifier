"""The batch: scan and measure the folder, then process each file in the spec's order.

    1. (optional) remove silent parts  → temp WAV
    2. (optional) apply the effect     → temp WAV
    3. measure                         ← the result of 1-2, never the original
    4. gain / loudnorm + encode        → output file

Measuring after the effect is what keeps every effect from breaking the loudness match.
UI-free: the GUI's worker thread calls scan() and run_batch() and passes callbacks; Stop is
runner.cancel(), which kills the FFmpeg call in flight and makes the batch end after it.
"""

import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.effects import NO_EFFECT, apply_effect
from core.measure import FFmpegError, find_quiet, measure_rms_peak, probe
from core.naming import output_name
from core.normalize import TARGET_RMS_PEAK_DB, normalize_file
from core.scan import scan_folder
from core.silence import remove_silence
from utils.ffmpeg import Cancelled, FFmpegRunner

Log = Callable[[str], None]
Progress = Callable[[int, int, str], None]   # (done, total, current file name)

MIN_FREE_BYTES = 20_000_000   # below this the output disk counts as full


@dataclass
class Settings:
    """Mirrors utils.config.DEFAULT_CONFIG."""
    input_dir: Path
    output_dir: Path
    include_subfolders: bool = False
    category: str = "sfx"
    effect: str = NO_EFFECT
    silence: str = "keep"       # keep / ends / all
    quiet_only: bool = False
    output_format: str = "same"


@dataclass
class ScanReport:
    files: list[Path] = field(default_factory=list)
    skipped_own: list[Path] = field(default_factory=list)
    rms_peaks: dict[Path, float | None] = field(default_factory=dict)
    unreadable: dict[Path, str] = field(default_factory=dict)   # path → reason, from the scan
    quiet: set[Path] | None = None    # None: fewer than 5 files, too few to judge

    def summary(self) -> str:
        """The scan summary line: "Found 47 audio files · 6 look unusually quiet"."""
        n = len(self.files)
        if n == 0:
            return "No audio files found in this folder"
        line = f"Found {n} audio file{'s' if n != 1 else ''}"
        if self.quiet is not None:
            q = len(self.quiet)
            line += f" · {q or 'none'} look{'s' if q == 1 else ''} unusually quiet"
        return line


@dataclass
class BatchSummary:
    succeeded: int = 0
    failed: int = 0
    stopped: bool = False
    problem: str | None = None   # why it stopped, when it wasn't the Stop button

    def stop_for(self, problem: str, log: Log) -> None:
        self.stopped, self.problem = True, problem
        log(f"{problem}\nThe batch stopped.")

    def __str__(self) -> str:
        text = f"{self.succeeded} succeeded, {self.failed} failed"
        return text + ", stopped before the end" if self.stopped else text


def check_output_dir(output_dir: Path) -> str | None:
    """None if output_dir can be created and written to, else a message for the user.
    Run before starting, so an unwritable folder doesn't fail every file one by one.
    Not tempfile: on Windows it takes "access denied" for a name clash and retries up to
    os.TMP_MAX (2^31) names, which hangs on a folder the user may not write to."""
    probe_file = output_dir / f".afu_write_test_{uuid.uuid4().hex}"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with probe_file.open("xb"):
            pass
        probe_file.unlink()
    except PermissionError:
        return f"Can't write to the output folder:\n{output_dir}\n\nWindows doesn't allow saving files there."
    except OSError as e:
        return f"Can't write to the output folder:\n{output_dir}\n\n{e.strerror or e}"
    return None


def _folder_problem(settings: Settings) -> str | None:
    """Asked when a file is missing or fails: is it the folders rather than the file? Then
    every remaining file would fail the same way, so the batch stops instead.
    The From folder is checked first: check_output_dir() creates missing folders, and with
    To inside From it would bring a deleted From folder back."""
    if not settings.input_dir.is_dir():
        return f"The From folder is gone (moved, renamed or deleted?):\n{settings.input_dir}"
    problem = check_output_dir(settings.output_dir)
    if problem:
        return problem
    if shutil.disk_usage(settings.output_dir).free < MIN_FREE_BYTES:
        return f"The disk with the output folder is full:\n{settings.output_dir}"
    return None


def scan(settings: Settings, runner: FFmpegRunner, progress: Progress | None = None) -> ScanReport:
    """Find the files and measure each one's RMS peak for the quiet check. A file that can't be
    read is kept in the list (processing logs the failure) and noted in .unreadable.
    Raises Cancelled if Stop is pressed mid-scan."""
    found = scan_folder(settings.input_dir, settings.output_dir, settings.include_subfolders)
    report = ScanReport(files=found.files, skipped_own=found.skipped_own)
    total = len(report.files)
    for i, path in enumerate(report.files):
        if progress:
            progress(i, total, path.name)
        try:
            report.rms_peaks[path] = measure_rms_peak(path, runner)[0]
        except FFmpegError as e:
            if not settings.input_dir.is_dir():
                raise FileNotFoundError("the From folder is gone (moved, renamed or deleted?)")
            report.unreadable[path] = str(e)
    if progress and total:
        progress(total, total, "")
    report.quiet = find_quiet(report.rms_peaks)
    return report


def output_path(source: Path, settings: Settings) -> Path:
    """Mirrors the input's subfolders: input/metal/clang.wav → output/metal/clang_sfx.wav."""
    rel_dir = source.parent.relative_to(settings.input_dir)
    name = output_name(source, settings.category, settings.effect, settings.silence,
                       settings.output_format)
    return settings.output_dir / rel_dir / name


def process_file(source: Path, output: Path, settings: Settings, runner: FFmpegRunner,
                 temp_dir: Path, rms_peak: float | None = None) -> str:
    """Steps 1-4 for one file; rms_peak is the scan's measurement, for the silence threshold.
    Returns the detail for its log line. Raises FFmpegError, Cancelled, or OSError (disk
    full etc.). Temp files are removed before returning."""
    info = probe(source, runner)
    work, notes, temps = source, [], []
    try:
        if settings.silence != "keep":
            trimmed = temp_dir / "1_trimmed.wav"
            temps.append(trimmed)
            before, after = remove_silence(work, trimmed, info, runner, rms_peak,
                                           ends_only=settings.silence == "ends")
            work = trimmed
            notes.append(f"silence {before:.1f} → {after:.1f} s" if after < before - 0.05
                         else "no silence to remove")
        if settings.effect != NO_EFFECT:
            effected = temp_dir / "2_effect.wav"
            temps.append(effected)
            # At the target level first, so the effect hits a quiet file as hard as a loud one
            level = 0.0 if rms_peak is None else TARGET_RMS_PEAK_DB - rms_peak
            apply_effect(work, effected, settings.effect, info.sample_rate, runner, level)
            work = effected
        if work is not source:
            info = probe(work, runner)   # trimming changes the duration: the under-3 s rule
        result = normalize_file(work, output, settings.category, runner, info)
    finally:
        for path in temps:
            path.unlink(missing_ok=True)
    if result.fell_back:
        notes.append("too short for loudness matching, used sound-effect method instead")
    return ", ".join([result.detail, *notes])


def run_batch(settings: Settings, report: ScanReport, runner: FFmpegRunner, log: Log,
              progress: Progress | None = None) -> BatchSummary:
    """Process the scanned files. Per-file errors are logged and the batch goes on, unless
    the folders are the cause (_folder_problem()); Stop (runner.cancel()) ends it after
    deleting the half-written output."""
    files = report.files
    if settings.quiet_only and report.quiet is not None:
        files = [f for f in files if f in report.quiet]
        log(f"Only fixing the {len(files)} unusually quiet file{'s' if len(files) != 1 else ''}")
    summary = BatchSummary()
    claimed: dict[str, Path] = {}   # output path (case-folded) → the source writing it
    total = len(files)

    with tempfile.TemporaryDirectory(prefix="afu_") as tmp:
        for i, source in enumerate(files):
            if runner.cancelled:
                summary.stopped = True
                break
            rel = source.relative_to(settings.input_dir)
            if progress:
                progress(i, total, str(rel))
            if not source.is_file():
                if problem := _folder_problem(settings):
                    summary.stop_for(problem, log)
                    break
                rest = files[i + 1:]
                if rest and not any(f.is_file() for f in rest):
                    # Deleting a folder mid-run can't remove the file FFmpeg has open, so the
                    # folder itself often survives with one file in it
                    summary.stop_for("The rest of the files are gone from the From folder "
                                     f"(moved or deleted?):\n{settings.input_dir}", log)
                    break
                summary.failed += 1
                log(f"{rel}: FAILED, the file is gone (moved, renamed or deleted since the check)")
                continue
            output = output_path(source, settings)
            key = os.path.normcase(str(output))
            if key in claimed:
                # door.wav and door.mp3 both become door_sfx.wav with a forced output format
                summary.failed += 1
                log(f"{rel}: FAILED, same output name as {claimed[key].name} ({output.name}). "
                    f"Rename one of them, or keep the original format.")
                continue
            claimed[key] = source
            if output.exists() and not os.access(output, os.W_OK):
                summary.failed += 1
                log(f"{rel}: FAILED, {output.name} is already in the To folder and is read-only, "
                    f"so it can't be replaced")
                continue
            file_tmp = Path(tmp) / str(i)
            file_tmp.mkdir()
            try:
                detail = process_file(source, output, settings, runner, file_tmp,
                                      report.rms_peaks.get(source))
            except Cancelled:
                summary.stopped = True
                log(f"{rel}: stopped")
                break
            except Exception as e:   # FFmpeg, disk full, permissions, a decode numpy can't shape...
                summary.failed += 1
                log(f"{rel}: FAILED, {e}")
                if isinstance(e, FFmpegError) and e.stderr_tail:
                    log("    " + e.stderr_tail.replace("\n", "\n    "))
                if problem := _folder_problem(settings):
                    summary.stop_for(problem, log)
                    break
            else:
                summary.succeeded += 1
                log(f"{rel} → {output.name}: {detail}")
            finally:
                try:
                    file_tmp.rmdir()
                except OSError:
                    pass
        else:
            if progress:
                progress(total, total, "")
    log(str(summary))
    return summary
