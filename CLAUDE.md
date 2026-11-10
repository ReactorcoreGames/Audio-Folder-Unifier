# Audio Folder Unifier — Claude Session Context

## What This Program Does

Point it at a folder of audio files. It writes out a new folder where every file sounds consistent with the others, optionally with a stylization effect applied. One window, layperson-friendly, compiled Windows exe. Released (v1) on 2026-11-09, MIT licensed. Graduated to `C:\14 Repos\Audio-Folder-Unifier` the same day.

## Standards

Follows the RC standard. Read at the start of a session that changes code:
- `C:\ClaudeWorkspace\!RC Standard CORE\!RC standard dev pack info.md` (project-wide rules; it wins any conflict)
- `C:\ClaudeWorkspace\!RC standard python\standard python program by RC.md`
- `C:\ClaudeWorkspace\!RC standard python\ttkbootstrap_gui_guidelines.md` (ttkbootstrap 2.x)

## Key Docs

- `checklist.md`: the session plan. New work gets a new session there. **Start here.**
- `open-questions.md`: questions waiting for the author
- `docs/INDEX.md`: overview, design principles, document map
- `docs/gui_spec.md`: window layout and behaviour (window size budget, ttkbootstrap quirks)
- `docs/processing_spec.md`: pipeline, FFmpeg commands, file handling, error handling
- `docs/presets.md`: all preset values, the source of truth (copied from `core/effects.py`)
- `docs/closed-questions.md`: resolved decisions and their reasoning
- `docs/session-notes/INDEX.md`: what each build session did and found, one file per session. Read only the one relevant to the task.
- Shipped docs at the root: `readme.md`, `guide.md`, `stats-for-nerds.md`, `LICENSE`. `promo.md` is internal store copy. **If a preset value or behaviour changes, update `docs/presets.md`, `stats-for-nerds.md` and, if user-visible, `guide.md`.**

## Folder Layout

```
Audio-Folder-Unifier/
├── main.py                ← entry point
├── gui/                   ← app.py (window, shared helpers), sections.py (sections 1-4), jobs.py (Start/Stop, progress, worker thread), theme.py
├── core/                  ← UI-free pipeline: formats, naming, scan, measure, normalize, effects, silence, pipeline (the batch)
├── utils/                 ← paths.py, config.py, logfile.py (log.txt), ffmpeg.py (PATH check, stoppable FFmpegRunner)
├── test/                  ← see Testing below; generated sample folders are gitignored
├── assets/                ← icon_og.jpg + icon.ico
├── docs/                  ← specs, closed questions, session-notes/
├── promo/                 ← release images (built by test/promo_*.py)
├── shots/                 ← previews for the author: screenshots, listening-test renders (gitignored; the 1.6 GB Session 5 renders were trashed at graduation, rebuild with the listening-test scripts)
├── trailer/               ← YouTube trailer: plan (trailer.md) and render scripts; music, videos and work/ gitignored
├── inspo/prototypes/      ← the three original prototypes (gitignored); #3's audio_unifier.py is the heart of core/
├── old wip/               ← retired notes, round 1 effects, old icon (gitignored)
├── build/ dist/           ← PyInstaller scratch / the release (both gitignored)
├── readme.md, guide.md, stats-for-nerds.md, LICENSE, promo.md
├── checklist.md, open-questions.md, CLAUDE.md
├── build_release.bat
└── Reactorcore's Homepage.url
```

## Tech Stack

- Python 3.11+, ttkbootstrap 2.x (custom `"unifier"` theme family, used as `unifier-dark`; Segoe UI)
- FFmpeg on PATH: all decode/filter/encode/measure. Users get it from https://reactorcore.itch.io/ffmpeg-to-path-installer
- numpy + soundfile: silence Slicer only
- PyInstaller `--onedir` via `build_release.bat`: 31 MB folder, 23.6 MB zip, cold start ~1.5-3 s

Deliberately not used: librosa, scipy, pydub, pyloudnorm.

## Testing, building, promo

- `python test/check_core.py` (~1 min) and `python test/check_pipeline.py` (~15 s): quick checks; run after any core change.
- `python test/run_folder.py <folder> [--category music] [--effect ps1] [--silence] [--format ogg] ...`: the pipeline from the command line.
- `python test/shot_window.py [name] [WxH]`: screenshot the window into `shots/`.
- Listening tests (effect changes): `test/make_session5_samples.py`, then `test/session5_runs.py <shots folder>` drives the real window through every category and effect, `test/session5_report.py` measures the outputs and builds a listen folder. See `docs/session-notes/session5.md`.
- Edge cases (window/pipeline changes): `test/make_session6_samples.py`, then `test/session6_edge.py [case ...]`.
- Release: run `build_release.bat` (from bash: `echo | cmd //c "<full path>\build_release.bat"`). Then test a copy of `dist\Audio Folder Unifier\` outside the project.
- Promo images: `python test/promo_shots.py` (drives the window, raw shots into `shots/promo_raw/`), then `python test/promo_images.py` (composes `promo/`).
- Scripts that drive the real window back up and restore `config.json`. Message boxes block them, so scripts that can hit one swap it for a recorder.

## Known Issues / Decisions

- **RMS peak, not integrated loudness, for short files.** EBU loudnorm needs several seconds; a 200ms SFX blip measures as near-silence and gets boosted into clipping. Files under 3s always use the RMS-peak method regardless of chosen category.
- **Effects are applied before measurement.** Non-negotiable ordering — measuring first would let effects shift loudness and break consistency.
- **Effects run on the file already at the target level** (`core.effects.filter_chain(level_db=...)`, from the scan's RMS peak). Crushers, compressors and clippers act on absolute level; without this a quiet file came out of NES or Brutal far more wrecked than a loud one.
- **The content categories never apply EQ or compression**, so the "can't pick wrong" promise stays literally true. Anything destructive is opt-in in the effects dropdown.
- **Group A is a severity ladder with console flavour, not console emulation.** This is the single most important framing in the project and it's easy to get wrong. The console names are a *relatable yardstick for how hard the degradation hits* — a layperson intuits that "NES" is harsher than "PS2". They are not fidelity claims. Each rung also carries its console's signature (NES thin and buzzy, SNES muffled and crunchy, PS1 reverb, N64 dull and roomy, Saturn atmospheric and ethereal, PS2 bright and gritty), at the author's request.

  The purpose: sounds gathered from random sources differ in *texture* (sample rate, noise floor, bandwidth), not just level. Pushing everything through the same quality bottleneck forces a shared texture floor. **The degradation is the unification.** Order the dropdown by severity, never by console release date. Any rung that can't be told apart from its neighbours gets cut, not shipped as padding.

- **The quality floor only pulls down, never up.** Users should pick a rung at or below their worst file. This lives in `guide.md`, deliberately not in the GUI.
- **N64 and PS2 are opposite flavours at about the same strength**: N64 dull and roomy, PS2 dry and bright. Saturn is the mood rung (chorus and long echoes).
- **Effect strength is the author's call, by ear** (approved values: "round 3", `docs/session-notes/session5.md`). Reference points: `C:\14 Repos\Script-To-Voice-Generator-KokoroTTS` (`config.py` → `AUDIO_EFFECTS`, "medium") and `C:\14 Repos\Audio-Satanifier-666` (`script.js`, "subtle"). Check them before inventing values. Round 1 values are in `old wip/effects_v1/`.
- **Gritty / Brutal are Group B, not Group C**: they make audio worse on purpose. Heavy distortion raises perceived loudness, so the RMS-peak pass pulls gain *down*; "Brutal" won't sound louder (the description says so).
- **Silence is a three-way choice**: Keep it / Trim the start and end (`trim_ends()`, tag `_t`) / Remove all silent parts (the full Slicer, tag `_x`). Config key `silence`; an old `remove_silence: true` loads as `all`. The silence box is bound one way (box → var): a script that sets `vars["silence"]` must also set `silence_box.current()`.
- **Silence removal runs before the level match, so its threshold follows the file's level** (never above -40 dBFS), and the Slicer's `min_length` is 300 ms, not the prototype's 3000. See `docs/processing_spec.md` → Step 1.
- **Silence removal memory-maps its decode** (`core.silence.load_pcm(raw=...)`) and works in blocks. Don't go back to reading PCM from a pipe or joining the kept chunks: a 1-hour stereo file needed 3.8 GB that way (now 1.1 GB).
- **Stop must kill the FFmpeg process tree, not just the process.** `ffmpeg` on PATH is often a shim (Chocolatey, Scoop) that runs the real binary as a child. `utils.ffmpeg.FFmpegRunner` handles it; route every FFmpeg/ffprobe call through it.
- **FFmpeg's `vibrato` writes garbage (sometimes NaN) into its first few samples.** `core.effects.filter_chain()` pads 20 ms of silence before it and trims it after; keep that for any new chain using vibrato.
- **FFmpeg's `acrusher` outputs NaN at `aa=0`** on some signals. Use `aa=0.01`; `core/effects.py` refuses a lower value on import.
- **loudnorm's second pass rejects first-pass values outside its ranges** (a hard-clipped file measures above 0 LUFS). `core/normalize.py` clamps them (`MEASURED_RANGES`).
- **Peaky material lands under target in loudnorm categories** (speech -17.4 for -16). Accepted, no pre-limiting: limiting would reshape the sound (closed question #13).
- **The ceiling uses the true peak, not `volumedetect`.** volumedetect converts to 16-bit and reads 0 dB for float overs. `measure_rms_peak()` takes the higher of astats' sample peak and ebur128's true peak.
- **Never use `tempfile` to test whether a folder is writable.** On Windows it treats "access denied" as a name clash and retries up to 2^31 names: the window hung. `core.pipeline.check_output_dir()` writes its own probe file.
- **When the folders are the problem, the batch stops instead of failing every file** (`core.pipeline._folder_problem()`). It checks the From folder first: `check_output_dir()` creates missing folders and would bring back a deleted From folder that held the To folder.
- **Window sizes are physical pixels.** At the author's 125% scaling, 900x800 was only 720x640. 900x960 at y=10 is about the most a 1080p screen allows, and the layout already needs 958 px: any new control must replace space, not add it. Scripts that click the window must call `SetProcessDpiAwareness(2)` first.
- **Release excludes:** `build_release.bat` excludes yaml, psutil, setuptools, charset_normalizer and win32pdh, which numpy and cffi pull in through optional imports. Check `_internal\` after adding a dependency.
- **Not handled, on purpose:** FFmpeg uninstalled while the program runs (every file fails), paths over 260 characters (untested).
