"""Drive the real window into a few states and screenshot each into shots/promo_raw/.

    python test/promo_shots.py
    python test/promo_images.py      (then: builds promo/ from these)

Builds test/promo_samples/Game Sounds/ (gitignored) from the Session 5/6 samples under
game-sound names, so the window shows a believable folder. config.json is restored afterwards.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from PIL import ImageGrab  # noqa: E402

from gui.app import App  # noqa: E402
from gui.sections import SILENCE_MODES  # noqa: E402
from utils.paths import app_dir  # noqa: E402

FOLDER = ROOT / "test" / "promo_samples" / "Game Sounds"
OUT = ROOT / "shots" / "promo_raw"
NAMES = [
    "door_creak", "explosion_big", "footstep_grass_1", "footstep_grass_2", "laser_shot",
    "menu_click", "menu_back", "coin_pickup", "jump", "land_heavy", "sword_swing", "sword_hit",
    "shield_block", "potion_drink", "chest_open", "fireball_cast", "ice_shatter", "arrow_whoosh",
    "boss_roar", "level_up",
]


def build_folder():
    if FOLDER.exists():
        return
    FOLDER.mkdir(parents=True)
    small = sorted((ROOT / "test" / "session6_samples" / "small").iterdir())
    for name, src in zip(NAMES, small):
        shutil.copy(src, FOLDER / f"{name}{src.suffix}")
    s5 = ROOT / "test" / "session5_samples"
    for src, name in [("gen_quiet_rifleshot.wav", "rifle_shot_distant.wav"),
                      ("heavybeamrifleshot.wav", "beam_rifle.wav"),
                      ("finnish morko (1).mp3", "monster_growl.mp3")]:
        shutil.copy(s5 / src, FOLDER / name)


def main():
    build_folder()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in FOLDER.glob("unified"):
        shutil.rmtree(old)
    cfg = app_dir() / "config.json"
    backup = cfg.read_bytes() if cfg.exists() else None
    app = App()
    r = app.root

    def grab(name):
        r.attributes("-topmost", True)   # a batch's end can leave it behind other windows
        r.lift()
        r.update()
        x, y = r.winfo_rootx(), r.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + r.winfo_width(), y + r.winfo_height()),
                       all_screens=True).save(OUT / f"{name}.png")
        print(name, flush=True)

    def setup(cat, effect, silence, quiet=False):
        v = app.vars
        v["input_dir"].set(str(FOLDER))
        v["output_dir"].set(str(FOLDER / "unified"))
        v["include_subfolders"].set(False)
        v["category"].set(cat)
        v["silence"].set(silence)
        app.silence_box.current(list(SILENCE_MODES).index(silence))
        v["output_format"].set("same")
        v["quiet_only"].set(quiet)
        app.effect_box.current([t for _, t in app.effect_rows].index(effect))
        app._on_effect_selected()
        app.on_scan_settings_changed()

    # Steps run one after another; each returns True when it's done waiting
    state = {"mid": False}
    original_progress = app._on_progress

    def on_progress(verb, done, total, name):
        original_progress(verb, done, total, name)
        if app.running_batch and done == 9 and not state["mid"]:
            state["mid"] = True
            r.after(50, lambda: grab("2_tape_mid"))
    app._on_progress = on_progress

    def idle():
        return app.worker is None and not app.running_batch

    steps = [
        lambda: setup("sfx", "saturn", "keep"),
        lambda: idle() and app.report is not None and grab("3_scanned") is None,
        lambda: setup("voice", "tape", "ends") or app.start(),
        lambda: state["mid"] and idle(),
        lambda: setup("sfx", "ps1", "keep") or app.start(),
        lambda: app.running_batch,
        lambda: idle() and grab("1_ps1_done") is None,
    ]

    def run(i=0):
        if i == len(steps):
            r.destroy()
            return
        done = steps[i]()
        # setup steps return None (done at once); wait steps return True when ready
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
