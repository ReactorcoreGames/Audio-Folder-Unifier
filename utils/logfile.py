"""log.txt next to the exe: everything the log box shows, kept across sessions."""

from datetime import datetime

from utils.paths import app_dir

FIRST_LINE = ("log.txt is where anything that happens in the program is printed. If this file "
              "grows too big, you can safely delete it - the program will make a fresh, empty one.")


class LogFile:
    def __init__(self):
        self.started = False   # this session's header written yet

    def write(self, text: str) -> None:
        """Append one line. Write errors are swallowed like config.json's: a read-only
        program folder must not crash the window, the lines just aren't kept."""
        try:
            with (app_dir() / "log.txt").open("a", encoding="utf-8") as f:
                if f.tell() == 0:
                    f.write(FIRST_LINE + "\n")
                if not self.started:
                    f.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M} ===\n")
                    self.started = True
                f.write(text + "\n")
        except OSError:
            pass
