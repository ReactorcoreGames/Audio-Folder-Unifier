# Stats for Nerds

Every number behind Audio Folder Unifier, and why it was chosen. Everything runs on FFmpeg; the filter chains below are what the program passes to `-af`.

## The order of operations

For each file:

1. **Silence removal** (if chosen), on the original.
2. **Level stage + effect** (if an effect is chosen): the file is first brought to -13 dBFS RMS peak, then the effect runs. Rendered to a 32-bit float WAV temp, so a lossy original isn't encoded twice and any overs the effect creates aren't clipped before the gain stage pulls them back.
3. **Measurement** of the result.
4. **Loudness match** and encode to the output format.

**Effects come before measurement.** Measuring first would let the effect shift the loudness afterwards and break the consistency the program exists for.

**The level stage before the effect** matters because crushers, compressors and clippers act on absolute level. Without it, a quiet file came out of NES or Brutal much more (or less) wrecked than a loud one.

## Content categories

These only choose the measurement method and target. No EQ, no compression: nothing here reshapes the sound.

| Category | Method | Target | Loudness range | Ceiling |
|---|---|---|---|---|
| Sound Effects | RMS peak, static gain | -13.0 dBFS RMS peak | n/a | -1.0 dBTP |
| Voice & Speech | EBU R128 two-pass `loudnorm` | -16 LUFS | LRA 11 | -1.5 dBTP |
| Music Tracks | EBU R128 two-pass `loudnorm` | -14 LUFS | LRA 11 | -1.0 dBTP |
| Ambient Loops | EBU R128 two-pass `loudnorm` | -20 LUFS | LRA 15 | -1.5 dBTP |

- **Why RMS peak for sound effects:** integrated loudness (LUFS) needs several seconds of material and gates out quiet parts. A 200 ms explosion measures as near-silence and gets boosted into clipping. The loudest short-window RMS (`astats` "RMS peak", highest channel) tracks how loud a blip *feels*. The gain is a plain `volume=NdB`, so the sound's character is untouched.
- **Under 3 seconds, always RMS peak**, whatever the category. Same reason: loudnorm can't judge material that short.
- **-16 LUFS** is the podcast/spoken-word convention. **-14 LUFS** is the streaming level (Spotify, YouTube, Apple Music). **-20 LUFS** leaves ambience sitting under other audio; its wider LRA keeps the natural swell of rain or wind.
- **The ceiling is a true peak**, measured as the higher of `astats`' sample peak and `ebur128`'s true peak. A sample-peak-only ceiling missed the inter-sample overshoot of the aliasing presets, and FFmpeg's `volumedetect` reads float overs as 0 dB.
- **Accepted shortfall:** when the gain needed would push peaks over the ceiling, loudnorm switches to its dynamic mode and lands under target (peaky speech measured -17.4 LUFS for a -16 target). No pre-limiting is added, because a limiter would reshape the sound. In Sound Effects the ceiling simply caps the gain.
- loudnorm resamples to 192 kHz internally; the output is returned to the source's own sample rate.
- First-pass values outside loudnorm's accepted ranges (a hard-clipped file can measure above 0 LUFS) are clamped before the second pass.

## Quiet-file detection

A file is "unusually quiet" when its RMS peak is **10 dB or more below the folder's median**. Relative, so a folder of deliberately quiet ambience doesn't flag everything. Needs at least 5 files with audio for the median to mean anything. Silent files are never flagged.

## Silence

The silence detector is ported from an earlier prototype's `Slicer` (pure NumPy): RMS over 80 ms windows, every 20 ms.

| Setting | Value | Why |
|---|---|---|
| Threshold | -40 dBFS, lowered with the file's level (never above -40) | Silence removal runs before the level match, so a quiet recording's soft passages would otherwise count as silence |
| Shortest part kept | 300 ms | The prototype's 3000 ms returned any file under 3 s untouched, i.e. nearly every sound effect |
| Pauses kept whole | up to 0.5 s | Natural pauses in speech survive |
| Kept at each end ("Trim the start and end") | 100 ms | Onsets and fades survive |

Long files are decoded to a memory-mapped temp file and processed in blocks (about 1.1 GB of RAM for a 1-hour stereo file).

## Effects: Group A, the quality ladder

**This is a severity ladder with console flavour, not console emulation.** The names are a yardstick for how hard the degradation hits; a layperson knows "NES" is rougher than "PS2". Each rung carries a trait its console is remembered for, but none of them models that console's sound hardware. They're ordered by severity, not release date.

Why degrade on purpose: files from different sources differ in *texture* (sample rate, noise floor, bandwidth), not just level. Level matching alone doesn't make a crunchy 22 kHz sample belong next to a pristine 48 kHz one. Pushing everything through the same quality bottleneck gives a shared texture floor. The degradation *is* the unification. It can only pull down: a file already worse than the rung stays worse.

