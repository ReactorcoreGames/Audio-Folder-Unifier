"""Which files count as audio, and how each output format gets encoded."""

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".opus", ".flac", ".m4a", ".aac", ".aiff", ".aif", ".wma"}

# Config value of the "Output format" choice → forced extension ("same" keeps the original)
OUTPUT_FORMATS = {"same": None, "wav": ".wav", "mp3": ".mp3", "ogg": ".ogg"}


def output_ext(source_ext: str, output_format: str) -> str:
    return OUTPUT_FORMATS.get(output_format) or source_ext.lower()


def encode_args(ext: str) -> list[str]:
    """Encoder settings inherited from audio_unifier.py. wav/flac/etc use lossless defaults."""
    ext = ext.lower()
    if ext == ".ogg":
        return ["-q:a", "7"]
    if ext == ".mp3":
        return ["-q:a", "2"]
    if ext in (".aac", ".m4a"):
        return ["-b:a", "192k"]
    return []
