"""Sections 1-4: folders, kind of audio, effect, extras. Every control saves to config.json
on change. Mixed into App; uses its set_config(), attach_context_menu() and the scan hooks
in gui/jobs.py (request_scan(), on_scan_settings_changed())."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import ttkbootstrap as ttk

from core.effects import NO_EFFECT, describe, dropdown_rows
from core.measure import QUIET_MARGIN_DB, QUIET_MIN_FILES
from core.normalize import LOUDNORM_TARGETS, TARGET_RMS_PEAK_DB
from gui.theme import FONT_BODY, PALETTE

# (config value, name, plain description, tooltip)
CATEGORIES = [
    ("sfx", "Sound Effects", "game sounds, foley, blips",
     "Short sounds: hits, clicks, footsteps, UI blips, explosions. Matches the loudest moment of "
     "each sound, so a quick blip ends up as punchy as a long explosion. Works for files of any "
     "length."),
    ("voice", "Voice & Speech", "narration, podcasts, ASMR",
     "Spoken word. Matches the overall loudness the way podcasts and audiobooks are levelled, so "
     "every voice clip sits at the same comfortable listening level."),
    ("music", "Music Tracks", "songs, loops, stingers",
     "Songs and musical loops. Matches overall loudness to the level streaming services use, so "
     "no track jumps out of a playlist."),
    ("ambient", "Ambient Loops", "rain, forest, machinery",
     "Background beds that play under everything else. Matched quieter than music or voice, so "
     "they fill the space without competing with the foreground."),
]

# config value → dropdown text
SILENCE_MODES = {"keep": "Keep it", "ends": "Trim the start and end", "all": "Remove all silent parts"}
FORMATS = [("same", "Same as original"), ("wav", "WAV"), ("mp3", "MP3"), ("ogg", "OGG")]
FORMAT_TIPS = {
    "same": "Each file keeps its own format: WAV stays WAV, MP3 stays MP3",
    "wav": "Uncompressed. Best quality, biggest files",
    "mp3": "Small files that play everywhere, at high quality (about 190 kbps)",
    "ogg": "Small files, popular in game engines (Godot, Unity)",
}

DESC_LINES = 3   # fixed, so nothing jumps; the longest description is 3 lines at the 860 minimum width


def category_anchor(cat: str) -> str:
    """The technical line under each category: peak/loudness method and its target."""
    target = LOUDNORM_TARGETS[cat]
    if target is None:
        return f"peak-normalize style, target {TARGET_RMS_PEAK_DB:g} dBFS"
    return f"loudness-normalize, target {target[0]:g} LUFS"


class SectionsMixin:
    def _build_sections(self, parent):
        """Rows 0-3 of the body grid."""
        self.lockable = []   # controls greyed out while a batch runs
        self._build_folders(parent).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._build_category(parent).grid(row=1, column=0, sticky="ew", pady=3)
        self._build_effect(parent).grid(row=2, column=0, sticky="ew", pady=3)
        self._build_extras(parent).grid(row=3, column=0, sticky="ew", pady=3)

    def _var(self, cls, key):
        """A Tk variable bound to a config key. Kept on self.vars: Tk variables die with
        their last Python reference and the widget then shows blank."""
        v = cls(value=self.config[key])
        v.trace_add("write", lambda *_: self._sync_vars or self.set_config(key, v.get()))
        self.vars[key] = v
        return v

    # ── 1. Folders ──────────────────────────────────────────────────────────
    def _build_folders(self, parent):
        f = ttk.LabelFrame(parent, text="1. Choose your folders", padding=(10, 4, 10, 8))
        f.columnconfigure(1, weight=1)
        rows = [("From:", "input_dir", self._browse_input,
                 "The folder with the audio files you want to make consistent. "
                 "The originals are never changed."),
                ("To:", "output_dir", self._browse_output,
                 "Where the finished files go. Filled in for you as a \"unified\" folder "
                 "inside the From folder; pick another one if you like.")]
        for r, (label, key, command, tip) in enumerate(rows):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="e", padx=(0, 6), pady=2)
            entry = ttk.Entry(f, textvariable=self._var(tk.StringVar, key), state="readonly",
                              font=FONT_BODY)
            entry.grid(row=r, column=1, sticky="ew", pady=2)
            # Long paths: show the end, where the folder's own name is
            self.vars[key].trace_add("write", lambda *_, e=entry: e.after_idle(e.xview_moveto, 1))
            entry.after_idle(entry.xview_moveto, 1)
            self.attach_context_menu(entry)
            ttk.ToolTip(entry, text=tip)
            btn = ttk.Button(f, text="Browse", width=10, command=command)
            btn.grid(row=r, column=2, padx=(6, 0), pady=2)
            ttk.ToolTip(btn, text=f"Pick the {'input' if r == 0 else 'output'} folder")
            self.lockable.append(btn)

        sub = ttk.Checkbutton(f, text="Include subfolders (output keeps the same tree)",
                              variable=self._var(tk.BooleanVar, "include_subfolders"),
                              command=self.on_scan_settings_changed)
        sub.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.ToolTip(sub, text="Also processes the audio in every folder inside the From folder. "
                              "The output gets the same folders, so metal\\clang.wav ends up "
                              "in To\\metal\\.")
        self.lockable.append(sub)
        return f

    def _browse_input(self):
        start = self.vars["input_dir"].get()
        path = filedialog.askdirectory(parent=self.root, title="Choose the folder with your audio",
                                       initialdir=start if start and Path(start).is_dir() else None)
        if not path:
            return
        path = str(Path(path))
        self.vars["input_dir"].set(path)
        self.vars["output_dir"].set(str(Path(path) / "unified"))
        self.on_scan_settings_changed()

    def _browse_output(self):
        start = self.vars["output_dir"].get() or self.vars["input_dir"].get()
        path = filedialog.askdirectory(parent=self.root, title="Choose where the finished files go",
                                       initialdir=start if start and Path(start).is_dir() else None)
        if path:
            self.vars["output_dir"].set(str(Path(path)))
            self.on_scan_settings_changed()

    # ── 2. Kind of audio ────────────────────────────────────────────────────
    def _build_category(self, parent):
        f = ttk.LabelFrame(parent, text="2. What kind of audio is this?", padding=(10, 2, 10, 6))
        f.columnconfigure((0, 1), weight=1)
        var = self._var(tk.StringVar, "category")
        if var.get() not in LOUDNORM_TARGETS:
            var.set("sfx")
        for i, (value, name, plain, tip) in enumerate(CATEGORIES):
            cell = ttk.Frame(f, style="Surface.TFrame")
            cell.grid(row=i // 2, column=i % 2, sticky="w", pady=1)
            rb = ttk.Radiobutton(cell, text=name, value=value, variable=var)
            rb.grid(row=0, column=0, sticky="w")
            ttk.Label(cell, text=plain).grid(row=0, column=1, sticky="w", padx=(8, 0))
            ttk.Label(cell, text=category_anchor(value), style="secondary.TLabel").grid(
                row=1, column=0, columnspan=2, sticky="w", padx=(26, 0))
            for w in cell.winfo_children():
                ttk.ToolTip(w, text=tip)
            self.lockable.append(rb)
        return f

    # ── 3. Effect ───────────────────────────────────────────────────────────
    def _build_effect(self, parent):
        f = ttk.LabelFrame(parent, text="3. Change the sound? (optional)", padding=(10, 4, 10, 8))
        f.columnconfigure(0, weight=1)
        self.effect_rows = dropdown_rows()
        tags = [tag for _, tag in self.effect_rows]
        if self.config["effect"] not in tags:
            self.set_config("effect", NO_EFFECT)

        # All 23 rows would open the list upwards and off the top of a 1080p screen
        self.effect_box = ttk.Combobox(f, state="readonly", font=FONT_BODY, height=15,
                                       values=[text for text, _ in self.effect_rows])
        self.effect_box.current(tags.index(self.config["effect"]))
        self.effect_box.grid(row=0, column=0, sticky="ew")
        self.effect_box.bind("<<ComboboxSelected>>", self._on_effect_selected)
        ttk.ToolTip(self.effect_box, text="Optional. Gives every file the same character before "
                                          "the loudness is matched. The ─── rows are group titles, "
                                          "not choices.")
        self.lockable.append(self.effect_box)

        # A disabled Text rather than a Label: fixed line height that rewraps with the window
        p = PALETTE
        self.effect_desc = tk.Text(f, height=DESC_LINES, width=1, wrap="word", font=FONT_BODY,
                                   background=p["bg_input"], foreground=p["text_primary"],
                                   relief="flat", borderwidth=0, highlightthickness=0,
                                   padx=10, pady=6, cursor="arrow", takefocus=0)
        self.effect_desc.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._show_description(self.config["effect"])
        return f

    def _on_effect_selected(self, _event=None):
        tag = self.effect_rows[self.effect_box.current()][1]
        if tag is None:   # a group title: snap back to the previous choice
            tags = [t for _, t in self.effect_rows]
            self.effect_box.current(tags.index(self.config["effect"]))
        else:
            self.set_config("effect", tag)
            self._show_description(tag)
        self.effect_box.selection_clear()

    def _show_description(self, tag):
        self.effect_desc.configure(state="normal")
        self.effect_desc.delete("1.0", "end")
        self.effect_desc.insert("1.0", describe(tag))
        self.effect_desc.configure(state="disabled")

    # ── 4. Extras ───────────────────────────────────────────────────────────
    def _build_extras(self, parent):
        f = ttk.LabelFrame(parent, text="4. Extras (optional)", padding=(10, 4, 10, 8))
        silence_row = ttk.Frame(f, style="Surface.TFrame")
        silence_row.grid(row=0, column=0, sticky="w")
        ttk.Label(silence_row, text="Silence:").pack(side="left", padx=(0, 8))
        var = self._var(tk.StringVar, "silence")
        if var.get() not in SILENCE_MODES:
            var.set("keep")
        modes = list(SILENCE_MODES)
        self.silence_box = ttk.Combobox(silence_row, state="readonly", font=FONT_BODY, width=24,
                                        values=list(SILENCE_MODES.values()))
        self.silence_box.current(modes.index(var.get()))
        self.silence_box.pack(side="left")
        self.silence_box.bind("<<ComboboxSelected>>", lambda _e: (
            var.set(modes[self.silence_box.current()]), self.silence_box.selection_clear()))
        ttk.ToolTip(self.silence_box, text="Trim the start and end: cuts the silence before the "
                                           "sound begins and after it ends. Remove all silent "
                                           "parts: also shortens long pauses in the middle; "
                                           "pauses of half a second or less are kept.")
        self.lockable.append(self.silence_box)

        self.quiet_check = ttk.Checkbutton(f, text="Only fix the files that are unusually quiet",
                                           variable=self._var(tk.BooleanVar, "quiet_only"),
                                           state="disabled")
        self.quiet_check.grid(row=0, column=1, sticky="w", padx=(20, 0))
        self.quiet_tip = ttk.ToolTip(self.quiet_check, text="")
        self.update_quiet_check(None)

        fmt_row = ttk.Frame(f, style="Surface.TFrame")
        fmt_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(fmt_row, text="Save as:").pack(side="left", padx=(0, 8))
        var = self._var(tk.StringVar, "output_format")
        if var.get() not in FORMAT_TIPS:
            var.set("same")
        for value, text in FORMATS:
            rb = ttk.Radiobutton(fmt_row, text=text, value=value, variable=var)
            rb.pack(side="left", padx=(0, 12))
            ttk.ToolTip(rb, text=FORMAT_TIPS[value])
            self.lockable.append(rb)
        return f

    def update_quiet_check(self, report, scanning=False):
        """Enable "only quiet files" when a finished scan of the current folder found some.
        Greyed, the tooltip says why."""
        about = (f"Leaves every other file alone. A file counts as unusually quiet when its "
                 f"loudest moment is more than {QUIET_MARGIN_DB:g} dB below the folder's typical "
                 f"level.")
        if report is not None and report.quiet:
            n = len(report.quiet)
            why = None
            about = f"{n} file{'s look' if n != 1 else ' looks'} unusually quiet. " + about
        elif scanning:
            why = "Checking the folder, one moment."
        elif report is None:
            why = "Pick a From folder first: the program checks it for unusually quiet files."
        elif report.quiet is None:
            why = (f"Needs at least {QUIET_MIN_FILES} audio files to tell what's unusually quiet "
                   f"for this folder.")
        else:
            why = "No file in this folder is unusually quiet, so there's nothing to pick out."
        # Shown unticked while greyed, without overwriting the choice saved in config.json
        self._sync_vars = True
        self.vars["quiet_only"].set(False if why else self.config["quiet_only"])
        self._sync_vars = False
        if why:
            self.quiet_check.configure(state="disabled")
            self.quiet_tip.configure(text=f"Not available: {why}\n\n{about}")
        else:
            self.quiet_check.configure(state="disabled" if self.running_batch else "normal")
            self.quiet_tip.configure(text=about)
