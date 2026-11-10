"""Build the Session 5 listening-test folders next to test/testfiles (both gitignored).

    python test/make_session5_samples.py

test/session5_samples/   the author's files + generated long speech, ambient, blip,
                         silent, corrupt, already-loud and very quiet files
test/session5_audition/  short excerpts for auditioning the effect presets
"""

import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "testfiles"
SAMPLES = ROOT / "session5_samples"
AUDITION = ROOT / "session5_audition"

SPEECH = (
    "Welcome back. Today we are going to talk about how a folder of sounds can feel like it "
    "belongs together, even when every file came from somewhere different. "
    "Imagine you downloaded a door creak from one website, a footstep from another, and a "
    "voice line you recorded yourself on a cheap microphone. "
    "Each one sits at its own volume. Some are crisp and bright, others are dull and hissy. "
    "When you play them one after another, the difference jumps out straight away. "
    "The first step is simple: make them all equally loud. "
    "But loudness is only half of the story. The texture matters too. "
    "A recording made at a low sample rate sounds muffled next to a clean studio take, no "
    "matter how carefully the levels are matched. "
    "So the second step is to push every file through the same filter, so that they share "
    "one character. "
    "That is the whole idea. Thanks for listening, and see you next time."
)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def tts(text, out):
    """Windows' built-in speech synthesizer, so no external service is needed."""
    tmp = out.with_suffix(".tmp.wav")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.SelectVoice('Microsoft David Desktop');$s.Rate=-1;"
          f"$s.SetOutputToWaveFile('{tmp}');$s.Speak([Console]::In.ReadToEnd());$s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)
    ffmpeg("-i", str(tmp), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(out))
    tmp.unlink()


def build_samples():
    SAMPLES.mkdir(exist_ok=True)
    for f in SRC.iterdir():
        if f.is_file():
            shutil.copy2(f, SAMPLES / f.name)

    tts(SPEECH, SAMPLES / "gen_speech_long.wav")
    # Rain-ish bed: brown noise for body, high-passed pink noise for the hiss, slow swell
    ffmpeg("-f", "lavfi", "-i", "anoisesrc=d=30:c=brown:a=0.5:r=44100:seed=1",
           "-f", "lavfi", "-i", "anoisesrc=d=30:c=pink:a=0.25:r=44100:seed=2",
           "-filter_complex", "[1]highpass=f=2500[h];[0][h]amix=inputs=2:normalize=0,"
           "tremolo=f=0.15:d=0.4,pan=stereo|c0=c0|c1=c0,volume=-12dB",
           "-c:a", "pcm_s16le", str(SAMPLES / "gen_ambient_rain.wav"))
    # A 200 ms UI blip: the case loudnorm gets wrong
    ffmpeg("-f", "lavfi", "-i", "sine=f=880:d=0.2:r=44100",
           "-af", "afade=t=out:st=0.12:d=0.08,volume=-6dB",
           "-c:a", "pcm_s16le", str(SAMPLES / "gen_sfx_blip.wav"))
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5",
           "-c:a", "pcm_s16le", str(SAMPLES / "gen_silent.wav"))
    random.seed(5)
    (SAMPLES / "gen_corrupt.mp3").write_bytes(bytes(random.getrandbits(8) for _ in range(65536)))
    # Already loud: a music excerpt pushed 12 dB into 16-bit clipping, loudness-war style
    ffmpeg("-ss", "60", "-t", "20", "-i", str(SRC / "MusMadness - Waterfall.mp3"),
           "-af", "volume=12dB", "-c:a", "pcm_s16le", str(SAMPLES / "gen_loud_music.wav"))
    ffmpeg("-i", str(SRC / "heavybeamrifleshot.wav"), "-af", "volume=-28dB",
           "-c:a", "pcm_s16le", str(SAMPLES / "gen_quiet_rifleshot.wav"))


def build_audition():
    AUDITION.mkdir(exist_ok=True)
    cut = lambda src, out, start, dur: ffmpeg(
        "-ss", str(start), "-t", str(dur), "-i", str(src), "-map", "0:a:0", "-c:a", "pcm_s16le", str(out))
    cut(SAMPLES / "gen_speech_long.wav", AUDITION / "speech.wav", 0, 14)
    cut(SRC / "MusMadness - Waterfall.mp3", AUDITION / "music.wav", 60, 15)
    cut(SAMPLES / "gen_ambient_rain.wav", AUDITION / "ambient.wav", 0, 10)
    for name in ("heavybeamrifleshot.wav", "finnish morko (1).mp3",
                 "Transform your audio into hellish masterpieces.mp3"):
        shutil.copy2(SRC / name, AUDITION / name)


if __name__ == "__main__":
    if not SRC.is_dir():
        sys.exit(f"Missing {SRC}")
    build_samples()
    build_audition()
    for d in (SAMPLES, AUDITION):
        print(d, sorted(p.name for p in d.iterdir()))
