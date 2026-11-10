# GUI Specification

Follows the RC standard: `C:\ClaudeWorkspace\!RC Standard CORE\!RC standard dev pack info.md`, plus `standard python program by RC.md` and `ttkbootstrap_gui_guidelines.md` in `C:\ClaudeWorkspace\!RC standard python\`. This document covers only what's specific to this program.

---

## Theme

**Custom theme, not a built-in one** (ttkbootstrap 2.x). Theme family `"unifier"`, registered with `ttk.Theme(...).register()` before `ttk.Window(themename="unifier-dark")`, then `apply_theme()` on top, exactly as in `ttkbootstrap_gui_guidelines.md`. The dark variant fits because body text is near-white on the medium blue-green base.

**Font:** `Segoe UI`. This is a technical/utility batch tool, which the font guidance puts firmly in sans-serif territory. `Consolas` for the log widget.

**Palette:** a colourful **2000s-era music player** look. Medium blue-green base — not too dark, not too saturated — with **neon yellow/lime accents**. Deliberately avoiding the overdone flat-dark / flat-light convention.

Reference feel: Winamp skins, early iTunes visualisers, WMP 9. Glossy, saturated, slightly playful — unmistakably a *media* application rather than a grey utility.

Constraints:
- WCAG AA 4.5:1 for body text. **The neon accents will almost certainly fail contrast as text colour** against a medium blue-green background — restrict them to borders, progress-bar fill, active/hover states, and selection highlights. Body copy stays on a high-contrast near-white.
- Semantic colours must remain recognisable (green reads green, red reads red)
- `ttk.Theme` needs the five accent colours (primary, success, info, warning, danger) and a background/foreground pair; `apply_theme()` sets the exact surfaces, inputs and borders on top

Exact hex values are the one remaining open item — see `open-questions.md`.

**Window:** 900x960 default, placed near the top of the screen (y=10), minsize 860x920. Resizable. Do *not* start maximized — this is a compact single-purpose window, not a workspace.

These are physical pixels: Tk on the author's 1080p screen at 125% scaling works in physical pixels, so the original 900x800 (written before any code) was really 720x640 and cut off everything below section 4. The full layout needs ~943px of height; a 1080p screen leaves ~980 for the window at 125%. To fit, the header is one line (title, then subtitle beside it), the current-file label and the scan summary share one row under the progress bar, and the log is 4 lines tall and the part that shrinks. Rechecked on the real window in Session 4: `winfo_reqheight()` is 943 and `winfo_reqwidth()` 786, so 960 leaves 17 px spare and at the 920 minimum the log still shows about 3 lines. Both `tk.Text` widgets need `width=1`, or their default 80 characters force the window to 870 px wide, past the 860 minimum.

**Widgets that need special handling in ttkbootstrap 2.2.3** (found in Session 1):
- Progress bar: use `style="Neon.Horizontal.TProgressbar"` (a flat clam bar defined in `apply_theme()`). The stock one is a recoloured image with a stray end-cap and an uncolourable trough.
- Log scrollbar: `bootstyle="secondary-round"` gives a teal thumb; `style.configure()` doesn't reach the image-based scrollbar.
- Entry and Combobox text needs `font=FONT_BODY` on the widget itself; the style font doesn't apply to the text inside.
- Keep a reference to every `tk.StringVar` / `BooleanVar`, or it's garbage-collected and the widget shows blank (checkboxes show an indeterminate dash).

---

## Layout

One window, no tabs. Four labelled sections stacked vertically, then controls, then progress/log.

```
┌──────────────────────────────────────────────────────────────┐
│  Audio Folder Unifier   Make a whole folder of audio sound…  │  ← title + subtitle, one line
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ 1. Choose your folders ─────────────────────────────┐   │
│  │  From: [C:\sounds\explosions            ] [ Browse ] │   │
│  │    To: [C:\sounds\explosions\unified    ] [ Browse ] │   │
│  │  [x] Include subfolders (output keeps the same tree) │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 2. What kind of audio is this? ─────────────────────┐   │
│  │  (o) Sound Effects    game sounds, foley, blips      │   │
│  │      peak-normalize style, target -13 dBFS           │   │
│  │  ( ) Voice & Speech   narration, podcasts, ASMR      │   │
│  │      loudness-normalize, target -16 LUFS             │   │
│  │  ( ) Music Tracks     songs, loops, stingers         │   │
│  │      loudness-normalize, target -14 LUFS             │   │
│  │  ( ) Ambient Loops    rain, forest, machinery        │   │
│  │      loudness-normalize, target -20 LUFS             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 3. Change the sound? (optional) ────────────────────┐   │
│  │  [ No change — just fix the loudness            ▾ ]  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Leaves the character of your audio alone and   │  │   │
│  │  │ only evens out how loud everything is.         │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ 4. Extras (optional) ───────────────────────────────┐   │
│  │  Silence: [ Keep it          ▾ ]  [ ] Only fix the…  │   │
│  │  Save as: (o) Same as original ( ) WAV ( ) MP3 ( ) OGG│  │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│       [    Start    ]          [    Stop    ]                │  ← big buttons
│                                                              │
│  [███████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  22 / 47     │
│  Now processing: explosion_03.wav   Found 47 audio files · 6… │
│  ┌─ Log ────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [ Open output folder ]        Made by Reactorcore  [link]   │
└──────────────────────────────────────────────────────────────┘
```

---

## Section notes

### 1. Folders
- Both Entry widgets are readonly, filled by `filedialog.askdirectory()`.
- **No drag-and-drop** (RC standard). Buttons only.
- "To" auto-fills to `<From>\unified` when a From folder is picked, and is editable afterwards via its own Browse button.
- Right-click context menu on both entries (RC standard) — Copy/Select All will work, Paste no-ops on readonly, which is correct.
- On Start, re-validate both paths still exist. If From is gone, clear it and tell the user.
- Warn if To is inside From *and* "Include subfolders" is on — that would make the program discover its own output on a re-run. Simplest fix: always skip the output folder during scanning. See `docs/processing_spec.md`.

### 2. Content category
- Radio buttons, default **Sound Effects**.
- Each has a two-line label: plain description, then the technical anchor in `secondary` styling (smaller, dimmer). Both peak/loudness wording and LUFS target shown.
- Tooltip per option expanding on what it's for.

### 3. Effects dropdown
- `ttk.Combobox`, readonly (no free text).
- Grouped with non-selectable separator rows. If ttk Combobox can't do genuinely non-selectable entries, render them as `─── Match Everything to One Quality Level ───` and ignore selection of them (snap back to previous value).
- **Group A is ordered by severity, strongest first** — the list is meant to read as a dial, not a chronology. Do not reorder it to console release order.
- Three groups, in this order:
  1. `─── Match Everything to One Quality Level ───` (NES → PS2, harshest to lightest)
  2. `─── Sounds Like It's Coming From ───` (radio, telephone, underwater, gritty, brutal…)
  3. `─── Polish & Finish ───` (podcast, punchy, warm, bright)
- **Dynamic description label below**, ≤300 chars, updates on `<<ComboboxSelected>>`. Fixed height of 3 lines so the layout doesn't jump between selections (the longest description is 3 lines at the 860 minimum width). It's a disabled `tk.Text`, not a Label, so it keeps that height and rewraps with the window.
- The list shows 15 rows and scrolls. All 23 rows open it upwards, off the top of a 1080p screen.
- Full list and descriptions in `docs/presets.md`.

### 4. Extras
- The checkbox defaults **off**.
- "Silence:" dropdown (Session 5, replaced the "Remove silent parts" checkbox): Keep it (default) / Trim the start and end / Remove all silent parts. The tooltip says what each does, including that "all" also shortens long pauses in the middle. It made the window need 958 px of height (was 943): 960 leaves 2 px, and at the 920 minimum the log keeps about 2 lines.
- "Only fix the files that are unusually quiet" is disabled until a scan has run and found some; tooltip explains why when greyed. While greyed it shows unticked, but the choice saved in `config.json` is kept and comes back once a scan finds quiet files.
- **The scan runs on its own** as soon as the From folder is picked (also when To or "Include subfolders" changes, and at startup for the remembered folder), so the scan summary and this checkbox are ready before Start. Stop also stops the scan. Pressing Start during the scan starts processing right after it. Start reuses the scan unless the folder's file list changed since, in which case it scans again.
- Output format radio, default "Same as original".

### Buttons
- Start: large, `bootstyle="success"`, disabled while running.
- Stop: large, `bootstyle="danger"`, disabled unless running. Must actually interrupt — set a flag the worker thread checks between files, and terminate any in-flight FFmpeg subprocess.

### Progress area
- Scan summary line: `Found 47 audio files · 6 look unusually quiet`. Populates after the scan pass, before processing.
- Determinate progress bar + `N / total` counter.
- Current-file label.
- Log: `tk.Text`, ~8 lines, Consolas, vertical scrollbar, autoscroll to bottom. Set `bg`/`fg`/`insertbackground` directly (tk widget, doesn't inherit ttk styles).
- Every log line is also appended to `log.txt` next to the exe (`utils/logfile.py`), since the box is small. Its first line tells the user it can be deleted when it grows too big (a fresh one is made); each session starts with a `=== YYYY-MM-DD HH:MM ===` header, written with the session's first line. Write errors are swallowed like `config.json`'s. Gitignored. Added in Session 5 at the author's request.

### Footer
- "Open output folder" button, disabled until an output folder exists.
- "Made by Reactorcore" + clickable https://reactorcoregames.github.io/ (RC standard branding).

---

## Behaviour

- **Threading:** worker thread for scan and processing, `queue.Queue` for updates, `root.after()` polling to update the GUI. Never block the mainloop.
- **FFmpeg check on startup:** `shutil.which("ffmpeg")`. If missing, show the RC standard message and disable Start: `"FFMPEG not found in PATH. Please install FFMPEG.\n\nYou can use: https://reactorcore.itch.io/ffmpeg-to-path-installer"`
- **Config persistence:** `config.json` per RC standard — remember last folders, category, effect, extras, output format. Save on every change.
- **Icon:** `_apply_icon()` on the main window and every Toplevel.
- **Errors are per-file, not fatal.** A file that fails to process logs the error and the batch continues. Summary at the end: `44 succeeded, 3 failed`. The exception is when the folders are the cause (From folder gone, To folder unwritable, disk full): the batch stops and a warning dialog says why (`docs/processing_spec.md` → Error handling).
- **Start checks before it creates anything:** no audio files → an info dialog (with the "Include subfolders" hint when there are folders inside), and the To folder isn't created; an unwritable To folder → an error dialog. Without FFmpeg the summary line keeps saying so, also after a folder is picked.

---

## Wording rules

- No jargon in primary labels. Technical terms appear only as secondary anchors.
- Buttons say what happens: "Start", not "Execute". "Open output folder", not "Open".
- Errors suggest a fix, not just state a problem.
- Tooltips on every control that isn't self-evident.
