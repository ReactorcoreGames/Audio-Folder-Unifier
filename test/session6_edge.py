"""Drive the real window through the Session 6 edge cases (checklist.md).

    python test/make_session6_samples.py      (first)
    python test/session6_edge.py [case ...]    (default: all of them, in this order)

Cases: ffmpeg, empty, names, nested, readonly, vanish, stop, big. Each works on copies in
test/session6_work/ (an earlier one is moved to C:\\trash). Message boxes are swapped for a
recorder so nothing waits for a click; "deleting" the From folder mid-run is a move to
C:\\trash. Prints ok / FAIL per check; screenshots and the big batch's numbers go to
shots/session6/. config.json is restored afterwards.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from tkinter import messagebox

import psutil
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from core.effects import NO_EFFECT  # noqa: E402
from gui import app as app_module  # noqa: E402
from gui.app import App  # noqa: E402
from utils.paths import app_dir  # noqa: E402

SAMPLES = ROOT / "test" / "session6_samples"
WORK = ROOT / "test" / "session6_work"
SHOTS = ROOT / "shots" / "session6"
TRASH = Path("C:/trash")
STAMP = time.strftime("%Y%m%d_%H%M%S")
failures = []


def check(cond, msg):
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}", flush=True)
    if not cond:
        failures.append(msg)


def to_trash(path: Path):
    TRASH.mkdir(exist_ok=True)
    path.rename(TRASH / f"afu_session6_{path.name}_{STAMP}_{time.time_ns() % 10**6}")


class Dialogs:
    """Stands in for tkinter.messagebox: records (kind, title, text), returns at once."""

    def __init__(self):
        self.calls = []
        for kind, answer in (("showinfo", "ok"), ("showwarning", "ok"), ("showerror", "ok"),
                             ("askyesno", False)):
            setattr(messagebox, kind, self._recorder(kind, answer))

    def _recorder(self, kind, answer):
        def record(title=None, message=None, **_):
            self.calls.append((kind, title, message or ""))
            return answer
        return record

    def take(self):
        calls, self.calls = self.calls, []
        return calls


class Driver:
    """Pumps the Tk event loop by hand and times every update(): the longest one is the
    longest the window was frozen."""

    def __init__(self, app):
        self.app = app
        self.lines = []
        window_log = app.log
        app.log = lambda text: (self.lines.append(text), window_log(text))
        self.update_times = []
        self.on_tick = None

    def until(self, cond, timeout, what):
        t0 = time.time()
        while not cond():
            if time.time() - t0 > timeout:
                raise TimeoutError(what)
            s = time.perf_counter()
            self.app.root.update()
            self.update_times.append(time.perf_counter() - s)
            if self.on_tick:
                self.on_tick()
            time.sleep(0.01)

    def sleep(self, seconds):
        end = time.time() + seconds
        self.until(lambda: time.time() > end, seconds + 1, "sleep")

    def idle(self):
        a = self.app
        return a.worker is None and a.pending is None and not a.running_batch

    def wait_idle(self, timeout=120, what="the job to end"):
        self.sleep(0.2)
        self.until(self.idle, timeout, what)
        self.sleep(0.2)   # let _poll() take the last messages

    def setup(self, src, out, subfolders=False, category="sfx", effect=NO_EFFECT,
              silence="keep", fmt="same", wait=True):
        """Set the controls like a user would, then let the automatic folder check finish."""
        a, v = self.app, self.app.vars
        v["input_dir"].set(str(src))
        v["output_dir"].set(str(out))
        v["include_subfolders"].set(subfolders)
        v["category"].set(category)
        v["silence"].set(silence)
        v["quiet_only"].set(False)
        v["output_format"].set(fmt)
        a.effect_box.current([t for _, t in a.effect_rows].index(effect))
        a._on_effect_selected()
        a.on_scan_settings_changed()
        if wait:
            self.wait_idle(what="the folder check")

    def run(self, timeout=300):
        """Press Start, wait for the batch; returns the log lines it wrote."""
        self.lines.clear()
        s = time.perf_counter()
        self.app.start()   # a button handler: it runs on the Tk thread too
        self.update_times.append(time.perf_counter() - s)
        self.wait_idle(timeout, "the batch")
        return list(self.lines)

    def done_count(self):
        return sum(1 for l in self.lines if " → " in l and not l.startswith("Starting:"))

    def shot(self, name):
        r = self.app.root
        r.lift()
        r.update()
        SHOTS.mkdir(parents=True, exist_ok=True)
        x, y = r.winfo_rootx(), r.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + r.winfo_width(), y + r.winfo_height()),
                       all_screens=True).save(SHOTS / f"{name}.png")


def copy_sample(name, as_name=None) -> Path:
    dest = WORK / (as_name or name)
    shutil.copytree(SAMPLES / name, dest)
    return dest


def audio_files(folder: Path):
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith("."))


def last(lines, prefix):
    return next((l for l in reversed(lines) if l.startswith(prefix)), "")


def ffmpeg_children():
    return [p for p in psutil.Process().children(recursive=True)
            if p.name().lower().startswith(("ffmpeg", "ffprobe"))]


# ── Cases ──────────────────────────────────────────────────────────────────
def case_ffmpeg(dialogs):
    print("missing FFmpeg")
    real = app_module.ffmpeg_available
    app_module.ffmpeg_available = lambda: False
    try:
        app = App()
        d = Driver(app)
        d.sleep(0.6)   # the warning comes 200 ms after the window opens
        calls = dialogs.take()
        check(any(k == "askyesno" and "FFMPEG" in t for k, t, _ in calls),
              "warning dialog offers the installer page")
        check(str(app.start_btn.cget("state")) == "disabled", "Start is disabled")
        check("FFmpeg not found" in app.summary_label.cget("text"), "the summary line says why")
        d.setup(SAMPLES / "tree", WORK / "no_ffmpeg_out")
        check(app.worker is None and app.report is None, "picking a folder doesn't start a check")
        check("FFmpeg not found" in app.summary_label.cget("text"), "the summary line still says why")
        app.start_btn.invoke()
        d.sleep(0.3)
        check(not (WORK / "no_ffmpeg_out").exists() and not dialogs.take(),
              "pressing the greyed Start does nothing")
        d.shot("no_ffmpeg")
        app.root.destroy()
    finally:
        app_module.ffmpeg_available = real


def case_empty(d, dialogs):
    print("zero audio files")
    cases = {"empty": [], "only_subfolders": ["inner/a.wav"], "not_audio": ["notes.txt", "song.mid"]}
    for name, files in cases.items():
        folder = WORK / name
        folder.mkdir(parents=True)
        for rel in files:
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            src = SAMPLES / "tree" / "top_a.wav"
            shutil.copy(src, folder / rel) if rel.endswith(".wav") else (folder / rel).write_text("x")
        d.setup(folder, folder / "unified")
        check(d.app.summary_label.cget("text") == "No audio files found in this folder",
              f"{name}: scan line says no audio files")
        d.lines.clear()
        d.app.start()
        d.wait_idle()
        calls = dialogs.take()
        check(len(calls) == 1 and calls[0][1] == "No audio files", f"{name}: one 'No audio files' message")
        if name == "only_subfolders":
            check("Include subfolders" in calls[0][2], f"{name}: suggests ticking Include subfolders")
        check(not (folder / "unified").exists(), f"{name}: no empty 'unified' folder left behind")
    d.setup(WORK / "only_subfolders", WORK / "only_subfolders" / "unified", subfolders=True)
    lines = d.run()
    check("1 succeeded, 0 failed" in last(lines, "1 succeeded"), "with subfolders ticked it processes the file")


def case_names(d, dialogs):
    print("unicode, spaces, commas in filenames")
    folder = copy_sample("names")
    d.setup(folder, folder / "unified", category="music", effect="saturn", silence="all", fmt="ogg")
    lines = d.run()
    n = len(list((SAMPLES / "names").iterdir()))
    check(f"{n} succeeded, 0 failed" in "\n".join(lines), f"all {n} processed (music + Saturn + silence + ogg)")
    outs = {p.name for p in (folder / "unified").iterdir()}
    expected = {f"{Path(x).stem}_music_saturn_x.ogg" for x in os.listdir(SAMPLES / "names")}
    check(outs == expected, "every output name is the original's plus the tags, nothing mangled")
    shown = d.app.log_text.get("1.0", "end")
    check("emoji 🎵 song" in shown and "日本語 テスト" in shown, "the log box shows emoji and CJK names")
    log_txt = (app_dir() / "log.txt").read_text(encoding="utf-8")
    check("Ünï cödé, ñ (copy)_music_saturn_x.ogg" in log_txt, "log.txt keeps them too")
    d.lines.clear()
    d.setup(folder, folder / "unified", effect="tape", silence="ends")
    lines = d.run()
    check(f"{n} succeeded, 0 failed" in "\n".join(lines), f"again in the original formats (sfx + tape + trim)")
    dialogs.take()


def case_nested(d, dialogs):
    print("output inside input, subfolders on")
    tree = copy_sample("tree")
    n = 6
    for label, out in (("To = From\\unified", tree / "unified"),
                       ("To inside a subfolder with audio", tree / "sub1" / "out"),
                       ("To = From", tree)):
        before = len(audio_files(tree))
        for attempt in (1, 2):
            d.lines.clear()
            d.setup(tree, out, subfolders=True)
            check_lines = list(d.lines)   # the folder check's own lines
            lines = d.run()
            check(f"{n} succeeded, 0 failed" in "\n".join(lines), f"{label}, run {attempt}: {n} processed")
        check(len(audio_files(tree)) == before + n, f"{label}: {n} new files after two runs, not more")
        if out != tree:
            check(not any(p.is_relative_to(out / out.relative_to(tree)) for p in audio_files(out)),
                  f"{label}: no output of an output")
            check(any("is inside the From folder" in l for l in lines), f"{label}: the log says it's skipped")
        else:
            check(any(l.startswith(f"Skipped {n} earlier results") for l in check_lines),
                  f"{label}: run 2 skips the {n} results beside their originals")
        if out != tree:   # or the next variant would rightly take these for new audio
            to_trash(out)
    dialogs.take()


def case_readonly(d, dialogs):
    print("read-only output")
    tree = copy_sample("tree", "tree_ro")
    locked = WORK / "locked_out"
    locked.mkdir()
    user = os.environ["USERNAME"]
    subprocess.run(["icacls", str(locked), "/deny", f"{user}:(OI)(CI)(W,AD,WD)"],
                   check=True, capture_output=True)
    try:
        for label, out in (("folder without write permission", locked),
                           ("new folder inside it", locked / "new")):
            d.setup(tree, out)
            t0 = time.time()
            d.run()
            calls = dialogs.take()
            check(time.time() - t0 < 3 and len(calls) == 1 and calls[0][0] == "showerror",
                  f"{label}: error message right away ({time.time() - t0:.1f} s)")
            check("Windows doesn't allow saving files there" in calls[0][2] if calls else False,
                  f"{label}: says why in plain words")
    finally:
        subprocess.run(["icacls", str(locked), "/remove:d", user], capture_output=True)

    out = WORK / "tree_ro_out"
    d.setup(tree, out)
    d.run()
    target = out / "top_a_sfx.wav"
    os.chmod(target, stat.S_IREAD)
    try:
        lines = d.run()
        check(any("top_a_sfx.wav is already in the To folder and is read-only" in l for l in lines),
              "a read-only earlier output: clear FAILED line")
        check(any("1 succeeded, 1 failed" in l for l in lines), "the other file still processed")
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
    dialogs.take()


def case_vanish(d, dialogs):
    print("From folder gone mid-run")
    for variant in ("folder moved", "files moved"):
        folder = copy_sample("small", "vanish_" + variant.split()[0])
        out = WORK / f"{folder.name}_out" if variant == "folder moved" else folder / "unified"
        d.setup(folder, out, effect="tape")
        d.lines.clear()
        d.app.start()
        d.until(lambda: d.done_count() >= 5, 120, "5 files done")
        if variant == "folder moved":
            # Windows refuses to move a folder while FFmpeg has a file in it open, so this
            # lands between two FFmpeg calls, like a user's retry would
            def try_move():
                try:
                    to_trash(folder)
                    d.on_tick = None
                except OSError:
                    pass
            d.on_tick = try_move
        else:
            for f in sorted(folder.glob("take_*")):
                try:
                    to_trash(f)
                except OSError:   # the one FFmpeg has open
                    pass
        d.wait_idle()
        d.on_tick = None
        failed = sum(1 for l in d.lines if "FAILED" in l)
        calls = dialogs.take()
        check(not folder.exists() if variant == "folder moved" else True, f"{variant}: the move happened")
        check(len(calls) == 1 and calls[0][1] == "The batch stopped", f"{variant}: one 'batch stopped' message")
        print(f"        {calls[0][2].splitlines()[0] if calls else '-'}")
        check(failed <= 1, f"{variant}: at most the file in flight fails ({failed}), not the rest one by one")
        check("stopped before the end" in d.app.current_label.cget("text"), f"{variant}: status line says it stopped")


def case_stop(d, dialogs):
    print("Stop mid-batch, then Start again")
    folder = copy_sample("small", "stop")
    temps_before = set(Path(tempfile.gettempdir()).glob("afu_*"))
    d.setup(folder, folder / "unified", effect="saturn", silence="all")
    d.lines.clear()
    d.app.start()
    d.until(lambda: d.done_count() >= 10, 120, "10 files done")
    t0 = time.time()
    d.app.stop()
    d.wait_idle(30, "the stop")
    took = time.time() - t0 - 0.4   # wait_idle's own settling time
    done = d.done_count()
    outs = audio_files(folder / "unified")
    check(took < 2, f"stopped in {took:.2f} s")
    check(len(outs) == done, f"{done} done, {len(outs)} files: no half-written file")
    check(not ffmpeg_children(), "no FFmpeg left running")
    label = d.app.current_label.cget("text")
    check("stopped" in label.lower() and str(d.app.start_btn.cget("state")) == "normal",
          f"status line '{label}', Start is back")
    lines = d.run()
    check(any("40 succeeded, 0 failed" in l for l in lines), "Start again: all 40 processed")
    check(len(audio_files(folder / "unified")) == 40, "40 outputs, the first run's overwritten, not doubled")
    check(set(Path(tempfile.gettempdir()).glob("afu_*")) == temps_before, "no temp folder left behind")
    dialogs.take()


def case_big(d, dialogs):
    print("very large batch (600 files, 6 subfolders)")
    big = SAMPLES / "big"
    out = WORK / "big_out"
    proc = psutil.Process()
    # Stop during the check, then Start: it has to check again before processing
    d.setup(big, out, subfolders=True, category="voice", effect="ps1", silence="all", wait=False)
    d.sleep(2)
    d.app.stop()
    d.wait_idle(30, "the stopped check")
    check(d.app.current_label.cget("text").startswith("Check stopped"), "Stop during the folder check")

    d.update_times.clear()
    mem = []
    last_sample = [0.0]

    def sample():
        if time.time() - last_sample[0] > 0.5:
            last_sample[0] = time.time()
            mi = proc.memory_info()
            mem.append((mi.rss, mi.private))
    d.on_tick = sample
    t0 = time.time()
    lines = d.run(timeout=3600)
    total = time.time() - t0
    d.on_tick = None
    d.shot("big_batch_done")
    times = sorted(d.update_times)
    p99 = times[int(len(times) * 0.99)]
    worst = times[-1]
    log_lines = int(d.app.log_text.index("end-1c").split(".")[0])
    check(any("600 succeeded, 0 failed" in l for l in lines), "600 processed")
    check(len(audio_files(out)) == 600, "600 outputs in the mirrored subfolders")
    check(worst < 0.25, f"window never froze: longest event handling {worst * 1000:.0f} ms, 99% under {p99 * 1000:.0f} ms")
    rss = [m[0] for m in mem]
    check(max(rss) - rss[0] < 100e6, f"memory flat: {rss[0] / 1e6:.0f} → {max(rss) / 1e6:.0f} MB peak")
    report = (f"600 files, voice + PS1 + remove silence, subfolders on\n"
              f"time: {total:.0f} s ({total / 600:.2f} s per file, check included)\n"
              f"longest event handling: {worst * 1000:.0f} ms, 99th percentile {p99 * 1000:.0f} ms\n"
              f"window process memory: start {rss[0] / 1e6:.0f} MB, peak {max(rss) / 1e6:.0f} MB, "
              f"end {rss[-1] / 1e6:.0f} MB; private peak {max(m[1] for m in mem) / 1e6:.0f} MB\n"
              f"log box lines: {log_lines}\n")
    (SHOTS / "big_batch.txt").write_text(report, encoding="utf-8")
    print("        " + report.replace("\n", "\n        "))
    dialogs.take()


CASES = ["ffmpeg", "empty", "names", "nested", "readonly", "vanish", "stop", "big"]


def main():
    chosen = sys.argv[1:] or CASES
    if not SAMPLES.exists():
        sys.exit("Run test/make_session6_samples.py first")
    if WORK.exists() and chosen != ["ffmpeg"]:
        to_trash(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    cfg = app_dir() / "config.json"
    backup = cfg.read_bytes() if cfg.exists() else None
    dialogs = Dialogs()
    try:
        if chosen == ["ffmpeg"]:
            case_ffmpeg(dialogs)
        elif "ffmpeg" in chosen:   # its own process: a second ttk.Window in one process is asking for trouble
            if subprocess.run([sys.executable, __file__, "ffmpeg"]).returncode:
                failures.append("missing FFmpeg (see above)")
        rest = [c for c in chosen if c != "ffmpeg"]
        if rest:
            app = App()
            d = Driver(app)
            d.wait_idle()
            for name in rest:
                globals()[f"case_{name}"](d, dialogs)
            app.root.destroy()
    finally:
        if backup is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_bytes(backup)
    print(f"\n{len(failures)} failed" + "".join(f"\n  {f}" for f in failures) if failures else "\nall checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
