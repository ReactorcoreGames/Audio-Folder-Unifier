"""Open the window, screenshot it into shots/, close it.

    python test/shot_window.py [name] [WxH]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402

from gui.app import App  # noqa: E402


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "window"
    app = App()
    if len(sys.argv) > 2:
        app.root.geometry(sys.argv[2])
    out = ROOT / "shots" / f"{name}.png"
    out.parent.mkdir(exist_ok=True)

    def grab():
        r = app.root
        r.lift()
        r.update()
        x, y = r.winfo_rootx(), r.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + r.winfo_width(), y + r.winfo_height()),
                       all_screens=True).save(out)
        print(out)
        r.destroy()

    app.root.after(1500, grab)
    app.run()


if __name__ == "__main__":
    main()
