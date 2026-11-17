import csv
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from src.benchmark.runner import run_benchmark
from src.gui.styles import COLORS
from src.timer.timer import format_elapsed

# Project root — folder containing main.py.
# report.py lives at  <root>/src/gui/report.py  -> two `..` = root.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

ALL_SIZES = [100, 1000, 10000, 30000]
ALL_ORDERS = ["Random", "Sorted", "Reverse-Sorted"]
ALL_ALGOS = ["Linear Search", "Binary Search", "Bubble Sort", "Merge Sort"]


class ReportWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("SONIQ — Benchmark Report")
        self.geometry("1180x780")
        self.minsize(1000, 640)
        self.configure(bg=COLORS["bg"])

        # State
        self.results = []
        self.running = False
        self.stop_flag = False
        self._ui_queue = queue.Queue()

        # Checkbox vars
        self.size_vars = {s: tk.BooleanVar(value=(s >= 1000)) for s in ALL_SIZES}
        self.order_vars = {o: tk.BooleanVar(value=True) for o in ALL_ORDERS}
        self.algo_vars = {a: tk.BooleanVar(value=True) for a in ALL_ALGOS}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_ui_queue()
        self.grab_set()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):
        # Config panel
        config = tk.Frame(self, bg=COLORS["panel"])
        config.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(
            config,
            text="BENCHMARK CONFIGURATION",
            bg=COLORS["panel"],
            fg=COLORS["accent_light"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))

        rows = tk.Frame(config, bg=COLORS["panel"])
        rows.pack(fill="x", padx=16, pady=(0, 12))

        self._check_row(
            rows, "Sizes", ALL_SIZES, self.size_vars, label_fn=lambda s: f"{s:,}"
        )
        self._check_row(rows, "Orders", ALL_ORDERS, self.order_vars)
        self._check_row(rows, "Algorithms", ALL_ALGOS, self.algo_vars)

        # Buttons
        btn_bar = tk.Frame(self, bg=COLORS["bg"])
        btn_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.run_btn = self._button(
            btn_bar, "▶  Run Benchmark", self._on_run, accent=True
        )
        self.run_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = self._button(btn_bar, "■  Stop", self._on_stop)
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.stop_btn.config(state="disabled")

        self.export_btn = self._button(btn_bar, "Export CSV", self._on_quick_export)
        self.export_btn.pack(side="left")
        self.export_btn.config(state="disabled")

        # Progress bar
        prog = tk.Frame(self, bg=COLORS["bg"])
        prog.pack(fill="x", padx=12, pady=(0, 6))

        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        self.progress_label = tk.Label(
            prog,
            text="Idle — choose a configuration and click Run.",
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.progress_label.pack(fill="x", pady=(4, 0))

        # Results tree
        wrap = tk.Frame(self, bg=COLORS["bg"])
        wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        cols = ("algorithm", "size", "order", "comparisons", "time", "status")
        headings = {
            "algorithm": "Algorithm",
            "size": "Rows",
            "order": "Input Order",
            "comparisons": "Comparisons",
            "time": "Time",
            "status": "Status",
        }
        widths = {
            "algorithm": 160,
            "size": 90,
            "order": 130,
            "comparisons": 130,
            "time": 110,
            "status": 120,
        }

        self.tree = ttk.Treeview(
            wrap, columns=cols, show="headings", style="App.Treeview"
        )
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="center")
        self.tree.column("algorithm", anchor="w")
        self.tree.column("status", anchor="w")

        self.tree.tag_configure("odd", background=COLORS["tree_bg"])
        self.tree.tag_configure("even", background=COLORS["tree_alt"])
        self.tree.tag_configure("slow", foreground=COLORS["warning"])
        self.tree.tag_configure("miss", foreground=COLORS["danger"])

        vsb = ttk.Scrollbar(
            wrap,
            orient="vertical",
            command=self.tree.yview,
            style="App.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _check_row(self, parent, label, items, vars_map, label_fn=str):
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(fill="x", pady=2)

        tk.Label(
            row,
            text=label + ":",
            width=11,
            anchor="w",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        for item in items:
            cb = tk.Checkbutton(
                row,
                text=label_fn(item),
                variable=vars_map[item],
                bg=COLORS["panel"],
                fg=COLORS["text"],
                selectcolor=COLORS["entry_bg"],
                activebackground=COLORS["panel"],
                activeforeground=COLORS["accent_light"],
                font=("Segoe UI", 9),
                cursor="hand2",
                highlightthickness=0,
                bd=0,
            )
            cb.pack(side="left", padx=(0, 14))

    def _button(self, parent, text, command, accent=False):
        bg = COLORS["accent"] if accent else COLORS["panel_alt"]
        fg = "#ffffff" if accent else COLORS["text"]
        hover = COLORS["accent_hover"] if accent else COLORS["border"]
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # ============================================================
    # THREAD-SAFE UI POSTING
    # ============================================================
    def _poll_ui_queue(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(50, self._poll_ui_queue)

    def _post(self, fn):
        """Call from any thread."""
        self._ui_queue.put(fn)

    # ============================================================
    # ACTIONS
    # ============================================================
    def _on_run(self):
        sizes = [s for s, v in self.size_vars.items() if v.get()]
        orders = [o for o, v in self.order_vars.items() if v.get()]
        algos = [a for a, v in self.algo_vars.items() if v.get()]

        if not sizes or not orders or not algos:
            messagebox.showwarning(
                "Empty config", "Check at least one size, order and algorithm."
            )
            return

        # Heavy warning for bubble at 30K
        if 30000 in sizes and "Bubble Sort" in algos:
            if not messagebox.askyesno(
                "Long-running benchmark",
                "Bubble Sort on 30,000 rows can take 5–15 MINUTES.\n"
                "The window will stay responsive — you can Stop anytime.\n\n"
                "Run anyway?",
            ):
                return

        self.results.clear()
        self.tree.delete(*self.tree.get_children())
        self.progress["value"] = 0
        self.stop_flag = False
        self.running = True
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.export_btn.config(state="disabled")

        threading.Thread(
            target=self._worker,
            args=(sizes, orders, algos),
            daemon=True,
        ).start()

    def _worker(self, sizes, orders, algos):
        def progress(done, total, message):
            pct = (done / total * 100.0) if total else 0
            self._post(lambda: self._update_progress(pct, message))

        def on_result(r):
            self._post(lambda: self._append_result(r))

        try:
            run_benchmark(
                sizes,
                orders,
                algos,
                on_progress=progress,
                on_result=on_result,
                should_stop=lambda: self.stop_flag,
            )
            self._post(self._on_finished)
        except Exception as exc:  # noqa: BLE001
            self._post(lambda: self._on_error(exc))

    def _on_stop(self):
        self.stop_flag = True
        self.progress_label.config(text="Stopping after current run…")

    def _on_finished(self):
        self.running = False
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.results:
            self.export_btn.config(state="normal")
        self.progress["value"] = 100
        self.progress_label.config(
            text=f"Complete. {len(self.results)} runs recorded — export to CSV for your report."
        )

    def _on_error(self, exc):
        self.running = False
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        messagebox.showerror("Benchmark error", str(exc))

    def _update_progress(self, pct, message):
        self.progress["value"] = pct
        self.progress_label.config(text=message)

    def _append_result(self, result):
        self.results.append(result)
        tag = "even" if len(self.results) % 2 == 0 else "odd"
        if result["status"].startswith("✗"):
            tag = "miss"
        elif "Bubble" in result["algorithm"] and result["time_us"] > 5_000_000:
            tag = "slow"
        self.tree.insert(
            "",
            "end",
            values=(
                result["algorithm"],
                f"{result['size']:,}",
                result["order"],
                f"{result['comparisons']:,}",
                self._fmt_time(result["time_us"]),
                result["status"],
            ),
            tags=(tag,),
        )
        self.tree.see(self.tree.get_children()[-1])

    @staticmethod
    def _fmt_time(us):
        return format_elapsed(us)

    def _on_export(self):
        if not self.results:
            messagebox.showinfo("No data", "Run the benchmark first.")
            return

        default_name = f"soniq_benchmark_{datetime.now():%Y%m%d_%H%M%S}.csv"

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=default_name,
            initialdir=ROOT_DIR,  # ← opens in project root
            title="Save benchmark report",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "Algorithm",
                        "Size",
                        "Input Order",
                        "Comparisons",
                        "Time (µs)",
                        "Status",
                    ]
                )
                for r in self.results:
                    w.writerow(
                        [
                            r["algorithm"],
                            r["size"],
                            r["order"],
                            r["comparisons"],
                            f"{r['time_us']:.2f}",
                            r["status"],
                        ]
                    )
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not write file:\n{exc}")
            return

        # Relative path if inside root — easier to read in the toast
        shown = path
        if path.startswith(ROOT_DIR + os.sep):
            shown = os.path.relpath(path, ROOT_DIR)
            shown = os.path.join(os.path.basename(ROOT_DIR), shown)

        messagebox.showinfo(
            "Exported",
            f"Saved {len(self.results)} runs to:\n\n{shown}",
        )

    def _on_quick_export(self):
        """Save directly to project root — no dialog, timestamped filename."""
        if not self.results:
            messagebox.showinfo("No data", "Run the benchmark first.")
            return

        filename = f"soniq_benchmark_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = os.path.join(ROOT_DIR, filename)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Algorithm", "Size", "Input Order",
                            "Comparisons", "Time (µs)", "Status"])
                for r in self.results:
                    w.writerow([
                        r["algorithm"], r["size"], r["order"],
                        r["comparisons"], f"{r['time_us']:.2f}", r["status"],
                    ])
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not write file:\n{exc}")
            return

        messagebox.showinfo(
            "Exported",
            f"Saved {len(self.results)} runs to:\n\n{os.path.basename(ROOT_DIR)}/{filename}",
        )

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno(
                "Benchmark running", "Stop the benchmark and close?"
            ):
                return
            self.stop_flag = True
        self.destroy()
