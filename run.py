import queue
import threading
import traceback
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from config_finder.pipeline import Pipeline, PipelineStats

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Config Finder")
        self.root.geometry("900x620")
        self.root.minsize(820, 560)
        self.events = queue.Queue()
        self.pipeline = None
        self.running = False
        self._build()
        self._poll_events()

    def _build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer, text="Config Finder", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text="Public configuration discovery, collection, validation and export",
        ).pack(anchor="w", pady=(2, 14))

        stats = ttk.Frame(outer)
        stats.pack(fill="x", pady=(0, 12))
        self.status_var = tk.StringVar(value="Ready")
        self.source_var = tk.StringVar(value="0")
        self.config_var = tk.StringVar(value="0")
        self.reachable_var = tk.StringVar(value="0")
        self.tested_var = tk.StringVar(value="0")
        for i, item in enumerate(
            (
                ("Status", self.status_var),
                ("Sources", self.source_var),
                ("Unique configs", self.config_var),
                ("Reachable", self.reachable_var),
                ("Tested", self.tested_var),
            )
        ):
            self._stat(stats, item[0], item[1], i)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(0, 12))
        self.start_button = ttk.Button(
            buttons, text="Start Full Scan", command=self.start
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            buttons, text="Stop", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(
            buttons, text="Open Output Folder", command=self.open_output
        ).pack(side="left")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 12))

        frame = ttk.LabelFrame(outer, text="Activity", padding=8)
        frame.pack(fill="both", expand=True)
        self.log = tk.Text(
            frame, wrap="word", state="disabled", font=("Consolas", 9)
        )
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)

        ttk.Label(
            outer,
            text="Public sources only. Testing is limited to advertised endpoints.",
        ).pack(anchor="w", pady=(8, 0))

    @staticmethod
    def _stat(parent, title, variable, column):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, sticky="w", padx=(0, 28))
        ttk.Label(frame, text=title).pack(anchor="w")
        ttk.Label(
            frame, textvariable=variable, font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

    def start(self):
        if self.running:
            return
        self.running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Starting...")
        self.progress.start(10)
        self._clear_log()
        self._emit("progress", "Starting full public-source scan...")
        self.pipeline = Pipeline(callback=self._pipeline_callback)
        threading.Thread(target=self._worker, daemon=True).start()

    def stop(self):
        if self.pipeline:
            self.pipeline.stop()
            self.status_var.set("Stopping...")
            self.stop_button.configure(state="disabled")
            self._append_log("Stop requested; finishing the current bounded batch...")

    def _worker(self):
        try:
            stats = self.pipeline.run()
            self._emit("finished", stats)
        except Exception as exc:
            self._emit(
                "error",
                "".join(traceback.format_exception_only(type(exc), exc)).strip(),
            )

    def _pipeline_callback(self, stats: PipelineStats, message: str):
        self._emit(
            "stats",
            (
                stats,
                message,
            ),
        )

    def _emit(self, kind, payload):
        self.events.put((kind, payload))

    def _poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self._append_log(payload)
                elif kind == "stats":
                    stats, message = payload
                    self._update_stats(stats)
                    if message:
                        self._append_log(message)
                elif kind == "finished":
                    self._update_stats(payload)
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.progress.stop()
                    if payload.stage == "completed":
                        self.status_var.set("Completed")
                        self._append_log("Scan completed successfully.")
                        messagebox.showinfo(
                            "Config Finder",
                            f"Completed: {payload.unique_configs} unique configs, "
                            f"{payload.reachable} reachable.",
                        )
                    else:
                        self.status_var.set("Stopped")
                        self._append_log("Scan stopped.")
                elif kind == "error":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.progress.stop()
                    self.status_var.set("Error")
                    self._append_log("ERROR: " + payload)
                    messagebox.showerror("Config Finder", payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _update_stats(self, stats: PipelineStats):
        self.status_var.set(stats.stage.replace("_", " ").title())
        self.source_var.set(str(stats.discovered_sources))
        self.config_var.set(str(stats.unique_configs))
        self.reachable_var.set(str(stats.reachable))
        self.tested_var.set(str(stats.tested))

    def _append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def open_output(self):
        DATA.mkdir(parents=True, exist_ok=True)
        webbrowser.open(DATA.resolve().as_uri())


def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
