"""Output filenames: <basename>_<category>[_<effect>][_t|_x].<ext> (docs/processing_spec.md).

Same settings → same name, so a re-run overwrites its own output; any changed setting
writes alongside instead.
"""

import re
from pathlib import Path

from core.formats import output_ext

CATEGORY_TAGS = ("sfx", "voice", "music", "ambient")
# Must match the effect registry in core/effects.py (docs/presets.md)
EFFECT_TAGS = (
    "nes", "snes", "ps1", "n64", "saturn", "ps2",
    "radio", "phone", "megaphone", "underwater", "tape", "vinyl", "distant", "gritty", "brutal",
    "podcast", "punchy", "warm", "bright",
)
# Silence mode → tag: "ends" trims the start and end, "all" also cuts long pauses inside
SILENCE_TAGS = {"ends": "t", "all": "x"}

_OWN_SUFFIX = re.compile(
    rf"^(?P<base>.+)_(?:{'|'.join(CATEGORY_TAGS)})(?:_(?:{'|'.join(EFFECT_TAGS)}))?(?:_(?:{'|'.join(SILENCE_TAGS.values())}))?$",
    re.IGNORECASE,
)


def output_name(source: Path, category: str, effect: str | None, silence: str,
                output_format: str = "same") -> str:
    parts = [source.stem, category]
    if effect and effect != "none":
        parts.append(effect)
    if silence in SILENCE_TAGS:
        parts.append(SILENCE_TAGS[silence])
    return "_".join(parts) + output_ext(source.suffix, output_format)


def own_output_base(path: Path) -> str | None:
    """The original basename if this filename carries our suffix, else None.
    explosion_sfx_ps1_x.wav → "explosion"."""
    m = _OWN_SUFFIX.match(path.stem)
    return m.group("base") if m else None
