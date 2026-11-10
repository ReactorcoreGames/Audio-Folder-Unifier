# Session 2 — Core pipeline: scan, measure, normalize

**Session 2 (2026-11-09):** core scan / measure / normalize, all UI-free, every FFmpeg/ffprobe call through `FFmpegRunner`. `python test/check_core.py` passes (~1 min, most of it on the long real files in `test/testfiles/`).
- **Files:** `core/formats.py` (extensions, `encode_args()`, output format), `core/naming.py` (output names, category/effect tags, own-suffix detection), `core/scan.py`, `core/measure.py` (`probe()`, `measure_rms_peak()`, `measure_loudness()` = loudnorm pass 1, `find_quiet()`, `FFmpegError` with `.stderr_tail` for the log), `core/normalize.py` (`normalize_file(work, output, category, runner)` → `NormalizeResult` with `method`, `detail` for the log, `silent`, `fell_back`).
- **`naming.EFFECT_TAGS` must match the Session 3 effect registry.** `core/effects.py` should import or assert against it rather than keep a second list.
- **loudnorm outputs 192 kHz**, so the second pass ends with `aresample=<source rate>`. Checked: outputs keep 44.1k / 24k.
- **`-map 0:a:0` on every encode and measurement**, so an mp3's cover art doesn't become a Theora video stream in `.ogg` output. Checked with a generated mp3 that has cover art.
- **Silent files are still written** (unchanged level, log `silent, left as is`) so the output folder is complete. Failed/stopped encodes delete their truncated output.
- **Own-suffix skip refined:** only skipped when the original sits beside it (open question #1 asks the author to confirm).
- **For Session 5:** big loudnorm boosts land a bit under target and near the ceiling after lossy encoding: chillnew.mp3 (-29 LUFS) → -14.8 LUFS, true peak -0.6 dBTP as .ogg (target -14 / -1.0). loudnorm drops to its dynamic mode when the gain would break the true-peak limit, and Vorbis encoding adds a few tenths of overshoot. Not clipping, but listen for it.
- **For Session 3:** the GUI log text uses `→`; any command-line runner must `sys.stdout.reconfigure(encoding="utf-8")` (the Windows console is cp1252). Temp files: the spec inherits "same extension as the original", but a lossless WAV temp avoids a double lossy encode; decide there.
