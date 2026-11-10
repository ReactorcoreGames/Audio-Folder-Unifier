"""Step 2: the "Change the sound?" presets (docs/presets.md): registry, filter chains,
dropdown labels and the descriptions shown under the dropdown.

Effects run before measurement, so the level matching afterwards undoes any loudness change
an effect makes. That ordering lives in core/pipeline.py.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from core.measure import run_checked
from core.naming import EFFECT_TAGS
from utils.ffmpeg import FFmpegRunner

NO_EFFECT = "none"
NO_EFFECT_LABEL = "No change — just fix the loudness"
NO_EFFECT_DESCRIPTION = (
    "Leaves the sound itself alone. Every file is only brought to the same loudness as the "
    "others, nothing else changes. The safe choice when your sounds already go well together."
)

# Group key → title of its separator row in the dropdown, in dropdown order
GROUPS = {
    "A": "Match Everything to One Quality Level",
    "B": "Sounds Like It's Coming From",
    "C": "Polish & Finish",
}

# Group A chains work at this rate, so `samples=N` (hold every Nth sample, the retro aliasing)
# means the same thing for every file. The chain returns to the file's own rate afterwards.
LADDER_RATE = 44100
# acrusher's aa (anti-aliasing) must stay above 0: at exactly 0 some signals come out as NaN,
# depending on the level (Session 5). 0.01 still sounds like hard sample-and-hold.
MIN_CRUSHER_AA = 0.01


@dataclass(frozen=True)
class Effect:
    tag: str            # filename tag and config value
    group: str          # key into GROUPS
    label: str          # dropdown text
    chain: str          # FFmpeg -af chain, run on the file already brought to the target level
    description: str    # ≤300 chars, plain language, what it sounds like first


# Strengths aim at the "medium" settings of the author's Script-To-Voice-Generator-KokoroTTS
# (config.py → AUDIO_EFFECTS) and the "subtle" ones of Audio-Satanifier-666 (Session 5).
EFFECTS = (
    # Group A: a severity ladder, strongest first, each rung with its console's signature.
    # Never reorder by console release date.
    Effect("nes", "A", "NES",
           "highpass=f=440:p=1,acrusher=bits=5:mode=lin:samples=10:aa=0.01:mix=1",
           "The harshest setting, top of the quality ladder. Thin, buzzy and crunchy like an 8-bit "
           "console: the bass is stripped away and everything is rebuilt from a handful of coarse "
           "steps. Strong enough to make even badly mismatched sounds feel like one set."),
    Effect("snes", "A", "SNES",
           "acrusher=bits=6:mode=lin:samples=5:aa=0.01:mix=1,lowpass=f=4000,lowpass=f=4000,"
           "aecho=0.8:0.4:110:0.15",
           "Strong and soft-edged, second on the quality ladder. Muffled and crunchy like 16-bit "
           "era game audio, with a faint trace of that console's trademark echo."),
    Effect("ps1", "A", "PlayStation 1",
           "acrusher=bits=9:mode=lin:samples=2:aa=0.01:mix=1,lowpass=f=9000,"
           "aecho=0.8:0.7:40|75|115|160:0.35|0.28|0.2|0.12",
           "Clearly lo-fi, the middle of the quality ladder. Grainy and slightly metallic, with the "
           "roomy reverb of early 3D games. A good middle setting when your sounds come from very "
           "different sources."),
    Effect("n64", "A", "Nintendo 64",
           "acrusher=bits=9:mode=lin:samples=3:aa=0.3:mix=1,lowpass=f=4500,lowpass=f=4500,"
           "aecho=0.8:0.75:70|140|210:0.35|0.25|0.15",
           "Dull and cavernous, fourth on the quality ladder. Blurs off the highs, adds a soft grain "
           "and a big, echoing space around every sound. Pick this over PlayStation 2 if your "
           "sounds are harsh or hissy."),
    Effect("saturn", "A", "Sega Saturn",
           "acrusher=bits=10:mode=lin:samples=2:aa=0.5:mix=0.6,"
           "chorus=0.7:0.9:55|70:0.4|0.32:0.25|0.4:2|1.3,"
           "aecho=0.8:0.85:200|400|700|1100:0.35|0.25|0.18|0.1,lowpass=f=10000",
           "Dreamy and spacious, fifth on the quality ladder. A soft shimmer and long, floating "
           "echoes with a light grain, like the atmospheric, ethereal soundtracks of that era. "
           "Pick this for an otherworldly mood."),
    Effect("ps2", "A", "PlayStation 2",
           "acrusher=bits=8:mode=lin:samples=2:aa=0.01:mix=0.7,treble=g=5:f=5000",
           "Bright and gritty, bottom of the quality ladder. Keeps the sound dry and open but adds "
           "a fizzy, sandpaper grain. About as strong as Nintendo 64 with the opposite flavour: "
           "pick this if your sounds are dull rather than harsh."),

    # Group B: texture, destructive on purpose
    Effect("radio", "B", "A radio",
           "highpass=f=500,highpass=f=500,lowpass=f=3000,lowpass=f=3000,"
           "acompressor=threshold=-24dB:ratio=10:attack=5:release=80,volume=6dB,asoftclip=type=atan,"
           "acrusher=bits=10:mode=log:aa=1,aphaser=in_gain=0.9:out_gain=0.9:delay=4:decay=0.5:speed=1",
           "Thin, boxy and a little overdriven, like a voice coming out of a small radio speaker. "
           "Only the middle of the sound gets through, squashed flat with a faint swirl. A strong "
           "effect."),
    Effect("phone", "B", "A telephone",
           "aresample=8000,highpass=f=300,highpass=f=300,lowpass=f=3400,lowpass=f=3400,"
           "acompressor=threshold=-22dB:ratio=10:attack=3:release=60,volume=4dB,asoftclip=type=tanh,"
           "acrusher=bits=8:mode=log:aa=1:mix=1",
           "Narrow, tinny and crackly, like someone on an old phone line. Squeezed into the same "
           "small slice of sound a real phone call carries. Thinner than the radio. A strong effect."),
    Effect("megaphone", "B", "A megaphone / PA",
           "highpass=f=600,highpass=f=600,lowpass=f=3800,lowpass=f=3800,equalizer=f=1500:t=q:w=1:g=6,"
           "volume=10dB,asoftclip=type=atan:param=2,acompressor=threshold=-20dB:ratio=8:attack=1:release=40,"
           "aecho=0.8:0.7:20|45:0.35|0.2",
           "Harsh, honky and blown-out, like an announcement through a megaphone or a station PA, "
           "with a short slap of echo. One of the strongest effects."),
    Effect("underwater", "B", "Underwater",
           "lowpass=f=700,flanger=speed=0.25:depth=4:delay=7:width=75,aecho=0.9:0.8:40:0.25,"
           "vibrato=f=2:d=0.15",
           "Deep, muffled and wobbly, as if heard from under the water. Only the low end gets "
           "through, with a watery swirl, a slow warble and a soft echo. A strong effect."),
    Effect("tape", "B", "An old cassette tape",
           r"vibrato=f=0.6:d=0.45,vibrato=f=7:d=0.15,volume=8dB,asoftclip=type=tanh,"
           r"aphaser=in_gain=0.85:out_gain=0.9:delay=5:decay=0.3:speed=0.2,tremolo=f=0.35:d=0.25,"
           r"aeval=val(ch)+0.006*(random(0)*2-1):c=same,acrusher=bits=11:mode=log:aa=1,"
           r"lowpass=f=4500,lowpass=f=4500,highpass=f=100",
           "Warbly, hissy and worn, like a cassette that's been played a hundred times. The pitch "
           "wavers, the level breathes, the sound is dull, smeared and swirly, with tape hiss "
           "underneath. A strong effect."),
    Effect("vinyl", "B", "An old vinyl record",
           r"vibrato=f=0.55:d=0.25,volume=6dB,asoftclip=type=tanh,"
           r"highpass=f=300,highpass=f=300,lowpass=f=4500,lowpass=f=4500,equalizer=f=1200:t=q:w=1:g=5,"
           r"acrusher=bits=10:mode=log:aa=1:mix=0.5,aeval=val(ch)+0.0025*(random(0)*2-1)"
           r"+if(gt(random(1)\,0.9997)\,(random(2)-0.5)*0.5\,0):c=same,lowpass=f=7000,highpass=f=150",
           "Old and crackly, like a worn record on a gramophone: pops and crackle, a soft hiss, a "
           "slow wobble and a narrow, honky, slightly distorted tone. A strong effect."),
    Effect("distant", "B", "Far away in another room",
           "lowpass=f=1200,lowpass=f=1200,highpass=f=150,aecho=0.6:0.8:30|65|110|170:0.5|0.4|0.3|0.2,"
           "lowpass=f=2500",
           "Muffled and hollow, as if the sound plays in another room behind a closed door. Only a "
           "dull thud gets through the wall, wrapped in room echo. A strong effect."),
    Effect("gritty", "B", "Gritty (mild)",
           "highpass=f=60,volume=10dB,asoftclip=type=tanh,equalizer=f=2500:t=q:w=1.5:g=4,"
           "acrusher=bits=8:mode=log:mix=0.5:aa=1,acompressor=threshold=-20dB:ratio=4:attack=1:release=40,"
           "alimiter=limit=0.95",
           "Rough and edgy. Drives the sound into warm distortion with extra bite, so any sound "
           "gets more abrasive while staying listenable. It won't sound louder: loudness is still "
           "matched afterwards."),
    Effect("brutal", "B", "Brutal (heavy)",
           # The drive comes first: a compressor in front (round 2) pulled the peaks down so far
           # that the +20 dB never reached the clipper, and Brutal came out softer than Gritty
           "highpass=f=90,volume=24dB,asoftclip=type=hard,equalizer=f=2800:t=q:w=1.5:g=6,"
           "acrusher=bits=4:mode=log:aa=0.01:mix=1,volume=6dB,asoftclip=type=hard,"
           "acrusher=bits=3:mode=lin:aa=0.01:mix=0.4,lowpass=f=10000,alimiter=limit=0.98",
           "Deliberately wrecks the sound: clipped, crushed and fizzing, with everything flattened "
           "into one wall of noise. Note that it won't sound louder: the program still matches "
           "loudness afterwards so everything stays consistent."),

    # Group C: corrective polish
    Effect("podcast", "C", "Podcast polish",
           "highpass=f=80,equalizer=f=3500:t=q:w=1.5:g=2,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100",
           "Clearer, more even speech. Removes low rumble, lifts the voice so words come through, "
           "and gently evens out loud and quiet moments. A subtle effect made for spoken word."),
    Effect("punchy", "C", "Punchy sound effects",
           "acompressor=threshold=-26dB:ratio=6:attack=15:release=90:makeup=3,"
           "equalizer=f=80:t=q:w=1:g=6,equalizer=f=4500:t=q:w=1.5:g=5,equalizer=f=400:t=q:w=1:g=-3,"
           "asoftclip=type=tanh,alimiter=limit=0.95",
           "Big, hard-hitting impacts. Lets the first crack of every hit through, then thickens the "
           "body, with a heavy low end and a sharp top. A strong effect made for game sounds."),
    Effect("warm", "C", "Warm & fuzzy",
           "equalizer=f=180:t=q:w=1:g=5,treble=g=-6:f=5000,lowpass=f=10000,volume=8dB,asoftclip=type=tanh,"
           "acompressor=threshold=-22dB:ratio=3:attack=20:release=200",
           "Soft, thick and cosy. Rounds off the highs, adds body and a gentle fuzz, like an old "
           "valve amplifier. A clear but friendly effect."),
    Effect("bright", "C", "Bright & crisp",
           "highpass=f=100,equalizer=f=300:t=q:w=1:g=-3,treble=g=5:f=6000,aexciter=amount=4:freq=3000,"
           "alimiter=limit=0.95",
           "Clear, crisp and sparkly. Clears up muddiness and adds fresh detail to the highs, good "
           "for recordings that sound dull or muffled. A clear effect."),
)

BY_TAG = {e.tag: e for e in EFFECTS}

if tuple(BY_TAG) != EFFECT_TAGS:
    raise RuntimeError("core.effects and core.naming.EFFECT_TAGS disagree")
if any(float(aa) < MIN_CRUSHER_AA for e in EFFECTS for aa in re.findall(r"aa=([\d.]+)", e.chain)):
    raise RuntimeError(f"an acrusher aa below {MIN_CRUSHER_AA} can output NaN")


def dropdown_rows() -> list[tuple[str, str | None]]:
    """(text, tag) in dropdown order. tag is None for the non-selectable group headers."""
    rows = [(NO_EFFECT_LABEL, NO_EFFECT)]
    for key, title in GROUPS.items():
        rows.append((f"─── {title} ───", None))
        rows += [(e.label, e.tag) for e in EFFECTS if e.group == key]
    return rows


def describe(tag: str) -> str:
    return BY_TAG[tag].description if tag in BY_TAG else NO_EFFECT_DESCRIPTION


def filter_chain(tag: str, sample_rate: int, level_db: float = 0.0) -> str:
    """The -af chain for an effect. `level_db` first brings the file to the target level, so
    the crushers, compressors and clippers hit every file equally hard however quiet it came
    in. The chain ends back at `sample_rate`, so an effect changes the texture, not the
    output file's rate."""
    effect = BY_TAG[tag]
    # FFmpeg's vibrato reads a few unwritten buffer slots at the very start: the first samples
    # come out as garbage, sometimes NaN, different every run. A filter after it (tape's
    # lowpass) spreads a NaN over the whole file, and LAME then crashes on it. So vibrato
    # gets 20 ms of silence to chew on, cut off again straight after.
    chain = re.sub(r"vibrato=([^,]*)", r"adelay=20:all=1,vibrato=\1,atrim=start=0.02,asetpts=PTS-STARTPTS",
                   effect.chain)
    if effect.group == "A":
        chain = f"aresample={LADDER_RATE},{chain}"
    return f"volume={level_db:.2f}dB,{chain},aresample={sample_rate or 48000}"


def apply_effect(source: Path, dest: Path, tag: str, sample_rate: int, runner: FFmpegRunner,
                 level_db: float = 0.0) -> None:
    """Write `source` with the effect applied to `dest` as a 32-bit float WAV: lossless, and
    float keeps the overs that volume=+3dB and friends can add, so the gain stage can pull
    them back down instead of them being clipped here."""
    run_checked(runner, [
        "ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(source), "-map", "0:a:0",
        "-af", filter_chain(tag, sample_rate, level_db), "-c:a", "pcm_f32le", str(dest),
    ], "Applying the effect")
