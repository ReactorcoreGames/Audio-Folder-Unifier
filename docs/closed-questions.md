# Closed Questions

Resolved design decisions, kept with their reasoning since the *why* matters more than the *what* when revisiting later. Numbers match the original question list; #4 (palette hex values) was settled in Session 1.

---

## 1. The silence checkbox — RESOLVED

**Original concern:** the checkbox said "Trim silence from the start and end" but the ported `Slicer` also removes silence in the middle.

**This was a false problem — the constraint was invented, not real.** Checking the actual code (`audio_silence_remover.py` lines 87 and 122-127), the Slicer explicitly handles leading and trailing silence as special cases *alongside* the middle ones. It already trims the ends. There was never a separate "edge-only" mode to choose between.

**DECIDED: one checkbox, full Slicer, no radio buttons.** Use the salvaged Slicer exactly as written. The wording just needs to match reality:

- Checkbox label: **"Remove silent parts"**
- Tooltip: notes that it cuts silence anywhere in the file, not only at the ends

Simplest possible resolution, and it removes a control rather than adding one.

---

## 2. Where does "Lo-fi tape" go? — RESOLVED

**DECIDED: Group B**, labelled **"An old cassette tape"**, sitting with radio / telephone / underwater. It's a texture effect, not a corrective finish.

---

## 3. Should silence trimming add a filename tag? — RESOLVED

**DECIDED: yes, but a short one — `_x`.**

Rationale: without a tag, running the same folder once with trimming and once without means the second run silently overwrites the first. A tag prevents that. `_x` keeps it from bloating filenames that already carry a category tag and possibly an effect tag.

```
explosion.wav                        → explosion_sfx.wav
explosion.wav + trimming             → explosion_sfx_x.wav
explosion.wav + trimming + PS1       → explosion_sfx_ps1_x.wav
```

Tag order: `<basename>_<category>[_<effect>][_x].<ext>` — the `_x` always goes last.

---

## 5. Console preset differentiation — RESOLVED

**DECIDED: option C — ship all six, with the weaker three given distinguishing character and the rate spacing widened.**

The framing changed, which dissolved the original concern. These were never meant as console *emulations* — they're a **severity ladder for quality-matching**, where console names serve as a relatable yardstick for how hard the degradation hits. Under that framing, N64/Saturn/PS2 sitting between PS1 and untouched isn't redundancy, it's the missing rungs of the dial.

Changes made:
- Reordered strongest → gentlest so the dropdown reads as a dial
- Group retitled from "Retro Game Consoles" to **"Match Everything to One Quality Level"** (the old title promised emulation)
- Rate spacing widened — the first draft bunched PS1/N64/Saturn at 22050/22050/24000
- N64 and Saturn deliberately trade crush vs filtering: N64 crushes less but filters more (dull), Saturn crushes more but stays open (gritty). Same severity, opposite flavour.

Full values in `docs/presets.md`. Still needs a listening test to confirm rungs 4-6 are audibly distinct — if they aren't, drop to just NES/SNES/PS1 rather than ship padding.

**Also decided:** no "Gentle — barely noticeable" rung below PS2. It would be indistinguishable from "No change", which already exists as the default.

---

## 6. Program name — RESOLVED

**DECIDED: Audio Folder Unifier stays.**

