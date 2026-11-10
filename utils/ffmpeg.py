"""FFmpeg on PATH: the startup check, hidden console windows, and a stoppable runner."""

import shutil
import subprocess
import sys
import threading

INSTALLER_URL = "https://reactorcore.itch.io/ffmpeg-to-path-installer"
FFMPEG_MISSING_MSG = (
    "FFMPEG not found in PATH. Please install FFMPEG.\n\n"
    f"You can use: {INSTALLER_URL}"
)


def ffmpeg_available() -> bool:
    """Both binaries are needed: ffmpeg does the work, ffprobe reads durations and formats."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _ffmpeg_startupinfo():
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si
    return None


def _kill_tree(proc) -> None:
    """terminate() alone isn't enough: ffmpeg on PATH is often a shim (Chocolatey, Scoop) that
    starts the real ffmpeg as a child. Killing only the shim leaves the child running and
    holding the pipes open, so the Stop button would wait for the whole file to finish."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True, startupinfo=_ffmpeg_startupinfo())
    else:
        proc.kill()


class Cancelled(Exception):
    """Raised by FFmpegRunner.run() once cancel() has been called."""


class FFmpegRunner:
    """Runs one ffmpeg/ffprobe process at a time and can kill it from another thread.

    The worker thread calls run(); the Stop button calls cancel(), which terminates the
    process in flight so a long file doesn't delay the stop. Every later run() raises
    Cancelled until reset() is called for the next batch.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def run(self, args, binary_stdout=False) -> subprocess.CompletedProcess:
        """args[0] is "ffmpeg" or "ffprobe". stderr is always text; stdout is text unless
        binary_stdout (raw PCM for the silence Slicer). Doesn't raise on a non-zero exit:
        the caller checks returncode and logs the stderr tail."""
        with self._lock:
            if self._cancelled:
                raise Cancelled()
            # stdin=DEVNULL: a windowed exe has no console stdin, and ffmpeg would try to read it
            proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=_ffmpeg_startupinfo(),
            )
            self._proc = proc
        try:
            out, err = proc.communicate()
        finally:
            with self._lock:
                self._proc = None
        if self._cancelled:
            raise Cancelled()
        stdout = out if binary_stdout else out.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(args, proc.returncode, stdout,
                                           err.decode("utf-8", errors="replace"))

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            if self._proc is not None and self._proc.poll() is None:
                _kill_tree(self._proc)

    def reset(self) -> None:
        with self._lock:
            self._cancelled = False
