"""Color palette + ttk theme for the Music Playlist Analyzer."""

from tkinter import ttk

# Palette
COLORS = {
    "bg": "#12121b",
    "panel": "#1b1b28",
    "panel_alt": "#262637",
    "border": "#32324a",
    "text": "#e6e6f2",
    "text_muted": "#8b8ba7",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "accent_light": "#a78bfa",
    "entry_bg": "#0d0d16",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "tree_bg": "#16161f",
    "tree_alt": "#1c1c28",
    "tree_sel": "#7c3aed",
}


def apply_theme(root):
    """Apply the ttk 'clam' theme and map our custom colors."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Treeview
    style.configure(
        "App.Treeview",
        background=COLORS["tree_bg"],
        fieldbackground=COLORS["tree_bg"],
        foreground=COLORS["text"],
        rowheight=26,
        borderwidth=0,
        font=("Segoe UI", 9),
    )
    style.configure(
        "App.Treeview.Heading",
        background=COLORS["panel_alt"],
        foreground=COLORS["accent_light"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padding=(8, 6),
    )
    style.map(
        "App.Treeview.Heading",
        background=[("active", COLORS["border"])],
    )
    style.map(
        "App.Treeview",
        background=[("selected", COLORS["tree_sel"])],
        foreground=[("selected", "#ffffff")],
    )

    # Scrollbar
    style.configure(
        "App.Vertical.TScrollbar",
        background=COLORS["panel_alt"],
        troughcolor=COLORS["panel"],
        bordercolor=COLORS["panel"],
        arrowcolor=COLORS["text_muted"],
        borderwidth=0,
    )

    # Combobox
    style.configure(
        "App.TCombobox",
        fieldbackground=COLORS["entry_bg"],
        background=COLORS["entry_bg"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["accent_light"],
        borderwidth=0,
        padding=6,
    )
    style.map(
        "App.TCombobox",
        fieldbackground=[("readonly", COLORS["entry_bg"])],
        foreground=[("readonly", COLORS["text"])],
    )

    return style