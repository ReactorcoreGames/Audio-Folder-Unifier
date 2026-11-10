# Presets — Content Categories and Effects

All values here are the source of truth for implementation. The user-facing explanations of these numbers live in `stats-for-nerds.md`, shipped with the release.

---

## Part 1: Content Categories

The single required choice. Controls **normalization method and target only** — nothing here reshapes the sound. Picking the wrong one is recoverable: the audio comes out too quiet or too loud, and the user re-runs.

The GUI shows the peak/loudness terms as an anchor for users who've seen Audacity tutorials, plus the LUFS target for those who know what it means.

### Sound Effects
> *game sounds, foley, blips, UI clicks* **Peak-normalize style — RMS peak matching, target -13 dBFS**

- **Method:** RMS-peak unification (folder #3's technique)
- **Measurement:** FFmpeg `astats` → highest `RMS peak dB` across channels
- **Target:** `-13.0 dBFS` RMS peak
- **Ceiling:** `-1.0 dBFS` true peak (gain is clamped so nothing clips)
- **Processing:** static gain only (`volume=NdB`). No dynamics, no EQ.

Why not loudnorm: EBU integrated loudness needs several seconds of material. A 200ms explosion measures as near-silence and gets boosted into clipping. RMS peak tracks how loud a short blip *feels*.

### Voice & Speech
> *narration, podcasts, ASMR, audiobooks* **Loudness-normalize — target -16 LUFS**

- **Method:** EBU R128 two-pass loudnorm
- **Target:** `I=-16, LRA=11, TP=-1.5`
- **Rationale:** -16 LUFS is the podcast/spoken-word convention. LRA 11 preserves natural dynamics without squashing.

### Music Tracks
> *songs, loops, stingers* **Loudness-normalize — target -14 LUFS**

- **Method:** EBU R128 two-pass loudnorm
- **Target:** `I=-14, LRA=11, TP=-1.0`
- **Rationale:** -14 LUFS is the Spotify/YouTube/Apple Music streaming standard.

### Ambient Loops
> *rain, forest, machinery, room tone* **Loudness-normalize — target -20 LUFS**

- **Method:** EBU R128 two-pass loudnorm
- **Target:** `I=-20, LRA=15, TP=-1.5`
- **Rationale:** Ambience sits *under* other audio. -20 leaves headroom. Wider LRA because ambient beds have wide natural variation that shouldn't be flattened.

### Fallback rule (important)

Loudnorm is unreliable below roughly 3 seconds of material. **Any file shorter than 3 seconds falls back to the Sound Effects method regardless of chosen category**, and the log notes it. This prevents the classic failure where a short stinger in a music folder gets destroyed.

---

## Part 2: Effects Dropdown

One dropdown, titled **"Change the sound? (optional)"**, default **"No change — just fix the loudness"**. Grouped with non-selectable separator headers. A dynamic description label sits below it (≤300 chars, updates on selection).

Applied **before** measurement and gain — so no effect can break the loudness consistency guarantee. This ordering is load-bearing.

**Every file is brought to the target level (-13 dBFS RMS peak) before its effect** (Session 5). Crushers, compressors and clippers act on absolute level, so without this a quiet file came out of NES or Brutal far more wrecked than a loud one, which works against unification. The level stage is part of `core.effects.filter_chain()`; the level matching afterwards still sets the final loudness.

**Strength target** (Session 5 round 2, the author's listening verdict "plenty more dramatic"): the "medium" settings of the author's `C:\14 Repos\Script-To-Voice-Generator-KokoroTTS` (`config.py` → `AUDIO_EFFECTS`) and the "subtle" ones of `C:\14 Repos\Audio-Satanifier-666` (`script.js` → `applyEffect`). The round 1 values (Sonnet's spec) were barely audible; they are kept in `old wip/effects_v1/`.

`core/effects.py` is the single source for labels, chains and descriptions; the tables below are copied from it.

---

### Group A — Match Everything to One Quality Level

**Still a severity ladder, now with each console's signature sound** (the author's call in Session 5). The dropdown stays ordered strongest first and the console names are still a yardstick for how hard the degradation hits, not fidelity claims. What changed: round 1 only lowered the sample rate cleanly and crushed lightly, which the author heard as "rather normal". Each rung now also carries the trait people remember its console for (NES thin and buzzy, SNES muffled with echo, PS1's reverb, N64 dull and roomy, Saturn bright and gritty). That helps unification too: a shared character on top of a shared texture floor.

The retro grit comes from `acrusher`'s `samples=N` with almost no anti-aliasing (`aa=0.01`): hold every Nth sample, so the lost highs fold back as aliasing, the way old hardware sounded. Round 1's clean `aresample` only muffled. The chains run at 44.1 kHz so `samples=N` means the same for every file, and return to the file's own rate afterwards. **`aa` must stay above 0**: at exactly 0, acrusher outputs NaN on some signals (Session 5; `core/effects.py` refuses such a chain on import).

| Order | Preset | Character | Chain (after the level stage, at 44.1 kHz) |
|---|---|---|---|
| 1 | NES | harshest: thin (440 Hz one-pole highpass, like the console's output stage), 4.4 kHz hold, 5-bit | `highpass=f=440:p=1,acrusher=bits=5:mode=lin:samples=10:aa=0.01:mix=1` |
| 2 | SNES | muffled and crunchy, 8.8 kHz hold, 6-bit, steep 4 kHz lowpass, a faint single echo | `acrusher=bits=6:mode=lin:samples=5:aa=0.01:mix=1,lowpass=f=4000,lowpass=f=4000,aecho=0.8:0.4:110:0.15` |
| 3 | PlayStation 1 | lo-fi and metallic, 22 kHz hold with aliasing, 9-bit, early-3D room reverb | `acrusher=bits=9:mode=lin:samples=2:aa=0.01:mix=1,lowpass=f=9000,aecho=0.8:0.7:40|75|115|160:0.35|0.28|0.2|0.12` |
| 4 | Nintendo 64 | dull and cavernous: 9-bit, 14.7 kHz hold (smoothed), steep 4.5 kHz lowpass, big echo | `acrusher=bits=9:mode=lin:samples=3:aa=0.3:mix=1,lowpass=f=4500,lowpass=f=4500,aecho=0.8:0.75:70|140|210:0.35|0.25|0.15` |
| 5 | Sega Saturn | atmospheric and ethereal: light grain, chorus shimmer, long floating echoes (up to 1.1 s) | `acrusher=bits=10:mode=lin:samples=2:aa=0.5:mix=0.6,chorus=0.7:0.9:55|70:0.4|0.32:0.25|0.4:2|1.3,aecho=0.8:0.85:200|400|700|1100:0.35|0.25|0.18|0.1,lowpass=f=10000` |
| 6 | PlayStation 2 | bright and gritty: dry, 8-bit grain at 22 kHz hold (70% mix), treble lift | `acrusher=bits=8:mode=lin:samples=2:aa=0.01:mix=0.7,treble=g=5:f=5000` |

**Round 3 (Session 5):** the round 1 PS2 (practically identical to the original) was cut in round 2. In round 3 the author gave the round 2 Saturn chain (bright and gritty) to a revived **PlayStation 2**, and Saturn became **atmospheric and ethereal**, the dreamy reverb-heavy style some games of that era favoured. SNES lost most of its echo and gained crush (it should sit between NES and N64); N64 gained a little grain.

**N64 and PS2 are opposite flavours at about the same strength**: N64 dull and roomy, PS2 dry and bright. Pick N64 for harsh or hissy sources, PS2 for dull ones. Saturn is the mood rung: its echoes are the longest of any preset.

**No "Gentle — barely noticeable" rung.** Considered and rejected: it would be indistinguishable from "No change", which is already the default.

#### The floor only pulls down, never up

Quality-matching works when source files are *higher* quality than the chosen rung. It cannot repair the reverse: if one file is already a mangled 8kHz mp3 and the user picks PS2, that file stays mangled while everything else gets only a little grit.

Practical advice for users: **pick a rung at or below your worst file.**

This goes in **`guide.md`** (the user manual), *not* in the tooltip or the description box — it's a nuance that would clutter the main window, and it's the kind of thing a user should find when they go read the manual.

---

### Group B — Sounds Like It's Coming From

Texture effects. Destructive by intent, like Group A.

| Preset | Chain |
|---|---|
| A radio | `highpass=f=500,highpass=f=500,lowpass=f=3000,lowpass=f=3000,acompressor=threshold=-24dB:ratio=10:attack=5:release=80,volume=6dB,asoftclip=type=atan,acrusher=bits=10:mode=log:aa=1,aphaser=in_gain=0.9:out_gain=0.9:delay=4:decay=0.5:speed=1` |
| A telephone | `aresample=8000,highpass=f=300,highpass=f=300,lowpass=f=3400,lowpass=f=3400,acompressor=threshold=-22dB:ratio=10:attack=3:release=60,volume=4dB,asoftclip=type=tanh,acrusher=bits=8:mode=log:aa=1:mix=1` |
| A megaphone / PA | `highpass=f=600,highpass=f=600,lowpass=f=3800,lowpass=f=3800,equalizer=f=1500:t=q:w=1:g=6,volume=10dB,asoftclip=type=atan:param=2,acompressor=threshold=-20dB:ratio=8:attack=1:release=40,aecho=0.8:0.7:20|45:0.35|0.2` |
| Underwater | `lowpass=f=700,flanger=speed=0.25:depth=4:delay=7:width=75,aecho=0.9:0.8:40:0.25,vibrato=f=2:d=0.15` |
| An old cassette tape | `vibrato=f=0.6:d=0.45,vibrato=f=7:d=0.15,volume=8dB,asoftclip=type=tanh,aphaser=in_gain=0.85:out_gain=0.9:delay=5:decay=0.3:speed=0.2,tremolo=f=0.35:d=0.25,aeval=val(ch)+0.006*(random(0)*2-1):c=same,acrusher=bits=11:mode=log:aa=1,lowpass=f=4500,lowpass=f=4500,highpass=f=100` |
| An old vinyl record | `vibrato=f=0.55:d=0.25,volume=6dB,asoftclip=type=tanh,highpass=f=300,highpass=f=300,lowpass=f=4500,lowpass=f=4500,equalizer=f=1200:t=q:w=1:g=5,acrusher=bits=10:mode=log:aa=1:mix=0.5,aeval=val(ch)+0.0025*(random(0)*2-1)+if(gt(random(1)\,0.9997)\,(random(2)-0.5)*0.5\,0):c=same,lowpass=f=7000,highpass=f=150` |
| Far away in another room | `lowpass=f=1200,lowpass=f=1200,highpass=f=150,aecho=0.6:0.8:30|65|110|170:0.5|0.4|0.3|0.2,lowpass=f=2500` |
| Gritty (mild) | `highpass=f=60,volume=10dB,asoftclip=type=tanh,equalizer=f=2500:t=q:w=1.5:g=4,acrusher=bits=8:mode=log:mix=0.5:aa=1,acompressor=threshold=-20dB:ratio=4:attack=1:release=40,alimiter=limit=0.95` |
| Brutal (heavy) | `highpass=f=90,volume=24dB,asoftclip=type=hard,equalizer=f=2800:t=q:w=1.5:g=6,acrusher=bits=4:mode=log:aa=0.01:mix=1,volume=6dB,asoftclip=type=hard,acrusher=bits=3:mode=lin:aa=0.01:mix=0.4,lowpass=f=10000,alimiter=limit=0.98` |

Notes:
- **Telephone** runs at 8 kHz with log ("mu-law"-like) 8-bit crushing, the same narrow band (300-3400 Hz) a real phone line carries.
- **Tape and vinyl** add their noise with `aeval` (`random()` is seeded, so a file comes out the same every run): tape hiss, vinyl hiss plus about 13 crackles a second. Two vibratos on tape: slow wow and faster flutter.
- **vibrato** is padded inside `filter_chain()`: it writes garbage (sometimes NaN) into its first samples, so it gets 20 ms of silence that is trimmed off afterwards.
- **Underwater** got STVG's flanger (round 3) for a watery swirl; the rest is unchanged from round 1 (the author: "fairly good").
- **Tape** (round 3) borrows from STVG's worn tape: phaser swirl and a 4.5 kHz band, plus deeper wow and flutter, a breathing level (tremolo) and more hiss. **Vinyl** (round 3) became a worn record on a gramophone: a narrow, honky 300-4500 Hz band with a 1.2 kHz bump and light saturation; the crackle (which the author liked) is unchanged.
- **Brutal** (round 3) drives first and compresses never: in round 2 a compressor in front pulled the peaks so low the +20 dB drive never reached the clipper, and it came out softer than Gritty (crest factor 10.4 dB vs Gritty's 9.1). Now crest 2.8 dB, a wall of distortion.

**Gritty / Brutal** are the salvage of folder #2's aggressive music profiles, reframed as **effects that make any sound abrasive**, in Group B (destructive texture) rather than Group C (corrective polish).

> **Loudness caveat for Gritty/Brutal:** heavy distortion raises *perceived* loudness a lot, so the RMS-peak measurement afterwards pulls the gain down significantly. That is correct — it keeps the batch consistent — but a user may expect "Brutal" to also mean "louder" and be surprised it isn't. The description text says so.

---

### Group C — Polish & Finish

Corrective rather than destructive. The survivors of folder #2's 15-profile list. Podcast polish is unchanged (the author: OK); the other three were made much stronger in round 2.

| Preset | Chain |
|---|---|
| Podcast polish | `highpass=f=80,equalizer=f=3500:t=q:w=1.5:g=2,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100` |
| Punchy sound effects | `acompressor=threshold=-26dB:ratio=6:attack=15:release=90:makeup=3,equalizer=f=80:t=q:w=1:g=6,equalizer=f=4500:t=q:w=1.5:g=5,equalizer=f=400:t=q:w=1:g=-3,asoftclip=type=tanh,alimiter=limit=0.95` |
| Warm & fuzzy | `equalizer=f=180:t=q:w=1:g=5,treble=g=-6:f=5000,lowpass=f=10000,volume=8dB,asoftclip=type=tanh,acompressor=threshold=-22dB:ratio=3:attack=20:release=200` |
| Bright & crisp | `highpass=f=100,equalizer=f=300:t=q:w=1:g=-3,treble=g=5:f=6000,aexciter=amount=4:freq=3000,alimiter=limit=0.95` |

**No ASMR preset.** Folder #2's four ASMR/hypnosis profiles are deliberately cut — that use case is already covered by a dedicated existing program.

---

## Part 3: Description Text

Each dropdown entry has a ≤300-char plain-language description for the dynamic label, in `core/effects.py` (rewritten for round 2 in Session 5). Rules: no jargon in the first sentence, say what it *sounds like* before what it *does*, mention if the effect is strong or subtle, and for Group A mention its position on the ladder. `test/check_pipeline.py` checks the length.

---

## Validation Status

| Preset group | Status |
|---|---|
| Content categories | Values are industry-standard, confident. Measured in Session 5: loudnorm categories within ±0.2 dB, except peaky speech ~1.5 dB under (accepted, closed question #13) |
| Round 1 effects (Sessions 3-4) | Listened to in Session 5: too weak. Replaced |
| Round 2 effects (Session 5) | Listened to: NES, PS1, Gritty and most of Group B/C good. SNES, N64, Saturn/PS2, tape, vinyl, Brutal, underwater changed in round 3 |
| Round 3 effects (Session 5) | Approved by the author: "Round 3 is good" (2026-11-09) |
