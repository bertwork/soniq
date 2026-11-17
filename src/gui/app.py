import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.algorithms import search as search_mod
from src.algorithms import sort as sort_mod
from src.data.generator import generate_songs
from src.gui.report import ReportWindow
from src.gui.styles import COLORS, apply_theme
from src.timer.timer import Timer, format_elapsed

MAX_DISPLAY = 300
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Generate-song options
SIZES = [
    ("1", 1),
    ("5", 5),
    ("10", 10),
    ("100", 100),
    ("1K", 1000),
    ("10K", 10000),
    ("30K", 30000),
]

ORDER_MAP = {
    "Random": "random",
    "Sorted by ID": "sorted_id",
    "Sorted by Title": "sorted_title",
}


class SoniqApp(tk.Tk):
    """SONIQ main application window."""

    def __init__(self):
        super().__init__()
        self.title("SONIQ")
        self.geometry("1280x820")
        self.minsize(1080, 760)
        self.configure(bg=COLORS["bg"])

        # State
        self.songs = []
        self.display_songs = []
        self.current_sort_key = None
        self.busy = False
        self._ui_queue = queue.Queue()
        self._loader_running = False
        self._loader_index = 0
        self._loader_text = ""

        apply_theme(self)
        self._build_header()
        self._build_body()
        self._build_statusbar()
        self._poll_ui_queue()
        self._load_sample()

    # ==============================================================
    # THREAD-SAFE UI POSTING
    # ==============================================================
    def _poll_ui_queue(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(40, self._poll_ui_queue)

    def _post(self, fn):
        self._ui_queue.put(fn)

    # ==============================================================
    # UI CONSTRUCTION
    # ==============================================================
    def _build_header(self):
        header = tk.Frame(self, bg=COLORS["panel"], height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SONIQ",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left", padx=20)

        tk.Label(
            header,
            text="Search  |  Sort  |  Benchmark",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 20))

        self.count_label = tk.Label(
            header,
            text="0 songs",
            bg=COLORS["panel"],
            fg=COLORS["accent_light"],
            font=("Segoe UI", 10, "bold"),
        )
        self.count_label.pack(side="right", padx=20)

    def _build_body(self):
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=COLORS["panel"], width=340)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.main_frame = tk.Frame(body, bg=COLORS["bg"])
        self.main_frame.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        self._build_sidebar(sidebar)
        self._build_tree(self.main_frame)
        self._build_loader(self.main_frame)

    # Sidebar
    def _build_sidebar(self, parent):
        # 1) GENERATE SONGS
        sec = self._section(parent, "GENERATE SONGS", pad_top=12)

        tk.Label(
            sec,
            text="Order",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
        ).pack(anchor="w")
        self.generate_order_var = tk.StringVar(value="Random")
        ttk.Combobox(
            sec,
            textvariable=self.generate_order_var,
            values=list(ORDER_MAP.keys()),
            state="readonly",
            style="App.TCombobox",
        ).pack(fill="x", pady=(2, 6))

        grid = tk.Frame(sec, bg=COLORS["panel"])
        grid.pack(fill="x")
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="size")
        for i, (label, size) in enumerate(SIZES):
            r, c = divmod(i, 4)
            btn = self._button(grid, label, lambda s=size: self._on_generate(s))
            btn.grid(row=r, column=c, sticky="ew", padx=1, pady=1)
            # disable row-padding issues
            btn.config(padx=6, pady=6, font=("Segoe UI", 9, "bold"))

        # 2) SEARCH
        sec = self._section(parent, "SEARCH")

        # Search by
        self.search_by_var = tk.StringVar(value="Song ID")
        sb_row = tk.Frame(sec, bg=COLORS["panel"])
        sb_row.pack(fill="x", pady=(0, 4))
        tk.Label(
            sb_row,
            text="Search by:",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
            width=10,
            anchor="w",
        ).pack(side="left")
        self._radio(sb_row, "Song ID", self.search_by_var).pack(side="left")
        self._radio(sb_row, "Title", self.search_by_var).pack(side="left", padx=(10, 0))

        # Algorithm
        self.search_algo_var = tk.StringVar(value="Linear")
        sa_row = tk.Frame(sec, bg=COLORS["panel"])
        sa_row.pack(fill="x", pady=(0, 4))
        tk.Label(
            sa_row,
            text="Algorithm:",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
            width=10,
            anchor="w",
        ).pack(side="left")
        self._radio(sa_row, "Linear", self.search_algo_var).pack(side="left")
        self._radio(sa_row, "Binary", self.search_algo_var).pack(
            side="left", padx=(10, 0)
        )

        # Input
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            sec,
            textvariable=self.search_var,
            bg=COLORS["entry_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=("Consolas", 10),
        )
        self.search_entry.pack(fill="x", ipady=6, pady=(2, 6))
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        self._button(sec, "Search", self._on_search, kind="accent").pack(fill="x")

        tk.Label(
            sec,
            text="Search is case-insensitive. Binary needs data sorted by the chosen key.",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # 3) SORT
        sec = self._section(parent, "SORT")

        self._label(sec, "Algorithm").pack(anchor="w")
        self.sort_algo_var = tk.StringVar(value="Merge Sort")
        ttk.Combobox(
            sec,
            textvariable=self.sort_algo_var,
            values=["Bubble Sort", "Merge Sort"],
            state="readonly",
            style="App.TCombobox",
        ).pack(fill="x", pady=(2, 4))

        self._label(sec, "Sort key").pack(anchor="w")
        self.sort_key_var = tk.StringVar(value="song_id")
        ttk.Combobox(
            sec,
            textvariable=self.sort_key_var,
            values=["song_id", "title", "artist", "year", "duration"],
            state="readonly",
            style="App.TCombobox",
        ).pack(fill="x", pady=(2, 6))

        self._button(sec, "Sort", self._on_sort, kind="accent").pack(fill="x")

        # 4) REPORT
        sec = self._section(parent, "BENCHMARK")
        self._button(sec, "Generate Report", self._on_report, kind="accent").pack(
            fill="x"
        )
        tk.Label(
            sec,
            text="Run the Data Run Log across sizes & input orders.",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # 5) LAST OPERATION
        sec = self._section(parent, "LAST OPERATION")
        self.timer_label = tk.Label(
            sec,
            text="—",
            bg=COLORS["panel"],
            fg=COLORS["accent_light"],
            font=("Consolas", 11, "bold"),
        )
        self.timer_label.pack(anchor="w")
        self.detail_label = tk.Label(
            sec,
            text="No operations yet.",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
            wraplength=300,
            justify="left",
        )
        self.detail_label.pack(anchor="w", pady=(4, 0))

    # Treeview
    def _build_tree(self, parent):
        wrap = tk.Frame(parent, bg=COLORS["bg"])
        wrap.pack(fill="both", expand=True)

        cols = ("id", "title", "artist", "album", "genre", "year", "duration")
        headings = {
            "id": "Song ID",
            "title": "Title",
            "artist": "Artist",
            "album": "Album",
            "genre": "Genre",
            "year": "Year",
            "duration": "Duration",
        }
        widths = {
            "id": 120,
            "title": 240,
            "artist": 170,
            "album": 200,
            "genre": 110,
            "year": 70,
            "duration": 90,
        }
        anchors = {
            "id": "w",
            "title": "w",
            "artist": "w",
            "album": "w",
            "genre": "w",
            "year": "center",
            "duration": "center",
        }

        self.tree = ttk.Treeview(
            wrap,
            columns=cols,
            show="headings",
            style="App.Treeview",
            selectmode="browse",
        )
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor=anchors[c], stretch=True)

        self.tree.tag_configure("odd", background=COLORS["tree_bg"])
        self.tree.tag_configure("even", background=COLORS["tree_alt"])

        vsb = ttk.Scrollbar(
            wrap,
            orient="vertical",
            command=self.tree.yview,
            style="App.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    # Loader overlay
    def _build_loader(self, parent):
        self.loader = tk.Frame(parent, bg=COLORS["bg"])
        # intentionally not placed yet
        inner = tk.Frame(self.loader, bg=COLORS["bg"])
        inner.pack(expand=True)

        self.loader_label = tk.Label(
            inner,
            text="",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 14, "bold"),
        )
        self.loader_label.pack()

        # Big live stopwatch readout 
        self.stopwatch_label = tk.Label(
            inner,
            text="0.000 s",
            bg=COLORS["bg"],
            fg=COLORS["accent_light"],
            font=("Consolas", 32, "bold"),
        )
        self.stopwatch_label.pack(pady=(14, 0))

        self.loader_sub = tk.Label(
            inner,
            text="This may take a moment…",
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 9),
        )
        self.loader_sub.pack(pady=(10, 0))

        # Stopwatch state 
        self._stopwatch_running = False
        self._stopwatch_job = None
        self._stopwatch_start = 0.0

    def _show_loader(self, text, sub="This may take a moment…"):
        self._loader_text = text
        self._loader_running = True
        self.stopwatch_label.config(text="0.000 s")
        self.loader_sub.config(text=sub)
        self.loader.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loader.lift()
        self._animate_loader()

    def _hide_loader(self):
        self._loader_running = False
        self.loader.place_forget()

    def _animate_loader(self):
        if not self._loader_running:
            return
        self._loader_index = (self._loader_index + 1) % len(SPINNER)
        self.loader_label.config(
            text=f"{SPINNER[self._loader_index]}  {self._loader_text}"
        )
        self.after(80, self._animate_loader)

        # Live stopwatch

    def _start_stopwatch(self):
        self._stopwatch_start = time.perf_counter()
        self._stopwatch_running = True
        self._tick_stopwatch()

    def _tick_stopwatch(self):
        if not self._stopwatch_running:
            return
        elapsed_us = (time.perf_counter() - self._stopwatch_start) * 1_000_000
        self.stopwatch_label.config(text=format_elapsed(elapsed_us))
        self._stopwatch_job = self.after(50, self._tick_stopwatch)

    def _stop_stopwatch(self):
        self._stopwatch_running = False
        if self._stopwatch_job is not None:
            self.after_cancel(self._stopwatch_job)
            self._stopwatch_job = None

    # Status bar
    def _build_statusbar(self):
        bar = tk.Frame(self, bg=COLORS["panel"], height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.status_label = tk.Label(
            bar,
            text="Ready.",
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_label.pack(side="left", padx=16, pady=6)

    # ==============================================================
    # SMALL WIDGET HELPERS
    # ==============================================================
    def _section(self, parent, title, pad_top=14):
        outer = tk.Frame(parent, bg=COLORS["panel"])
        outer.pack(fill="x", padx=16, pady=(pad_top, 0))
        tk.Label(
            outer,
            text=title,
            bg=COLORS["panel"],
            fg=COLORS["accent_light"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 6))
        body = tk.Frame(outer, bg=COLORS["panel"])
        body.pack(fill="x")
        return body

    def _label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=COLORS["panel"],
            fg=COLORS["text_muted"],
            font=("Segoe UI", 8),
        )

    def _button(self, parent, text, command, kind="default"):
        if kind == "accent":
            bg, fg, hover = COLORS["accent"], "#ffffff", COLORS["accent_hover"]
        else:
            bg, fg, hover = COLORS["panel_alt"], COLORS["text"], COLORS["border"]
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
            padx=8,
            pady=6,
            font=("Segoe UI", 9, "bold" if kind == "accent" else "normal"),
            cursor="hand2",
        )
        btn.bind(
            "<Enter>",
            lambda e: btn.config(bg=hover) if str(btn["state"]) != "disabled" else None,
        )
        btn.bind(
            "<Leave>",
            lambda e: btn.config(bg=bg) if str(btn["state"]) != "disabled" else None,
        )
        return btn

    def _radio(self, parent, text, var):
        return tk.Radiobutton(
            parent,
            text=text,
            variable=var,
            value=text,
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

    # ==============================================================
    # DATA + UI UPDATES
    # ==============================================================
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        shown = self.display_songs[:MAX_DISPLAY]
        for i, song in enumerate(shown):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=song.to_row(), tags=(tag,))

        total = len(self.display_songs)
        self.count_label.config(text=f"{total:,} songs")
        if total > MAX_DISPLAY:
            self._set_status(
                f"Showing {MAX_DISPLAY} of {total:,} rows (display capped for performance)."
            )

    def _set_status(self, msg):
        self.status_label.config(text=msg)

    def _load_sample(self):
        self.songs = generate_songs(25, seed=42)
        self.display_songs = self.songs
        self.current_sort_key = None
        self._refresh_tree()
        self._set_status("SONIQ ready — loaded 25 sample songs.")

    def _update_timer_panel(self, op_name, n, comparisons, elapsed_us):
        self.timer_label.config(text=format_elapsed(elapsed_us))

        detail = f"{op_name}\nRows: {n:,}"
        if comparisons:
            detail += f"  •  Comparisons: {comparisons:,}"
        self.detail_label.config(text=detail)

    # ==============================================================
    # HANDLERS
    # ==============================================================
    def _on_generate(self, n):
        if self.busy:
            return
        order_label = self.generate_order_var.get()
        order = ORDER_MAP[order_label]

        self._set_status(f"Generating {n:,} songs ({order_label})…")
        self.update_idletasks()

        with Timer() as t:
            self.songs = generate_songs(n, order=order)

        self.display_songs = self.songs
        # Track sort state
        if order == "sorted_id":
            self.current_sort_key = "song_id"
        elif order == "sorted_title":
            self.current_sort_key = "title"
        else:
            self.current_sort_key = None

        self._refresh_tree()
        self._set_status(
            f"✓ Generated {n:,} songs ({order_label}) in "
            f"{t.elapsed_us / 1000:.2f} ms"
        )
        self._update_timer_panel(f"Generate ({order_label})", n, 0, t.elapsed_us)

    def _on_search(self):
        if self.busy:
            return
        target = self.search_var.get().strip()
        if not target:
            messagebox.showwarning(
                "Missing input", "Enter a search value (Song ID or Title)."
            )
            return
        if not self.songs:
            messagebox.showinfo("No data", "Generate songs first.")
            return

        search_by = self.search_by_var.get()  # "Song ID" | "Title"
        algo = self.search_algo_var.get()  # "Linear"  | "Binary"
        field = "song_id" if search_by == "Song ID" else "title"

        # Warn if binary search against mismatched sort
        if algo == "Binary" and self.current_sort_key != field:
            if not messagebox.askyesno(
                "Binary search on unsorted data",
                f"Binary Search needs data sorted by '{field}'.\n"
                f"Current sort: {self.current_sort_key or 'unknown / unsorted'}.\n\n"
                "Results will likely be wrong. Continue anyway?",
            ):
                return

        with Timer() as t:
            if algo == "Linear":
                idx, comps = search_mod.linear_search(self.songs, target, field)
            else:
                idx, comps = search_mod.binary_search(self.songs, target, field)

        if idx >= 0:
            song = self.songs[idx]
            self._set_status(
                f"✓ Found {song.title} — index {idx} • "
                f"{comps:,} comparisons • {t.elapsed_us:.2f} µs"
            )
        else:
            self._set_status(
                f"✓ Found {song.title} — index {idx} • "
                f"{comps:,} comparisons • {t.elapsed_us:.2f} µs"
            )

        self._update_timer_panel(
            f"Search ({algo}/{search_by})", len(self.songs), comps, t.elapsed_us
        )

        # Highlight if visible
        if idx >= 0:
            children = self.tree.get_children()
            if idx < len(children):
                self.tree.selection_set(children[idx])
                self.tree.see(children[idx])

    def _on_sort(self):
        if self.busy:
            return
        if not self.songs:
            messagebox.showinfo("No data", "Generate songs first.")
            return

        algo = self.sort_algo_var.get()
        key = self.sort_key_var.get()
        n = len(self.songs)

        # Heavy warning for bubble sort on big data
        if algo == "Bubble Sort" and n >= 5000:
            if not messagebox.askyesno(
                "Slow sort warning",
                f"Bubble Sort on {n:,} rows can take a long time\n"
                f"(often several minutes). The UI will stay responsive.\n\n"
                "Continue?",
            ):
                return

        self.busy = True
        self._show_loader(
            f"Sorting {n:,} songs with {algo}…",
            "Bubble Sort is O(n²) — please be patient.",
        )
        self._set_status(f"Sorting {n:,} songs by '{key}' using {algo}…")
        self._start_stopwatch()

        def worker():
            with Timer() as t:
                if algo == "Bubble Sort":
                    arr, comps = sort_mod.bubble_sort(self.songs, key)
                else:
                    arr, comps = sort_mod.merge_sort(self.songs, key)
            self._post(lambda: self._on_sort_done(arr, comps, t.elapsed_us, algo, key))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sort_done(self, arr, comps, elapsed_us, algo, key):
        self._stop_stopwatch()  # ← NEW
        self.songs = arr
        self.display_songs = arr
        self.current_sort_key = key
        self._refresh_tree()
        self._hide_loader()
        self.busy = False

        self._set_status(
            f"✓ {algo} sorted {len(arr):,} rows by '{key}' — "
            f"{comps:,} comparisons • {format_elapsed(elapsed_us)}"
        )
        self._update_timer_panel(f"Sort ({algo}/{key})", len(arr), comps, elapsed_us)

    def _on_report(self):
        if self.busy:
            return
        ReportWindow(self)


# direct execution:  python src/gui/app.py
if __name__ == "__main__":
    SoniqApp().mainloop()
