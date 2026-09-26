import json
import queue
import threading
import traceback
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from config_finder.cli import command_crawl, command_discover, command_export, command_test

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Config Finder")
        self.root.geometry("820x560")
        self.root.minsize(760, 500)
        self.events = queue.Queue()
        self.running = False
        self._build()
        self._poll_events()

    def _build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Config Finder", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Public configuration discovery, collection and endpoint testing").pack(anchor="w", pady=(2, 14))
        stats = ttk.Frame(outer)
        stats.pack(fill="x", pady=(0, 12))
        self.status_var = tk.StringVar(value="Ready")
        self.total_var = tk.StringVar(value="—")
        self.reachable_var = tk.StringVar(value="—")
        self._stat(stats, "Status", self.status_var, 0)
        self._stat(stats, "Configs", self.total_var, 1)
        self._stat(stats, "Reachable", self.reachable_var, 2)
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(0, 12))
        self.start_button = ttk.Button(buttons, text="Start Full Scan", command=self.start)
        self.start_button.pack(side="left")
        ttk.Button(buttons, text="Open Output Folder", command=self.open_output).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 12))
        frame = ttk.LabelFrame(outer, text="Activity", padding=8)
        frame.pack(fill="both", expand=True)
        self.log = tk.Text(frame, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)
        ttk.Label(outer, text="Only public sources and advertised endpoints are processed.").pack(anchor="w", pady=(8, 0))

    @staticmethod
    def _stat(parent, title, variable, column):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, sticky="w", padx=(0, 34))
        ttk.Label(frame, text=title).pack(anchor="w")
        ttk.Label(frame, textvariable=variable, font=("Segoe UI", 12, "bold")).pack(anchor="w")

    def start(self):
        if self.running:
            return
        self.running = True
        self.start_button.configure(state="disabled")
        self.status_var.set("Running...")
        self.progress.start(10)
        self._clear_log()
        self._emit("log", "Starting full public-source scan...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _emit(self, kind, message):
        self.events.put((kind, message))

    def _worker(self):
        try:
            self._emit("log", "1/4 Discovering public source pages...")
            command_discover()
            self._emit("log", "2/4 Crawling sources and extracting configurations...")
            command_crawl()
            self._emit("log", "3/4 Testing advertised endpoints...")
            command_test(None)
            self._emit("log", "4/4 Exporting final datasets...")
            command_export()
            self._emit("done", "Scan completed successfully.")
        except Exception as exc:
            self._emit("error", "".join(traceback.format_exception_only(type(exc), exc)).strip())

    def _poll_events(self):
        try:
            while True:
                kind, message = self.events.get_nowait()
                if kind == "log":
                    self._append_log(message)
                elif kind == "done":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.progress.stop()
                    self.status_var.set("Completed")
                    self._refresh_stats()
                    self._append_log(message)
                    messagebox.showinfo("Config Finder", message)
                elif kind == "error":
                    self.running = False
                    self.start_button.configure(state="normal")
                    self.progress.stop()
                    self.status_var.set("Error")
                    self._append_log("ERROR: " + message)
                    messagebox.showerror("Config Finder", message)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _refresh_stats(self):
        summary = DATA / "summary.json"
        if summary.exists():
            try:
                data = json.loads(summary.read_text(encoding="utf-8"))
                self.total_var.set(str(data.get("total", 0)))
                self.reachable_var.set(str(data.get("reachable", 0)))
            except Exception:
                pass

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