Alternatives considered: *Sound Batch* (vague about what it does), *Make It Match* (warm and states the user's goal, but doesn't say it's audio — bad for store search), *Audio Levelizer* (implies loudness only, undersells the texture-matching half), *Batch Sound Unifier* (marginal difference), *Uniform* (too generic to find).

The deciding factor: **literal descriptiveness beats cleverness for store discovery.** Someone searching itch.io for "audio normalizer batch" needs to land on this. *Make It Match* was the only serious contender and it loses on searchability.

---

## 7. Salvage from folder #2 — RESOLVED

**ASMR presets: cut, confirmed.** Already covered by a dedicated existing program for ASMR and hypnosis audio. No need to duplicate it here.

**Aggressive music presets: salvaged and reframed.** Added as **Gritty (mild)** and **Brutal (heavy)** — but as *effects that make any sound abrasive*, not as mastering chains for already-brutal music the way folder #2 framed them. That reframing makes them far more useful in a batch tool.

They go in **Group B (texture), not Group C (polish)** — they make audio worse on purpose, same as the console ladder. Putting "Brutal" next to "Podcast polish" would be exactly the category confusion this dropdown's grouping exists to prevent.

Chains in `docs/presets.md`. One caveat to surface in the description text: heavy distortion raises perceived loudness, so the RMS-peak pass afterwards pulls gain *down* — "Brutal" won't sound louder, and a user might expect it to.

---

## 4. Exact palette hex values — RESOLVED

The direction is decided: a colourful 2000s-era music player look (Winamp skins, early iTunes, WMP 9). The base is a medium blue-green, not too dark and not too saturated, with neon yellow/lime accents. Details are in `docs/gui_spec.md` → Theme.

Still to pick: the exact hex values for `PALETTE` in `gui/theme.py`. The plan is for Claude to propose a palette in Session 1, show it in the running window (screenshot in `shots/`), and let the author approve or tweak it there. The neon accents stay off body text (they fail contrast) and are used for borders, the progress fill, active states and selection.

Is that approach fine, or do you have specific colours or a reference skin in mind? (Reference images can go in `inspo/`.)

**Session 1 proposal, now live in `gui/theme.py`.** Screenshot: `shots/palette_proposal.png` (and `shots/built_exe.png` for the built exe with its title bar). The window body is a static mock of the real layout so every widget type can be judged; Session 4 replaces it with the working sections.

| Job | Hex | Notes |
|---|---|---|
| Window background | `#1D525B` | medium blue-green |
| Panels (the four sections) | `#26656F` | one step lighter |
| Input wells (entries, dropdown, description box, log, progress trough) | `#123A41` | dark "LCD display" wells, the main media-player cue |
| Secondary buttons (Browse, Open output folder) | `#30808B` / hover `#3B95A1` | |
| Neon lime | `#C8FF2E` | radio/checkbox fill, progress fill, focus and hover borders, selection, header underline. Only ever a fill or border, with dark ink `#0B2226` on top |
| Neon yellow | `#F2FF5C` | hover on Start/Stop |
| Pale lime | `#E4FF9C` | section titles, subtitle, footer link, log text (6.0:1 on panels) |
| Borders | `#4FA0A9` | |
| Body text | `#F2FBF7` | 6.3:1 on panels, 8.3:1 on background |
| Dimmed text | `#C4E2DD` | tech anchors, captions (4.8:1 on panels) |
| Start / Stop | `#4FD86E` / `#FF6F6F` | dark ink on both |

Every text colour passes WCAG AA 4.5:1 against what it sits on. To tweak, name the job and the direction ("panels a bit bluer", "lime more yellow") or give hex values.

Author: Style looks good and so does the layout. (2026-11-09)

**DECIDED: the Session 1 proposal ships as is**, including the compact layout (one-line header, 900x960 window).

---

## 8. Skipping files that look like earlier output — RESOLVED

**Original concern:** the spec skipped any input file whose name carries the output suffix (`door_sfx.wav`). Sound libraries often name files like that (`explosion_sfx.wav`, `theme_music.mp3`), and they would have been silently ignored.

**DECIDED: keep the Session 2 refinement.** A file with the suffix is skipped only when its original sits beside it (`door_sfx.wav` next to `door.wav`), which is exactly what a run with output folder = input folder leaves behind. Output folders inside the input are never scanned regardless.

Author: "I'll go with your recommendation. The spec files were written by a more incompetent Sonnet, so your Claude Opus 5.5 opinion takes priority and you are free to make choices regarding this to make the program better for it." (2026-11-09)

---

## 9. Session 3 choices against the spec — RESOLVED

**Original concern:** Session 3 departed from the spec in five places and asked the author to check them: the Slicer's `min_length` 300 ms instead of 3000 (so short files get trimmed at all), a silence threshold that follows each file's level (never above -40 dB), 32-bit float WAV temp files, Group A rungs returning to each file's own sample rate instead of a fixed 48 kHz, and a same-output-name clash logged as failed instead of overwriting.

**DECIDED: all five stand as built.**

Author: "1. Yes, this is better. 2. Good. 3. Ok. 4. Ok - the original was set by Sonnet so it may have been inadequate, hence your Opus 5.5 direction is superior. 5. Ok." (2026-11-09)

The author also couldn't find a processed `chillnew.mp3` to listen to: Session 3's command-line runs wrote to a scratch folder, not `test/testfiles/`. That listening check moves to Session 5, run from the GUI.

---

## 10. The regenerated icon — RESOLVED

**Original concern:** the author asked for an icon about "harmonization of audio". Two BAIG attempts (Session 4, `shots/icon_gen2/`): A, a glowing speaker in a cluttered control room; B, a teal head with headphones, eyes closed, on a plain teal backdrop.

**DECIDED: B.** It is now `assets/icon_og.jpg`, with `assets/icon.ico` rebuilt from it (16-256 px). The first icon (the braided-gadgets image) and its .ico are retired to `old wip/retired_icon/`.

Author: "Lets actually use B - its perfect for what I need. It looks good and also works better as the icon too. Retire the original icon_og." (2026-11-09)

---

## 11. A log.txt file — RESOLVED

**Original request (author, Session 5):** the log box is small and narrow, so keep an accumulating `log.txt` that each session's log lines are appended to. The user deletes it if it grows too big; its first line says so.

**DONE in Session 5:** `utils/logfile.py`, called from `JobsMixin.log()`, so every line the box shows also goes to `log.txt` next to the exe. First line: "log.txt is where anything that happens in the program is printed. If this file grows too big, you can safely delete it - the program will make a fresh, empty one." Each session gets a `=== date time ===` header with its first line, so a session that logs nothing adds nothing. Write errors are swallowed like `config.json`'s. Spec: `docs/gui_spec.md` → Section notes → Progress area.

---

## 12. Session 5 listening, round 1 — RESOLVED

**Original concern:** round 1 of the listening tests (`shots/session5/`): the Group A ladder, N64 / Saturn / PS2, Gritty vs Brutal, every other preset, and chillnew.mp3 with "Remove silent parts".

Author (2026-11-09), in the chat: NES, SNES, PS1, N64, Saturn, PS2, cassette tape, vinyl, far away, Punchy ("much harder please!"), Warm & fuzzy and Bright & crisp "could be plenty more dramatic". OK but "maybe a bit more oomph": radio, telephone, megaphone, Gritty, Brutal. Fine: No change, Underwater ("fairly good"), Podcast polish. PS2: "admittedly this one is indeed mild, I am willing to axe it." A "normal or strong" toggle was considered and dropped for simplicity. Pointed at `C:\14 Repos\Script-To-Voice-Generator-KokoroTTS` and `C:\14 Repos\Audio-Satanifier-666`, "especially the middle-level setting of the effects in those as the target to aim for".

Author, in the file: "a. yeah I'd want more dramatic difference between them, especially NES getting pushed even lower. Saturn and PS2 are indeed faint. I think Saturn could be made stylized somehow and maybe PS2 in some way even if it's not quite accurate to the real deal but sort of emulates a core aesthetic that those consoles have. I'd say the SNES, N64 and PS1 could also lean more into that since they mostly sound rather normal even if intentionally "degraded". c. yes distinct, but the all could be made even more stronger in their respective styles, stronger/rougher. e. Hmm interesting, so does that mean the trim silence actually snips silences in the middle? I had thought that it only snips away silence at the ends [...] I think I'd want there to be both option - one that just trims the ends, and the other that trims like it does now. It did indeed make the chillnew podcast-like asmr speech feel a bit more snappier with less/shorter pauses in between but otherwise it stayed fairly intact."

**DECIDED (round 2, `shots/session5_round2/`):** every effect rebuilt to the strength of the two earlier programs (Kokoro "medium", Satanifier "subtle"); Group A rungs keep the severity order but each gets its console's signature; PS2 cut; every file brought to the target level before its effect; silence became a dropdown (Keep it / Trim the start and end / Remove all silent parts). Details in `docs/presets.md` and `docs/processing_spec.md`; round 1 values in `old wip/effects_v1/`.

---

## 13. Voice files landing ~1.5 dB quiet — RESOLVED

**Original concern:** speech's peaks are high for its loudness, so loudnorm can't raise it fully without passing the true-peak limit, switches to its "dynamic" mode and undershoots (generated speech: -17.4 LUFS in Voice, target -16). Limiting the peaks first hits the target but reshapes the sound (chillnew needed 16.7 dB of limiting to gain 0.7 dB).

Author: "I don't know because the technical aspect goes over my head, I think I will go with your recommendation on this. If its perhaps useful in some way, maybe checking "C:\14 Repos\Script-To-Voice-Generator-KokoroTTS" project in what it did might be interesting just in case." (2026-11-09)

**DECIDED: no pre-limiting.** 1-1.5 dB is about the smallest loudness step most people notice, and the categories promise not to reshape the sound. The Kokoro project was checked: single clips are peak-normalized to 0 dBFS (`apply_peak_normalize()`), and the merged script gets one single-pass `loudnorm=I=-14:TP=-1.5:LRA=11` (`audio_merger.py` → `_apply_loudnorm()`). Single-pass loudnorm always runs in the dynamic mode, so it has the same undershoot; nothing there does better than what we have.

---

## 14. Session 5 listening, round 2 — RESOLVED

**Original concern:** the round 2 effects (`shots/session5_round2/`), rebuilt to the strength of the author's earlier programs.

Author (2026-11-09): "NES - good. SNES - feel a bit too echo-y and missing some level of bitcrushing/lower quality that makes it be in the middle zone between NES and N64. N64 - also feels somewhat echo-y which I think is okay, but it need a quality reduction a little bit too. PS1 - good. Saturn - good... but I think its preset should be given over to a revived PS2 preset and Saturn itself would get something that captures the "Atmospheric & Ethereal" style that some games in that era tended to favor. vinyl - I like the crackles, but I think the sound texture/feel could be altered more. tape - it still sounds somewhat normal. [...] gritty - good. brutal - strange... it feels softer than gritty [...] I think this needs a much harder effect. underwater - I like it, its good, but I was wondering if the STVG's underwater preset had a bit more texture to it? if so, lets add it to this one too. The rest feel good." On the normal/strong toggle: "Ok that settles it, keeping it simple then."

**DECIDED (round 3, `shots/session5_round3/`):** SNES less echo, more crush; N64 a little more grain; the round 2 Saturn chain became PlayStation 2 (back in the dropdown, bottom rung) and Saturn became atmospheric and ethereal (chorus shimmer, long floating echoes, light grain); vinyl a narrow, honky gramophone tone with the same crackle; tape borrows STVG's worn-tape phaser and narrow band, with deeper wobble, a breathing level and more hiss; underwater got STVG's flanger (it was the texture ours lacked). Brutal had a bug rather than weak values: its compressor ran before the drive and pulled the peaks too low to ever clip (crest factor 10.4 dB, Gritty 9.1); now it drives first, crest 2.8 dB. No normal/strong toggle, one strength per preset.

---

## 15. Session 5 listening, round 3 — RESOLVED

Author: "Round 3 is good, I think we got it where I wanted it to." (2026-11-09)

**DECIDED:** the round 3 effects ship as they are (`shots/session5_round3/`).
