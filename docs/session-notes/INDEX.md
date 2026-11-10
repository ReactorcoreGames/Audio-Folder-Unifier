# Session Notes — Index

What each build session did, found and decided, moved here from `checklist.md` so the checklist stays short. Read a file only when its topic is relevant; the lasting decisions are also in `CLAUDE.md` → Known Issues and in `docs/closed-questions.md`.

| File | Session | Read it for |
|---|---|---|
| [session0_setup.md](session0_setup.md) | Setup | How the prototypes and old docs were reorganised |
| [session1.md](session1.md) | 1: Scaffold and theme | Icon, window size in physical pixels, FFmpeg tree kill, first build size, `build_release.bat` zip fix, the author's test files |
| [session2.md](session2.md) | 2: Scan, measure, normalize | `core/` file roles, loudnorm 192 kHz resample, `-map 0:a:0`, silent files, own-suffix skip |
| [session3.md](session3.md) | 3: Effects, silence, pipeline | `test/run_folder.py`, float WAV temps, the two Slicer changes, worker callback contract |
| [session4.md](session4.md) | 4: GUI | Auto-scan on folder pick, one worker / job numbers, height budget, dropdown cap, GUI checklist |
| [session5.md](session5.md) | 5: Listening tests (4 rounds) | Sample folders and run/report scripts, loudnorm clamp, vibrato NaN, acrusher NaN, true-peak ceiling, every effect's revision history |
| [session6.md](session6.md) | 6: Edge cases | `test/session6_edge.py`, writable-folder probe, memory-mapped silence removal, `_folder_problem()`, large batch numbers |
| [session7.md](session7.md) | 7: Release | Release materials, promo scripts, build excludes, clean-copy exe test, gitignore |

At the end of a session, add `sessionN.md` here and a row to this table.
