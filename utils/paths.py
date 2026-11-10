"""Where things live: next to the exe (writable) vs bundled inside it (read-only)."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """Folder the user sees: next to the exe, or the project root when running as a script.
    Writable files live here (config.json)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return _PROJECT_ROOT


def resource_path(relative: str) -> Path:
    """Read-only files bundled into the exe with --add-data (the icon).
    In a built exe they sit in _internal\\ (sys._MEIPASS). Never write here."""
    base = Path(getattr(sys, "_MEIPASS", _PROJECT_ROOT))
    return base / relative
