"""Main window: header, body, footer, and the helpers every panel shares."""

import tkinter as tk
import webbrowser
from tkinter import messagebox

import ttkbootstrap as ttk

from gui.jobs import JobsMixin
from gui.sections import SectionsMixin
from gui.theme import PALETTE, THEME_NAME, apply_theme, register_theme
from utils.config import load_config, save_config
from utils.ffmpeg import FFMPEG_MISSING_MSG, INSTALLER_URL, ffmpeg_available
from utils.paths import resource_path

HOMEPAGE_URL = "https://reactorcoregames.github.io/"


class App(SectionsMixin, JobsMixin):
    def __init__(self):
        register_theme()                              # before Window()
        self.root = ttk.Window(themename=THEME_NAME)
        self.root.title("Audio Folder Unifier")
        # 960 tall fits a 1080p screen at 125% scaling only if the window starts near the top
        height = min(960, self.root.winfo_screenheight() - 110)
        x = max(0, (self.root.winfo_screenwidth() - 900) // 2)
        self.root.geometry(f"900x{height}+{x}+10")
        self.root.minsize(860, 920)

        apply_theme(ttk.Style(), root=self.root)      # before building widgets
        self._apply_icon(self.root)

        self.config = load_config()
        save_config(self.config)                      # first run: create it with defaults
        self.ffmpeg_ok = ffmpeg_available()
        self.vars = {}            # Tk variables by config key (see SectionsMixin._var)
        self._sync_vars = False   # True while a variable is set without saving it
        self._init_jobs()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._refresh_open_output()
        if not self.ffmpeg_ok:
            self.root.after(200, self._warn_ffmpeg_missing)
        else:
            self.request_scan()   # the folder from last time, so the quiet check is ready

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        self._build_header().grid(row=0, column=0, sticky="ew")
        ttk.Separator(self.root, style="Neon.TSeparator").grid(row=1, column=0, sticky="ew")

        body = ttk.Frame(self.root, padding=(14, 8, 14, 8))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(6, weight=1)   # the log takes up (and gives back) the spare height
        self._build_sections(body)
        self._build_run_area(body)

        ttk.Separator(self.root).grid(row=3, column=0, sticky="ew")
        self._build_footer().grid(row=4, column=0, sticky="ew")

    def _build_header(self):
        hf = ttk.Frame(self.root, padding=(16, 6, 16, 6))
        ttk.Label(hf, text="Audio Folder Unifier", style="Title.TLabel").pack(side="left")
        ttk.Label(hf, text="Make a whole folder of audio sound consistent.",
                  style="Subtitle.TLabel").pack(side="left", padx=(14, 0), pady=(6, 0))
        return hf

    def _build_footer(self):
        ff = ttk.Frame(self.root, padding=(14, 5))
        self.open_output_btn = ttk.Button(ff, text="Open output folder", width=18, state="disabled",
                                          command=self.open_output)
        self.open_output_btn.pack(side="left")
        ttk.ToolTip(self.open_output_btn, text="Opens the folder your finished files were saved to")

        link = ttk.Label(ff, text="reactorcoregames.github.io", style="Link.TLabel", cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open(HOMEPAGE_URL))
        ttk.Label(ff, text="Made by Reactorcore", style="Footer.TLabel").pack(side="right", padx=(0, 4))
        return ff

    # ── Shared helpers ──────────────────────────────────────────────────────
    def _apply_icon(self, window):
        """Main window and every Toplevel; Toplevels don't inherit it."""
        try:
            window.iconbitmap(str(resource_path("assets/icon.ico")))
        except Exception:
            pass

    def attach_context_menu(self, entry_widget):
        p = PALETTE
        menu = tk.Menu(entry_widget, tearoff=0, background=p["bg_input"], foreground=p["text_primary"],
                       activebackground=p["accent_neon"], activeforeground=p["ink"])
        menu.add_command(label="Cut",        command=lambda: entry_widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",       command=lambda: entry_widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste",      command=lambda: entry_widget.event_generate("<<Paste>>"))
        menu.add_command(label="Select All", command=lambda: entry_widget.event_generate("<<SelectAll>>"))

        def _show(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry_widget.bind("<Button-3>", _show)

    def set_config(self, key, value):
        """Every control saves on change (RC standard: save on every change, not on exit)."""
        self.config[key] = value
        save_config(self.config)

    def _warn_ffmpeg_missing(self):
        if messagebox.askyesno("FFMPEG missing",
                               FFMPEG_MISSING_MSG + "\n\nOpen that page now?",
                               icon="warning", parent=self.root):
            webbrowser.open(INSTALLER_URL)

    def run(self):
        self.root.mainloop()
