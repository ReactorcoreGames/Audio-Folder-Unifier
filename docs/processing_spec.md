# Processing Specification

The pipeline, the FFmpeg commands, and file handling rules.

---

## Supported formats

**Input:** `.wav .mp3 .ogg .opus .flac .m4a .aac .aiff .aif .wma` **Output:** same as original, or forced to `.wav` / `.mp3` / `.ogg`.

Encoder settings when re-encoding (inherited from `audio_unifier.py`):

| Extension | Args |
|---|---|
| `.ogg` | `-q:a 7` |
| `.mp3` | `-q:a 2` |
| `.aac` / `.m4a` | `-b:a 192k` |
| `.wav` / `.flac` / other | none (lossless defaults) |

Temp files between steps are always 32-bit float WAV (Session 3): lossless, so a lossy original isn't encoded twice, and float keeps the overs an effect can add (`volume=3dB`) until the gain stage pulls them down. With no silence removal and no effect there is no temp file at all.

---

## The pipeline

Per file, in this exact order:

```
1. (optional) Trim silence          → temp file
2. (optional) Apply effect filter   → temp file
3. Measure loudness                 ← on the RESULT of steps 1-2
4. Apply gain + encode              → output file
```

**Step 3 measuring after steps 1-2 is load-bearing.** If we measured the original and then applied an effect, the effect would shift the loudness and break consistency. This is why no effect can violate the unification guarantee.

Steps 1 and 2 can't share one FFmpeg graph: the Slicer runs in numpy. Step 1 writes a temp WAV, step 2 reads it and writes another, and both are deleted as soon as the file is done (`core/pipeline.py`).

---

## Step 1 — Silence trimming (optional, off by default)

Uses the `Slicer` class ported from `1 Audio Library Mass Normalizer and Quiet Detector/V3 Final Ready For Compile/audio_silence_remover.py` (lines 42-140). That class is **pure numpy** — it picks cut points at RMS minima, which gives smoother joins than FFmpeg's `silenceremove`. Keep it verbatim; it works.

**Replace only the loader.** The original called `librosa.load()`. Instead:

```
ffmpeg -i <input> -f f32le -acodec pcm_f32le -ac <n> -ar <sr> -
```
→ in the pipeline FFmpeg writes the raw PCM to a temp file that is memory-mapped (`np.memmap`), reshaped to channels. Reading it from stdout (`np.frombuffer`, still used by `test/session5_report.py`) holds the whole decode twice while the pipe is read.

Get `sr` and channel count from `ffprobe` first. Write the result with `soundfile`, then hand the temp WAV to step 2 or 3.

This drops librosa, scipy, scikit-learn and numba (~150MB) while keeping the algorithm.

Slicer parameters: `threshold=-40dB, min_length=300, min_interval=300, hop_size=20, max_sil_kept=500`. No GUI exposure — the old program's sensitivity slider is cut as unnecessary complexity for a checkbox feature. Two changes from the working code (Session 3):

- **`min_length` 300, not 3000.** The Slicer returns any file shorter than `min_length` untouched, which with 3000 was nearly every sound effect (a 2.6 s blip with 2.3 s of padding came out unchanged), and it only cut a middle pause once 3 s had passed since the last cut. Pauses up to `max_sil_kept` (0.5 s) are still kept whole, so natural pauses in speech survive; longer gaps shrink to about 0.5 s.
- **The threshold follows the file's level:** -40 dB below where the level matching will put it, `min(-40, -40 + rms_peak - (-13))`, using the RMS peak the scan already measured. Silence removal runs before the level matching, so with a fixed -40 dBFS a quiet recording's soft passages counted as silence (a -29 LUFS music file lost 119 of 421 s; now 63, the rest is its real quiet stretches). It never goes above -40, so a loud file is never trimmed harder than the prototype trimmed it.

