"""config.json next to the exe. Missing, malformed or partial files fall back to defaults."""

import json

from utils.paths import app_dir

DEFAULT_CONFIG = {
    "input_dir": "",
    "output_dir": "",
    "include_subfolders": False,
    "category": "sfx",          # sfx / voice / music / ambient
    "effect": "none",           # effect tag from docs/presets.md, or "none"
    "silence": "keep",          # keep / ends / all
    "quiet_only": False,
    "output_format": "same",    # same / wav / mp3 / ogg
}


def _config_path():
    return app_dir() / "config.json"


def load_config() -> dict:
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_CONFIG)
        if data.get("remove_silence") is True and "silence" not in data:
            data["silence"] = "all"   # the Session 4 checkbox
        return {**DEFAULT_CONFIG, **{k: v for k, v in data.items() if k in DEFAULT_CONFIG}}
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(data: dict) -> None:
    """Saved on every change. A read-only program folder must not crash the window, so
    write errors are swallowed: the settings just won't be remembered."""
    try:
        _config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass
