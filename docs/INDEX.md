# Audio Folder Unifier — Design Overview

**Status:** released (v1, Session 7, 2026-11-09). This document and its siblings were written as the spec before the build and kept up to date during it, so they describe the program as it is.

---

## What This Program Does

The user points it at a folder of audio files. Those files are inconsistent — some quiet, some loud, some recorded differently. The program writes out a new folder where every file sounds consistent with the others, optionally with a stylization effect applied on the way.

One window. Pick two folders, pick what kind of audio it is, press the button.

**Target user:** a layperson who records or collects audio and wants pro-quality consistency without being an audio engineer. Push button, receive bacon.

---

## Origin — Three Folders, One Program

This project merges three earlier prototypes that were all circling the same idea:

| Folder | What it was | What survives |
|---|---|---|
| `1 Audio Library Mass Normalizer and Quiet Detector` | Quiet-file detection + normalization; became a Batch Audio Silence Remover | The `Slicer` class (silence removal). The quiet-detection *idea*, rebuilt on a better measurement. |
| `2 Audio mastering profile auto batch` | 15 mastering profiles (EQ/comp/limiter per content type) | The best few, folded into the effects dropdown as "Polish & Finish" entries. The 15-profile structure is cut as scope creep. |
| `3 audio normalizer miniapp` | Loudness unification via RMS-peak + stylization filters | **Everything.** This is the heart of the program. |

### Why folder #3 is the core

`audio_unifier.py` solved a problem the other two didn't know they had. EBU loudnorm (integrated loudness) is unreliable on sub-second SFX blips — they're too short to measure meaningfully. Folder #3 instead measures each file's **loudest short-window RMS** (FFmpeg `astats` "RMS peak"), which tracks how loud a blip actually *feels*, and applies a plain static gain. No dynamics processing, so the sound's character is untouched. A true-peak ceiling keeps it clip-safe.

That technique is the program's main value proposition and it is what "Sound Effects" mode uses.

### Two corrections made to the old prototypes

**Folder #1's quiet detection was broken.** Its algorithm returned "too quiet" only if *every* frame fell below threshold — so one door slam anywhere in an otherwise whisper-quiet file marked the whole thing as fine. Near-useless on real material. Replaced with RMS peak, which is a byproduct of the measurement pass the unifier already does, so detection is now essentially free and stops being a slow separate phase.

**Folder #1 didn't actually need librosa.** It only used `librosa.load()`; the clever `Slicer` class is pure numpy. Swapping the loader for FFmpeg-decode-to-numpy drops librosa, scipy, scikit-learn and numba (LLVM, 100MB+) while keeping the algorithm intact.

---

## Tech Stack

- **Python 3.11+**
- **ttkbootstrap** — GUI, with a *custom injected theme* (not a built-in theme). See `docs/gui_spec.md` and `ttkbootstrap_gui_guidelines.md` in the RC Python standard (ttkbootstrap 2.x).
- **FFmpeg on PATH** — all decoding, filtering, encoding, and measurement. Users get it from https://reactorcore.itch.io/ffmpeg-to-path-installer
- **numpy + soundfile** — only for the silence-removal Slicer.
- **PyInstaller `--onedir`** — target ~40MB.

Deliberately *not* used: librosa, scipy, pydub, pyloudnorm. Everything they'd provide, FFmpeg already does.

---

## Design Principles

1. **Can't-go-wrong presets.** The four content categories only control normalization method and target — safe, non-destructive, and a wrong pick is obvious and recoverable. Anything that *reshapes* the sound lives in the effects dropdown, opt-in and clearly labelled.
2. **Originals are never touched.** Output always goes to a separate folder.
3. **No jargon in the UI, jargon available on request.** The GUI says "Sound Effects"; `stats-for-nerds.md` says `-13 dBFS RMS peak, -1 dBTP ceiling`. Peak/loudness terms *are* shown as anchors for users who've seen Audacity tutorials.
4. **Everything optional is off by default.** Silence trimming, quiet-only mode, and stylization all start disabled. The default run is: unify loudness, nothing else.
5. **One window, no tabs.**

---

## Document Map

- `docs/INDEX.md` — this file
- `docs/gui_spec.md` — window layout, controls, wording, behaviour
- `docs/processing_spec.md` — the pipeline, FFmpeg commands, file handling
- `docs/presets.md` — content categories and all effect presets, with exact values
- `docs/closed-questions.md` — resolved design decisions and their reasoning
- `docs/session-notes/` — what each build session did and found, one file per session (`INDEX.md` lists them)
- `checklist.md` (project root) — the build plan in sessions
- `open-questions.md` (project root) — questions still waiting for the author

Shipped with the release (project root, copied by `build_release.bat`):
- `readme.md` — what it is, requirements, quickstart, MIT license (`LICENSE`)
- `guide.md` — the user manual. Home for nuances too detailed for the GUI, notably the "quality matching only pulls down, never up — pick a rung at or below your worst file" explanation.
- `stats-for-nerds.md` — every preset value with its reasoning
- `promo/` images (built by `test/promo_shots.py` + `test/promo_images.py`) and `Reactorcore's Homepage.url`

Not shipped: `promo.md` (internal store copy), `CLAUDE.md` and the dev docs.

---

Made by Reactorcore — https://reactorcoregames.github.io/
