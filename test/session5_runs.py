"""Drive the real window through the Session 5 runs; outputs go to shots/session5/.

    python test/make_session5_samples.py     (first)
    python test/session5_runs.py [folder name in shots/, default session5]

Each run sets the controls, presses Start and waits for the batch, the same path a user
takes. The window's log is saved as _log.txt in each output folder. config.json is
restored afterwards. Runs whose output folder already exists are skipped.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from core.effects import NO_EFFECT, dropdown_rows  # noqa: E402
from gui.app import App  # noqa: E402
from utils.paths import app_dir  # noqa: E402

SAMPLES = ROOT / "test" / "session5_samples"
AUDITION = ROOT / "test" / "session5_audition"
OUT = ROOT / "shots" / (sys.argv[1] if len(sys.argv) > 1 else "session5")


def plan():
    runs = [(SAMPLES, OUT / f"1_category_{c}", c, NO_EFFECT, "keep")
            for c in ("sfx", "voice", "music", "ambient")]
    runs.append((SAMPLES, OUT / "2_silence_music", "music", NO_EFFECT, "all"))
    runs.append((SAMPLES, OUT / "2_silence_ends_music", "music", NO_EFFECT, "ends"))
    # Effects in dropdown order, all on the sound-effect method so every file lands on the
    # same -13 dBFS RMS peak and only the effect differs between folders
    tags = [tag for _, tag in dropdown_rows() if tag is not None]
    runs += [(AUDITION, OUT / "3_effects" / f"{i:02d}_{tag}", "sfx", tag, "keep")
             for i, tag in enumerate(tags)]
    return runs


def main():
    cfg = app_dir() / "config.json"
    backup = cfg.read_bytes() if cfg.exists() else None
    # A run whose folder exists is done; move a folder away to redo that run
    runs = [r for r in plan() if not r[1].exists()]
    if not runs:
        sys.exit(f"Every run already has its folder in {OUT}")
    app = App()
    lines = []
    window_log = app.log
    app.log = lambda text: (lines.append(text), window_log(text))
    state = {"i": -1, "saw_batch": False, "t0": 0.0}

    def begin(i):
        src, out, cat, effect, silence = runs[i]
        state.update(i=i, saw_batch=False, t0=time.time())
        lines.clear()
        out.mkdir(parents=True)
        v = app.vars
        v["input_dir"].set(str(src))
        v["output_dir"].set(str(out))
        v["include_subfolders"].set(False)
        v["category"].set(cat)
        v["silence"].set(silence)
        v["quiet_only"].set(False)
        v["output_format"].set("same")
        app.effect_box.current([t for _, t in app.effect_rows].index(effect))
        app._on_effect_selected()
        app.on_scan_settings_changed()
        app.start()

    def poll():
        if app.running_batch:
            state["saw_batch"] = True
        elif state["saw_batch"] and app.worker is None:
            out = runs[state["i"]][1]
            (out / "_log.txt").write_text("\n".join(lines), encoding="utf-8")
            done = next((l for l in reversed(lines) if "succeeded" in l), "?")
            print(f"[{state['i'] + 1}/{len(runs)}] {out.relative_to(OUT)}: {done} "
                  f"({time.time() - state['t0']:.0f} s)", flush=True)
            if state["i"] + 1 == len(runs):
                app.root.destroy()
                return
            begin(state["i"] + 1)
        app.root.after(300, poll)

    app.root.after(1000, lambda: (begin(0), poll()))
    try:
        app.run()
    finally:
        if backup is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_bytes(backup)


if __name__ == "__main__":
    main()
