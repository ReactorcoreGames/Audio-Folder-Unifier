"""Screenshot the real window for the trailer's "Press Start" shot into trailer/work/window/.

    python trailer/window_shots.py

Uses test/promo_shots.py's Game Sounds folder. config.json is restored afterwards.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
sys.stdout.reconfigure(encoding="utf-8")

import ctypes  # noqa: E402

from PIL import ImageGrab  # noqa: E402

from gui.app import App  # noqa: E402
from gui.sections import SILENCE_MODES  # noqa: E402
from promo_shots import FOLDER, build_folder  # noqa: E402
from utils.paths import app_dir  # noqa: E402

OUT = ROOT / "trailer" / "work" / "window"


def main():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    build_folder()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in FOLDER.glob("unified"):
        shutil.rmtree(old)
    cfg = app_dir() / "config.json"
    backup = cfg.read_bytes() if cfg.exists() else None
    app = App()
    r = app.root

    def grab(name):
        r.attributes("-topmost", True)
        r.lift()
        r.update()
        x, y = r.winfo_rootx(), r.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + r.winfo_width(), y + r.winfo_height()),
                       all_screens=True).save(OUT / f"{name}.png")
        print(name, flush=True)

    def setup():
        v = app.vars
        v["input_dir"].set(str(FOLDER))
        v["output_dir"].set(str(FOLDER / "unified"))
        v["include_subfolders"].set(False)
        v["category"].set("sfx")
        v["silence"].set("keep")
        app.silence_box.current(list(SILENCE_MODES).index("keep"))
        v["output_format"].set("same")
        v["quiet_only"].set(False)
        app.effect_box.current([t for _, t in app.effect_rows].index("none"))
        app._on_effect_selected()
        app.on_scan_settings_changed()

    state = {"mid": False}
    original_progress = app._on_progress

    def on_progress(verb, done, total, name):
        original_progress(verb, done, total, name)
        if app.running_batch and done == 12 and not state["mid"]:
            state["mid"] = True
            r.after(50, lambda: grab("2_mid"))
    app._on_progress = on_progress

    def idle():
        return app.worker is None and not app.running_batch

    steps = [
        setup,
        lambda: idle() and app.report is not None and grab("1_ready") is None,
        app.start,
        lambda: app.running_batch,
        lambda: idle() and grab("3_done") is None,
    ]

    def run(i=0):
        if i == len(steps):
            r.destroy()
            return
        done = steps[i]()
        r.after(300, lambda: run(i + 1) if done is None or done else run(i))

    r.after(1500, run)
    try:
        app.run()
    finally:
        if backup is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_bytes(backup)


if __name__ == "__main__":
    main()