The grit is `acrusher`'s `samples=N` sample-and-hold with almost no anti-aliasing: hold every Nth sample, so the lost highs fold back as aliasing, the way old hardware sounded. A clean resample only muffles. The chains run at 44.1 kHz so N means the same for every file (44100 / N = the hold rate), then return to the file's own rate. `aa` is never 0: at exactly 0, `acrusher` outputs NaN on some signals.

| Rung | Character | Hold rate / bits | Chain |
|---|---|---|---|
| 1. NES | thin and buzzy (440 Hz one-pole highpass, like the console's output stage) | 4.4 kHz / 5-bit | `highpass=f=440:p=1,acrusher=bits=5:mode=lin:samples=10:aa=0.01:mix=1` |
| 2. SNES | muffled and crunchy, faint echo | 8.8 kHz / 6-bit | `acrusher=bits=6:mode=lin:samples=5:aa=0.01:mix=1,lowpass=f=4000,lowpass=f=4000,aecho=0.8:0.4:110:0.15` |
| 3. PlayStation 1 | lo-fi, metallic, early-3D room reverb | 22 kHz / 9-bit | `acrusher=bits=9:mode=lin:samples=2:aa=0.01:mix=1,lowpass=f=9000,aecho=0.8:0.7:40\|75\|115\|160:0.35\|0.28\|0.2\|0.12` |
| 4. Nintendo 64 | dull and cavernous, big echo | 14.7 kHz (smoothed) / 9-bit | `acrusher=bits=9:mode=lin:samples=3:aa=0.3:mix=1,lowpass=f=4500,lowpass=f=4500,aecho=0.8:0.75:70\|140\|210:0.35\|0.25\|0.15` |
| 5. Sega Saturn | atmospheric: chorus shimmer, echoes up to 1.1 s | 22 kHz / 10-bit, 60% mix | `acrusher=bits=10:mode=lin:samples=2:aa=0.5:mix=0.6,chorus=0.7:0.9:55\|70:0.4\|0.32:0.25\|0.4:2\|1.3,aecho=0.8:0.85:200\|400\|700\|1100:0.35\|0.25\|0.18\|0.1,lowpass=f=10000` |
| 6. PlayStation 2 | dry, bright, fizzy grain | 22 kHz / 8-bit, 70% mix | `acrusher=bits=8:mode=lin:samples=2:aa=0.01:mix=0.7,treble=g=5:f=5000` |

Nintendo 64 and PlayStation 2 are about equally strong with opposite flavours: N64 for harsh or hissy sources, PS2 for dull ones. A rung that couldn't be told apart from its neighbours in listening tests was cut, not shipped as padding (the first PS2 was, before it was rebuilt).

## Effects: Group B, "sounds like it's coming from"

Destructive by intent, like Group A.

| Preset | Chain |
|---|---|
| A radio | `highpass=f=500,highpass=f=500,lowpass=f=3000,lowpass=f=3000,acompressor=threshold=-24dB:ratio=10:attack=5:release=80,volume=6dB,asoftclip=type=atan,acrusher=bits=10:mode=log:aa=1,aphaser=in_gain=0.9:out_gain=0.9:delay=4:decay=0.5:speed=1` |
| A telephone | `aresample=8000,highpass=f=300,highpass=f=300,lowpass=f=3400,lowpass=f=3400,acompressor=threshold=-22dB:ratio=10:attack=3:release=60,volume=4dB,asoftclip=type=tanh,acrusher=bits=8:mode=log:aa=1:mix=1` |
| A megaphone / PA | `highpass=f=600,highpass=f=600,lowpass=f=3800,lowpass=f=3800,equalizer=f=1500:t=q:w=1:g=6,volume=10dB,asoftclip=type=atan:param=2,acompressor=threshold=-20dB:ratio=8:attack=1:release=40,aecho=0.8:0.7:20\|45:0.35\|0.2` |
| Underwater | `lowpass=f=700,flanger=speed=0.25:depth=4:delay=7:width=75,aecho=0.9:0.8:40:0.25,vibrato=f=2:d=0.15` |
| An old cassette tape | `vibrato=f=0.6:d=0.45,vibrato=f=7:d=0.15,volume=8dB,asoftclip=type=tanh,aphaser=in_gain=0.85:out_gain=0.9:delay=5:decay=0.3:speed=0.2,tremolo=f=0.35:d=0.25,aeval=val(ch)+0.006*(random(0)*2-1):c=same,acrusher=bits=11:mode=log:aa=1,lowpass=f=4500,lowpass=f=4500,highpass=f=100` |
| An old vinyl record | `vibrato=f=0.55:d=0.25,volume=6dB,asoftclip=type=tanh,highpass=f=300,highpass=f=300,lowpass=f=4500,lowpass=f=4500,equalizer=f=1200:t=q:w=1:g=5,acrusher=bits=10:mode=log:aa=1:mix=0.5,aeval=val(ch)+0.0025*(random(0)*2-1)+if(gt(random(1)\,0.9997)\,(random(2)-0.5)*0.5\,0):c=same,lowpass=f=7000,highpass=f=150` |
| Far away in another room | `lowpass=f=1200,lowpass=f=1200,highpass=f=150,aecho=0.6:0.8:30\|65\|110\|170:0.5\|0.4\|0.3\|0.2,lowpass=f=2500` |
| Gritty (mild) | `highpass=f=60,volume=10dB,asoftclip=type=tanh,equalizer=f=2500:t=q:w=1.5:g=4,acrusher=bits=8:mode=log:mix=0.5:aa=1,acompressor=threshold=-20dB:ratio=4:attack=1:release=40,alimiter=limit=0.95` |
| Brutal (heavy) | `highpass=f=90,volume=24dB,asoftclip=type=hard,equalizer=f=2800:t=q:w=1.5:g=6,acrusher=bits=4:mode=log:aa=0.01:mix=1,volume=6dB,asoftclip=type=hard,acrusher=bits=3:mode=lin:aa=0.01:mix=0.4,lowpass=f=10000,alimiter=limit=0.98` |

- **Doubled filters** (`lowpass=f=3000,lowpass=f=3000`) make a steeper 24 dB/octave slope out of FFmpeg's 12 dB/octave biquads.
- **Telephone** runs at 8 kHz with log ("mu-law"-like) 8-bit crushing, inside the 300-3400 Hz band a real phone line carries.
- **Tape and vinyl noise** comes from `aeval` with `random()`, which is seeded, so a file comes out identical every run. Vinyl's crackle is about 13 pops a second. Tape has two vibratos: slow wow and faster flutter.
- **vibrato pad:** FFmpeg's `vibrato` writes garbage (sometimes NaN) into its first few samples, different every run. The program puts 20 ms of silence in front of it and trims it off afterwards.
- **Brutal** drives first and never compresses: an earlier version had a compressor in front that pulled the peaks so low the drive never reached the clipper, and it came out softer than Gritty. Now its crest factor is 2.8 dB, against about 9 for Gritty and 12 for the original.
- **Gritty and Brutal won't sound louder:** distortion raises perceived loudness, so the RMS-peak match afterwards turns them down. That's what keeps the batch consistent.

## Effects: Group C, polish & finish

Corrective rather than destructive.

| Preset | Chain |
|---|---|
| Podcast polish | `highpass=f=80,equalizer=f=3500:t=q:w=1.5:g=2,acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100` |
| Punchy sound effects | `acompressor=threshold=-26dB:ratio=6:attack=15:release=90:makeup=3,equalizer=f=80:t=q:w=1:g=6,equalizer=f=4500:t=q:w=1.5:g=5,equalizer=f=400:t=q:w=1:g=-3,asoftclip=type=tanh,alimiter=limit=0.95` |
| Warm & fuzzy | `equalizer=f=180:t=q:w=1:g=5,treble=g=-6:f=5000,lowpass=f=10000,volume=8dB,asoftclip=type=tanh,acompressor=threshold=-22dB:ratio=3:attack=20:release=200` |
| Bright & crisp | `highpass=f=100,equalizer=f=300:t=q:w=1:g=-3,treble=g=5:f=6000,aexciter=amount=4:freq=3000,alimiter=limit=0.95` |

Punchy's 15 ms attack lets the transient through before the compressor clamps, which is what makes hits crack.

## Encoding

| Output | Settings |
|---|---|
| MP3 | LAME VBR `-q:a 2` (~190 kbps) |
| OGG | Vorbis `-q:a 7` (~224 kbps) |
| M4A / AAC (when kept as original) | 192 kbps |
| WAV, FLAC and other lossless | FFmpeg's lossless defaults |

Only the first audio stream is used (`-map 0:a:0`), so an MP3's cover art doesn't turn into a video stream in an OGG. Sample rates are kept as they were.

## Testing

Measured on a test folder of real and generated files (short SFX, long speech, music, ambience, a silent file, a corrupt file, a clipped file, a very quiet file) with every category and every effect: zero clipped samples and no true peak over the ceiling in any output. The loudnorm categories land within ±0.2 dB of target except the peaky material noted above. Every effect was rendered at 4 input levels on 5 sources with no NaN. 600 files in one batch: about 0.9 s per file with silence removal and an effect, and the window stayed responsive.
