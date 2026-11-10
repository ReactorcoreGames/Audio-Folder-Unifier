"""Find the audio files to process."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from core.formats import AUDIO_EXTS
from core.naming import own_output_base


@dataclass
class ScanResult:
    files: list[Path] = field(default_factory=list)
    skipped_own: list[Path] = field(default_factory=list)   # earlier output found in the input


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def scan_folder(input_dir: Path, output_dir: Path | None, recursive: bool) -> ScanResult:
    """Audio files in input_dir (and its subfolders if recursive), sorted.

    The output folder is never entered, even when it sits inside the input, so a re-run
    doesn't pick up its own previous output. As a second guard, a file carrying our output
    suffix is skipped when its original sits beside it (door_sfx.wav next to door.wav):
    that's what a run with output = input leaves behind. Without an original next to it,
    door_sfx.wav is more likely a library's own naming and gets processed.
    """
    input_dir = Path(input_dir)
    result = ScanResult()
    for root, dirs, names in os.walk(input_dir):
        root = Path(root)
        if output_dir is not None:
            dirs[:] = [d for d in dirs if not _same_dir(root / d, output_dir)]
        dirs.sort(key=str.lower)
        audio = sorted((n for n in names if Path(n).suffix.lower() in AUDIO_EXTS), key=str.lower)
        stems = {Path(n).stem.lower() for n in audio}
        for name in audio:
            path = root / name
            base = own_output_base(path)
            if base is not None and base.lower() in stems:
                result.skipped_own.append(path)
            else:
                result.files.append(path)
        if not recursive:
            break
    return result