`get_rms` was rewritten to sum squares per hop instead of building the strided frame matrix: same values (checked), a fraction of the memory (the original needed ~4x the file's samples as a temporary, 2.7 GB for an hour of 48 kHz audio). Since Session 6 it also works a block at a time (`RMS_BLOCK_HOPS`) and adds the zero padding per block, and the kept parts are written to the temp WAV a block at a time instead of joined first. Measured on a 1-hour stereo mp3 with "Remove all silent parts": 3.8 GB peak before, 1.1 GB private now (the mono mix the Slicer needs, plus the memory-mapped decode, which Windows can page out). The temp disk use is the decode, ~1.3 GB per stereo hour, deleted as soon as the file is done.

If the Slicer leaves nothing (an all-silent file), the file is passed on unchanged.

**Two modes** (Session 5; the author wanted both after hearing chillnew):

- **Remove all silent parts** (`silence: "all"`, tag `_x`): the full Slicer. It removes silence *anywhere* in the file — leading, trailing, and middle (original code lines 87 and 122-127). chillnew.mp3: 7:01 → 5:59.
- **Trim the start and end** (`silence: "ends"`, tag `_t`): `core.silence.trim_ends()`. Same RMS measure, hop, window and threshold as the Slicer, so "silence" means the same thing; cuts before the first and after the last frame above the threshold, keeping 100 ms (`EDGE_KEPT_MS`) at each end so onsets and fades survive. Pauses inside are left alone. chillnew.mp3: 7:01 → 6:59.

The GUI shows a dropdown, Keep it / Trim the start and end / Remove all silent parts, default Keep it.

---

## Step 2 — Effect filter (optional, off by default)

Single `-af <chain>` pass using the chain from `docs/presets.md`, built by `core.effects.filter_chain()`. It starts with `volume=<gain>dB`, the gain that puts the file's RMS peak (from the scan) on the -13 dBFS target, so every effect hits a quiet file as hard as a loud one (Session 5). Step 4 still sets the final level.

```
ffmpeg -y -i <input> -map 0:a:0 -af "<chain>" -c:a pcm_f32le <temp>.wav
```

Every chain ends with `aresample=<source rate>`, so an effect changes the texture, not the output file's rate (Group A works at 44.1 kHz, telephone at 8 kHz).

---

## Step 3 — Measurement

### For Sound Effects (and any file under 3 seconds)

```
ffmpeg -i <file> -af astats,ebur128=peak=true:framelog=quiet -f null NUL
```

Parse stderr:
- `RMS peak dB:` → take the **maximum** across all channel occurrences
- `Peak level dB:` (astats, sample peak) and ebur128's true `Peak:` → `max_peak` is the higher of the two

Not `volumedetect` (the prototype's choice): it converts to 16-bit, so it reads 0 dB for a float temp file that an effect pushed above full scale, and the gain then left the overs in (Session 5: 11 clipped samples from vinyl's crackle). The true peak also catches the overshoot between samples that the aliasing in Group A creates (NES measured +0.5 dBTP with a -1.0 dB sample peak).

```
gain = TARGET_RMS_PEAK_DB - rms_peak          # TARGET = -13.0
gain = min(gain, TRUE_PEAK_CEILING_DB - max_peak)   # CEILING = -1.0
```

If `rms_peak` is None (silent file), gain = 0 and log it as skipped. The file is still written to the output (unchanged level) so the output folder stays complete; the log says `silent, left as is`. Same for a file loudnorm measures at or below -70 LUFS.

This is exactly `audio_unifier.py`'s `measure()` — reuse it.

### For Voice / Music / Ambient (files ≥ 3 seconds)

Two-pass EBU loudnorm. First pass with `print_format=json` to get measured values, second pass feeding them back in via `measured_I`, `measured_TP`, `measured_LRA`, `measured_thresh`, `offset`. Single-pass loudnorm is noticeably less accurate and should not be used.

Targets per category are in `docs/presets.md`.

### The under-3-seconds rule

Get duration from `ffprobe`. Any file shorter than 3.0s uses the Sound Effects method regardless of the chosen category, and the log notes it: `clip.wav — too short for loudness matching, used sound-effect method instead`.

---

## Step 4 — Output

```
ffmpeg -y -i <work> -af "volume=<gain>dB" <encoder args> <output>
```

For loudnorm categories, step 4 is the second loudnorm pass rather than a plain gain. loudnorm works and outputs at 192 kHz, so the second pass ends with `aresample=<source rate>`; without it a WAV comes out at 192 kHz.

The first pass's values are clamped to the ranges the second pass accepts (`measured_I` and `measured_thresh` at most 0, and so on; `core/normalize.py` → `MEASURED_RANGES`). A file clipped hard enough measures above 0 LUFS, and the second pass then refused to start, so the file failed in every loudnorm category (Session 5: a music excerpt pushed 12 dB into clipping measured +0.2 LUFS). Clamping costs at most those few tenths of a dB.

Every output encode and measurement uses `-map 0:a:0`: only the first audio stream. Otherwise an mp3's cover art becomes a video stream in the output (a Theora video inside an `.ogg`). A failed or stopped encode deletes its truncated output.

---

## File and folder handling

### Scanning
- Non-recursive by default; recursive when "Include subfolders" is checked.
- **Always skip the output folder** when scanning, even if it sits inside the input folder. Prevents the program discovering its own previous output on a re-run.
- Also skip any file whose name already carries this program's output suffix (below) **and whose original sits beside it** (`door_sfx.wav` next to `door.wav`): that's what a run with output = input leaves behind. Belt and braces against re-processing. Without the original next to it, `door_sfx.wav` is more likely a sound library's own naming and gets processed (Session 2 refinement, see open-questions.md).

### Output naming

Originals are never modified. Output filenames get a suffix describing what was done, so re-running with the *same* settings cleanly overwrites its own previous output, while changing settings writes alongside rather than clobbering.

```
<original basename>_<category tag>[_<effect tag>][_t|_x].<ext>
```

**Category tags:** `sfx`, `voice`, `music`, `ambient`

**Effect tags:**

| Group | Tags |
|---|---|
| A — quality level | `nes`, `snes`, `ps1`, `n64`, `saturn`, `ps2` |
| B — texture | `radio`, `phone`, `megaphone`, `underwater`, `tape`, `vinyl`, `distant`, `gritty`, `brutal` |
| C — polish | `podcast`, `punchy`, `warm`, `bright` |

**Silence tag:** `_t` for "Trim the start and end", `_x` for "Remove all silent parts", always last, absent for "Keep it". Short deliberately — names already carry a category tag and possibly an effect tag.

Examples:
```
explosion.wav                     → explosion_sfx.wav
explosion.wav + PS1               → explosion_sfx_ps1.wav
explosion.wav + PS1 + all silence → explosion_sfx_ps1_x.wav
narration.mp3 + trim the ends    → narration_voice_t.mp3
narration.mp3 → OGG               → narration_voice.ogg
```

This means re-running with identical settings cleanly overwrites its own previous output, while changing *any* setting writes alongside rather than clobbering.

### Subfolder mirroring

With "Include subfolders" on, the output mirrors the input tree:

```
input/                        output/
  metal/clang.wav       →       metal/clang_sfx.wav
  wood/thud.wav         →       wood/thud_sfx.wav
```

Create output subdirectories as needed.

### Quiet-only mode

Every file gets measured during the scan pass anyway. A file is flagged "unusually quiet" if its RMS peak is **more than 10 dB below the median RMS peak** of the whole folder. Relative, not absolute — a folder of deliberately quiet ambience shouldn't flag every file.

The scan reports the count. If the user then checks "Only fix the files that are unusually quiet", processing skips everything not flagged.

If fewer than 5 files are found, skip the median comparison entirely (not enough data for a meaningful median) and disable the checkbox with an explanatory tooltip.

---

## Subprocess rules

- Hide console windows on Windows — pass `startupinfo=_ffmpeg_startupinfo()` to every `subprocess.run()` (pattern in the RC standard doc).
- Temp files in the system temp dir, uniquely named per file (**not** the shared fixed name `unify_tmp.ext` that `audio_unifier.py` uses — that breaks if processing is ever parallelised, and leaks on crash). Clean up in a `finally`.
- Stop button: set a flag checked between files, and kill any running FFmpeg process so a long file doesn't delay the stop. All FFmpeg calls go through `utils.ffmpeg.FFmpegRunner`, which does both. It kills the whole process tree (`taskkill /T`), not just the process: on the author's PC `ffmpeg` is a Chocolatey shim, and `terminate()` only killed the shim while the real ffmpeg kept running (Stop waited for the whole file).

---

## Error handling

Per-file try/except. A failure logs and continues, unless the folders are the cause (below). Final summary: `44 succeeded, 3 failed`. Log the FFmpeg stderr tail for failures so the user has something to report.

Cases to handle explicitly (all tested in Session 6, `test/session6_edge.py`):
- Corrupt / unreadable file → log, skip
- Silent file (`RMS peak = -inf`) → gain 0, log as skipped
- Output folder not writable → stop with a clear message before starting (`check_output_dir()`, which writes a probe file of its own: `tempfile` on Windows retries "access denied" up to 2^31 names and hung the window)
- Zero audio files found → Start says so in a dialog before creating the output folder, and suggests ticking "Include subfolders" when there are folders inside
- Two inputs that map to the same output name (`door.wav` + `door.flac` with output forced to `.mp3`) → the second is logged as failed instead of overwriting the first
- An earlier output that is read-only → that file is logged as failed with the reason, the rest go on
- **The folders as the cause** (`_folder_problem()` in `core/pipeline.py`, asked whenever a file is missing or fails): the From folder gone, the To folder no longer writable, or under 20 MB free on its disk → the batch stops with one message (log + dialog) instead of failing every remaining file. Also when every remaining file is gone but the folder isn't: Windows can't delete or move the file FFmpeg has open, so deleting the From folder mid-run usually leaves the folder with that one file in it. The From folder is checked first, because `check_output_dir()` creates missing folders and would bring back a deleted From folder that contained the To folder.
- The From folder vanishing during the folder check → the check ends with "Couldn't check the folder: the From folder is gone", not one "Can't read" line per file
