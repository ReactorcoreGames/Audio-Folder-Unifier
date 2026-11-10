"""Build the trailer's demo audio with the real pipeline (see trailer.md).

    python trailer/make_audio.py

trailer/work/before/  the five sound effects, trimmed, levels untouched
trailer/work/after/   the same through Sound effects + No change
trailer/work/voice/   the TTS line; work/ladder_<tag>/ it through each shown rung
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "test" / "testfiles" / "sound effects"
WORK = ROOT / "trailer" / "work"

# (output name, source, start s, length s), in play order: loud and quiet alternate
SOUNDS = [
    ("1_explosion", "hits/explosion-2.ogg", 0, 1.31),
    ("2_raven", "monsters/raven-2.ogg", 0.25, 1.4),
    ("3_glass", "hits/glass-breaking-2.ogg", 0, 0.84),
    ("4_coin", "monsters/gold-1.ogg", 0, 0.8),
    ("5_dinosaur", "monsters/dinosaur-1.wav", 0, 1.31),
]
VOICE_LINE = "Unify your audio."
RUNGS = ["nes", "ps1", "saturn", "ps2"]


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def unify(src, out, category, effect="none"):
    if out.exists():
        shutil.rmtree(out)
    subprocess.run([sys.executable, str(ROOT / "test" / "run_folder.py"), str(src), "--out", str(out),
                    "--category", category, "--effect", effect], check=True)


def tts(text, out):
    """Same Windows voice as test/make_session5_samples.py."""
    tmp = out.with_suffix(".tmp.wav")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.SelectVoice('Microsoft David Desktop');$s.Rate=-1;"
          f"$s.SetOutputToWaveFile('{tmp}');$s.Speak([Console]::In.ReadToEnd());$s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)
    # Trim the synthesizer's leading and trailing silence
    ffmpeg("-i", str(tmp), "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-50dB,areverse",
           "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(out))
    tmp.unlink()


def main():
    before = WORK / "before"
    if before.exists():
        shutil.rmtree(before)
    before.mkdir(parents=True)
    for name, src, start, length in SOUNDS:
        ffmpeg("-ss", str(start), "-t", str(length), "-i", str(SFX / src),
               "-af", f"afade=t=out:st={length - 0.08:.2f}:d=0.08", "-ar", "44100", "-ac", "2",
               "-c:a", "pcm_s16le", str(before / f"{name}.wav"))
    unify(before, WORK / "after", "sfx")

    voice = WORK / "voice"
    if voice.exists():
        shutil.rmtree(voice)
    voice.mkdir()
    tts(VOICE_LINE, voice / "line.wav")
    for tag in RUNGS:
        unify(voice, WORK / f"ladder_{tag}", "voice", tag)


if __name__ == "__main__":
    main()
