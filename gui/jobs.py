"""Start / Stop, the progress area and the worker thread. Mixed into App.

One worker at a time, two kinds of job:
- the check: core.pipeline.scan(), started on its own whenever the From folder (or anything
  else that changes which files are found) changes, so the scan summary and the "only quiet
  files" box are ready before Start is pressed;
- the batch: run_batch() on the check's report (scanning first if there is none, or the
  folder's file list changed since).
The worker's callbacks only put messages on self.queue; _poll() applies them on the Tk
thread. Stop is runner.cancel(), which also kills the FFmpeg call in flight.
"""

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import ttkbootstrap as ttk

from core.formats import AUDIO_EXTS
from core.pipeline import Settings, check_output_dir, run_batch, scan
from core.scan import scan_folder
from gui.theme import FONT_MONO, PALETTE
from utils.ffmpeg import Cancelled, FFmpegRunner
from utils.logfile import LogFile

POLL_MS = 100
NO_FFMPEG_NOTE = "FFmpeg not found: install it to use the program"


class JobsMixin:
    def _init_jobs(self):
        self.queue = queue.Queue()
        self.log_file = LogFile()   # log.txt: the log box is small, this keeps everything
        self.runner = FFmpegRunner()
        self.worker = None
        self.job = None            # "scan" / "batch" while a worker runs
        self.pending = None        # "scan" / "start": what to do once the current worker ends
        self.running_batch = False
        self.report = None         # last finished scan, valid for self.report_key
        self.report_key = None
        self.gen = 0               # stamps messages, so a finished job's stragglers are ignored

    # ── Layout: rows 4-6 of the body grid ───────────────────────────────────
    def _build_run_area(self, parent):
        bf = ttk.Frame(parent)
        bf.grid(row=4, column=0, pady=(6, 4))
        self.start_btn = ttk.Button(bf, text="Start", bootstyle="success", width=16, command=self.start)
        self.start_btn.pack(side="left", padx=12)
        self.start_tip = ttk.ToolTip(self.start_btn, text="Makes every file consistent and saves "
                                     "the results in the To folder. Your originals are never changed.")
        self.stop_btn = ttk.Button(bf, text="Stop", bootstyle="danger", width=16, state="disabled",
                                   command=self.stop)
        self.stop_btn.pack(side="left", padx=12)
        ttk.ToolTip(self.stop_btn, text="Stops right away. Files already finished are kept; the "
                                        "one being worked on is not saved.")

        pf = ttk.Frame(parent)
        pf.grid(row=5, column=0, sticky="ew")
        pf.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(pf, maximum=1, value=0, style="Neon.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.counter = ttk.Label(pf, text="0 / 0", style="Base.TLabel", width=9, anchor="e")
        self.counter.grid(row=0, column=1, padx=(8, 0))
        self.current_label = ttk.Label(pf, text="", style="BaseDim.TLabel")
        self.current_label.grid(row=1, column=0, sticky="w")
        self.summary_label = ttk.Label(pf, text="", style="BaseDim.TLabel")
        self.summary_label.grid(row=1, column=0, columnspan=2, sticky="e")

        lf = ttk.Frame(parent)
        lf.grid(row=6, column=0, sticky="nsew", pady=(4, 0))
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        p = PALETTE
        self.log_text = tk.Text(lf, height=4, width=1, wrap="word", background=p["bg_input"],
                                foreground=p["accent_soft"], insertbackground=p["text_primary"],
                                selectbackground=p["accent_neon"], selectforeground=p["ink"],
                                font=FONT_MONO, relief="flat", borderwidth=0, padx=8, pady=6,
                                state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.log_text.yview, bootstyle="secondary-round")
        sb.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=sb.set)

        if not self.ffmpeg_ok:
            self.start_btn.configure(state="disabled")
            self.start_tip.configure(text="FFmpeg isn't installed, so nothing can be processed. "
                                          "Install it, then restart the program.")
            self.summary_label.configure(text=NO_FFMPEG_NOTE)
        self.root.after(POLL_MS, self._poll)

    def log(self, text):
        self.log_file.write(text)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    # ── Settings ────────────────────────────────────────────────────────────
    def _settings(self) -> Settings:
        c = self.config
        out = c["output_dir"] or str(Path(c["input_dir"]) / "unified")
        return Settings(Path(c["input_dir"]), Path(out), c["include_subfolders"],
                        c["category"], c["effect"], c["silence"],
                        self.vars["quiet_only"].get(), c["output_format"])

    def _scan_key(self):
        """What decides which files a scan finds; a report is only reused for the same key."""
        c = self.config
        return (os.path.normcase(c["input_dir"]), os.path.normcase(c["output_dir"]),
                c["include_subfolders"])

    # ── The check ───────────────────────────────────────────────────────────
    def on_scan_settings_changed(self):
        """From, To or "Include subfolders" changed: the last scan no longer applies."""
        self.report = self.report_key = None
        self.summary_label.configure(text="" if self.ffmpeg_ok else NO_FFMPEG_NOTE)
        self.update_quiet_check(None)
        self._refresh_open_output()
        self.request_scan()

    def request_scan(self):
        if not self.ffmpeg_ok or not self.config["input_dir"]:
            return
        if self.worker is not None:
            if self.job == "scan":     # restart it for the new folder once it has stopped
                self.pending = "scan"
                self.runner.cancel()
            return
        self._start_scan()

    def _start_scan(self):
        folder = Path(self.config["input_dir"])
        if not folder.is_dir():
            self.summary_label.configure(text="The From folder doesn't exist any more")
            return
        self._launch("scan", self._scan_worker, self._settings(), self._scan_key())
        self.summary_label.configure(text="Checking the folder…")
        self.update_quiet_check(None, scanning=True)
        self.log(f"Checking {folder} …")

    def _scan_worker(self, gen, settings, key):
        try:
            report = scan(settings, self.runner, self._progress_cb(gen, "Checking"))
            self.queue.put(("scanned", gen, key, report))
            self.queue.put(("end", gen, None))
        except Cancelled:
            self.queue.put(("end", gen, "Check stopped. Press Start to check and process the folder."))
        except Exception as e:   # the folder vanished mid-scan, permissions...
            self.queue.put(("end", gen, f"Couldn't check the folder: {e}"))

    # ── Start / Stop ────────────────────────────────────────────────────────
    def start(self):
        c = self.config
        if not c["input_dir"]:
            messagebox.showinfo("No folder chosen", "Pick the folder with your audio first: "
                                "the Browse button next to \"From\".", parent=self.root)
            return
        if not Path(c["input_dir"]).is_dir():
            gone = c["input_dir"]
            self.vars["input_dir"].set("")
            if Path(c["output_dir"]).is_relative_to(gone):
                self.vars["output_dir"].set("")
            self.on_scan_settings_changed()
            messagebox.showwarning("Folder not found", f"This folder doesn't exist any more:\n{gone}"
                                   "\n\nIt may have been moved, renamed or deleted. Pick it again "
                                   "with the Browse button next to \"From\".", parent=self.root)
            return
        if not c["output_dir"]:
            self.vars["output_dir"].set(str(Path(c["input_dir"]) / "unified"))
        if self._warn_no_files():
            return
        problem = check_output_dir(Path(c["output_dir"]))
        if problem:
            messagebox.showerror("Can't save there", problem + "\n\nPick a different folder with "
                                 "the Browse button next to \"To\".", parent=self.root)
            return
        self._refresh_open_output()

        if self.worker is not None:   # the check is still running: start when it's done
            self.pending = "start"
            self.start_btn.configure(state="disabled")
            self.current_label.configure(text="Starting as soon as the folder check is done…")
            return
        self._start_batch()

    def _warn_no_files(self) -> bool:
        """True (after saying why) if the From folder has nothing to process. Checked before
        the To folder is created, so an empty folder doesn't leave an empty "unified" behind."""
        s = self._settings()
        found = scan_folder(s.input_dir, s.output_dir, s.include_subfolders)
        if found.files:
            return False
        where = "this folder or the folders inside it" if s.include_subfolders else "this folder"
        text = f"There are no audio files in {where}:\n{s.input_dir}"
        if not s.include_subfolders and any(p.is_dir() for p in s.input_dir.iterdir()):
            text += "\n\nIf your files are in folders inside it, tick \"Include subfolders\"."
        text += "\n\nThe program works with " + ", ".join(
            sorted(e[1:].upper() for e in AUDIO_EXTS if e != ".aif")) + " files."
        messagebox.showinfo("No audio files", text, parent=self.root)
        return True

    def _start_batch(self):
        settings, key = self._settings(), self._scan_key()
        report = self.report if self.report_key == key else None
        self.running_batch = True
        self._lock_controls(True)
        self._launch("batch", self._batch_worker, settings, key, report)
        self.log("")
        self.log(f"Starting: {settings.input_dir} → {settings.output_dir}")
        if settings.include_subfolders and settings.output_dir.is_relative_to(settings.input_dir):
            self.log("The To folder is inside the From folder. It's skipped when looking for "
                     "audio, so earlier results are never processed again.")

    def _batch_worker(self, gen, settings, key, report):
        log = lambda text: self.queue.put(("log", gen, text))
        try:
            if report is not None:
                found = scan_folder(settings.input_dir, settings.output_dir, settings.include_subfolders)
                if found.files != report.files:
                    log("The folder changed since it was checked, checking it again …")
                    report = None
            if report is None:
                report = scan(settings, self.runner, self._progress_cb(gen, "Checking"))
                self.queue.put(("scanned", gen, key, report))
            if not report.files:
                self.queue.put(("end", gen, "Nothing to do: no audio files found in the From folder."))
                return
            summary = run_batch(settings, report, self.runner, log, self._progress_cb(gen, "Now processing"))
            if summary.problem:   # before "end": a scan pending after it would bump the job number
                self.queue.put(("problem", gen, summary.problem))
            self.queue.put(("end", gen, f"Done: {summary}"))
        except Cancelled:
            self.queue.put(("end", gen, "Stopped."))
        except Exception as e:
            self.queue.put(("end", gen, f"Something went wrong, the batch stopped: {e}"))

    def stop(self):
        self.pending = None
        self.runner.cancel()
        self.stop_btn.configure(state="disabled")
        self.current_label.configure(text="Stopping…")

    # ── Worker plumbing ─────────────────────────────────────────────────────
    def _launch(self, job, target, *args):
        self.runner.reset()
        self.gen += 1
        self.job = job
        self.worker = threading.Thread(target=target, args=(self.gen, *args), daemon=True)
        self.stop_btn.configure(state="normal")
        if job == "batch":
            self.start_btn.configure(state="disabled")
        self.progress.configure(value=0, maximum=1)
        self.counter.configure(text="0 / 0")
        self.worker.start()

    def _progress_cb(self, gen, verb):
        return lambda done, total, name: self.queue.put(("progress", gen, verb, done, total, name))

    def _poll(self):
        try:
            while True:
                kind, gen, *rest = self.queue.get_nowait()
                if gen == self.gen:
                    getattr(self, f"_on_{kind}")(*rest)
        except queue.Empty:
            pass
        self.root.after(POLL_MS, self._poll)

    def _on_progress(self, verb, done, total, name):
        self.progress.configure(maximum=max(total, 1), value=done)
        self.counter.configure(text=f"{done} / {total}")
        self.current_label.configure(text=f"{verb}: {name}" if name else "")

    def _on_log(self, text):
        self.log(text)

    def _on_problem(self, text):
        """The batch stopped by itself: the folders, not one file, were the trouble."""
        messagebox.showwarning("The batch stopped", text, parent=self.root)

    def _on_scanned(self, key, report):
        self.report, self.report_key = report, key
        self.summary_label.configure(text=report.summary())
        self.update_quiet_check(report)
        self.log(report.summary())
        n = len(report.skipped_own)
        if n:
            self.log(f"Skipped {n} earlier result{'s' if n != 1 else ''} of this program "
                     f"(files ending in its own tags, next to their originals)")
        for path in report.unreadable:
            self.log(f"Can't read {path.name}, it will be listed as failed")

    def _on_end(self, message):
        job, self.worker, self.job = self.job, None, None
        if job == "batch":
            self.running_batch = False
            self._lock_controls(False)
            self._refresh_open_output()
        elif self.report is None:
            self.summary_label.configure(text="")
            self.update_quiet_check(None)
        if message and self.pending != "scan":
            self.current_label.configure(text=message)
            if job == "scan":
                self.log(message)
        self.stop_btn.configure(state="disabled")
        if self.ffmpeg_ok:
            self.start_btn.configure(state="normal")

        pending, self.pending = self.pending, None
        if pending == "scan":
            self._start_scan()
        elif pending == "start":
            self._start_batch()

    def _lock_controls(self, locked):
        for w in self.lockable:
            if isinstance(w, ttk.Combobox):
                w.configure(state="disabled" if locked else "readonly")
            else:
                w.configure(state="disabled" if locked else "normal")
        if locked:
            self.quiet_check.configure(state="disabled")
        else:
            self.update_quiet_check(self.report)

    # ── Output folder, closing ──────────────────────────────────────────────
    def _refresh_open_output(self):
        out = self.config["output_dir"]
        self.open_output_btn.configure(state="normal" if out and Path(out).is_dir() else "disabled")

    def open_output(self):
        out = self.config["output_dir"]
        if out and Path(out).is_dir():
            os.startfile(out)
        else:
            self._refresh_open_output()

    def on_close(self):
        """Kill any FFmpeg in flight and give the worker a moment to delete its temp files."""
        if self.worker is not None:
            self.runner.cancel()
            self.worker.join(timeout=5)
        self.root.destroy()
