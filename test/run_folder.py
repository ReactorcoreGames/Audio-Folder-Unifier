"""Run the full pipeline on a folder from the command line, without the GUI.

    python test/run_folder.py <input> [--out DIR] [--category sfx|voice|music|ambient]
        [--effect TAG] [--silence keep|ends|all] [--quiet-only] [--subfolders] [--format same|wav|mp3|ogg]

Output defaults to <input>\\unified, like the GUI. Ctrl+C stops the batch the way Stop does.
"""

import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")   # log lines contain "→"; the Windows console is cp1252

from core.effects import BY_TAG, NO_EFFECT
from core.formats import OUTPUT_FORMATS
from core.normalize import LOUDNORM_TARGETS
from core.pipeline import Settings, check_output_dir, run_batch, scan
from utils.ffmpeg import Cancelled, FFmpegRunner, ffmpeg_available


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--category", default="sfx", choices=list(LOUDNORM_TARGETS))
    ap.add_argument("--effect", default=NO_EFFECT, choices=[NO_EFFECT, *BY_TAG])
    ap.add_argument("--silence", default="keep", choices=["keep", "ends", "all"])
    ap.add_argument("--quiet-only", action="store_true")
    ap.add_argument("--subfolders", action="store_true")
    ap.add_argument("--format", default="same", choices=list(OUTPUT_FORMATS))
    a = ap.parse_args()

    if not ffmpeg_available():
        sys.exit("ffmpeg / ffprobe not found on PATH")
    settings = Settings(a.input.resolve(), (a.out or a.input / "unified").resolve(), a.subfolders,
                        a.category, a.effect, a.silence, a.quiet_only, a.format)
    problem = check_output_dir(settings.output_dir)
    if problem:
        sys.exit(problem)

    runner = FFmpegRunner()
    # Work in a thread so Ctrl+C reaches the main thread and can cancel, like the Stop button
    def work():
        try:
            report = scan(settings, runner)
        except Cancelled:
            print("stopped during the scan")
            return
        print(report.summary())
        for path in report.skipped_own:
            print(f"  skipped (earlier output): {path.name}")
        if report.files:
            run_batch(settings, report, runner, print)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    try:
        while t.is_alive():
            t.join(0.2)
    except KeyboardInterrupt:
        print("stopping...")
        runner.cancel()
        t.join()
    print(f"output: {settings.output_dir}")


if __name__ == "__main__":
    main()
