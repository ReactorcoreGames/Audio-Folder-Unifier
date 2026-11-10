"""The "unifier" theme: a 2000s media-player look. Medium blue-green panels, dark LCD-style
wells for inputs and the log, neon lime for indicators, focus, selection and the progress fill.

Neon lime never goes on body text against the teal panels; it's only used as a fill (with
dark ink on top), a border, or on the dark wells where it has the contrast to pass.
"""

# ── Palette ─────────────────────────────────────────────────────────────────
# Contrast ratios (WCAG) noted against the surface each colour sits on.
PALETTE = {
    # Backgrounds
    "bg_base":        "#1D525B",   # root window, header/footer band
    "bg_surface":     "#26656F",   # LabelFrame panels
    "bg_input":       "#123A41",   # dark LCD wells: entries, combobox, log, progress trough
    "bg_button":      "#30808B",   # secondary buttons (Browse, Open output folder)
    "bg_button_hot":  "#3B95A1",   # their hover

    # Accents
    "accent_neon":    "#C8FF2E",   # radio/check fill, progress, focus, selection. Dark ink on top
    "accent_yellow":  "#F2FF5C",   # hover on neon fills
    "accent_soft":    "#E4FF9C",   # LabelFrame titles, links, log text. 6.0:1 on surface
    "accent_glow":    "#4FA0A9",   # borders, separators

    # Text
    "text_primary":   "#F2FBF7",   # 6.3:1 on surface, 8.3:1 on base
    "text_secondary": "#C4E2DD",   # captions, tech anchors. 4.8:1 on surface
    "ink":            "#0B2226",   # dark text on neon / semantic fills

    # Semantic (green means go, red means stop). All carry dark ink.
    "success":        "#4FD86E",
    "danger":         "#FF6F6F",
    "warning":        "#FFC542",
    "info":           "#55CCF2",
}

# ── Fonts ───────────────────────────────────────────────────────────────────
FONT_FAMILY    = "Segoe UI"
FONT_TITLE     = (FONT_FAMILY, 18, "bold")
FONT_HEADING   = (FONT_FAMILY, 14, "bold")
FONT_BODY      = (FONT_FAMILY, 11)
FONT_BODY_BOLD = (FONT_FAMILY, 11, "bold")
FONT_BIG_BOLD  = (FONT_FAMILY, 13, "bold")   # Start / Stop
FONT_SMALL     = (FONT_FAMILY, 10)
FONT_TINY      = (FONT_FAMILY, 9)
FONT_MONO      = ("Consolas", 10)

# ── Theme registration ──────────────────────────────────────────────────────
THEME_FAMILY = "unifier"
THEME_NAME   = f"{THEME_FAMILY}-dark"


def register_theme():
    """Register the theme family. Call before ttk.Window(themename=THEME_NAME)."""
    import ttkbootstrap as ttk
    p = PALETTE
    ttk.Theme(
        name=THEME_FAMILY,
        primary=p["accent_neon"],
        secondary=p["bg_button"],
        success=p["success"],
        info=p["info"],
        warning=p["warning"],
        danger=p["danger"],
        dark=dict(background=p["bg_base"], foreground=p["text_primary"]),
    ).register()


def apply_theme(style, root=None):
    """Fine-tune surfaces, fonts and custom styles on top of the registered theme.
    Call right after the window is created, before building widgets."""
    p = PALETTE
    if root is not None:
        root.configure(bg=p["bg_base"])
        # The combobox dropdown list is a plain Tk Listbox and ignores ttk styles
        root.option_add("*TCombobox*Listbox.background", p["bg_input"])
        root.option_add("*TCombobox*Listbox.foreground", p["text_primary"])
        root.option_add("*TCombobox*Listbox.selectBackground", p["accent_neon"])
        root.option_add("*TCombobox*Listbox.selectForeground", p["ink"])
        root.option_add("*TCombobox*Listbox.font", FONT_BODY)

    style.configure(".",
                    background=p["bg_base"],
                    foreground=p["text_primary"],
                    bordercolor=p["accent_glow"],
                    darkcolor=p["bg_base"],
                    lightcolor=p["bg_surface"],
                    troughcolor=p["bg_input"],
                    fieldbackground=p["bg_input"],
                    selectbackground=p["accent_neon"],
                    selectforeground=p["ink"],
                    font=FONT_BODY)

    # ── Frames and labels ──
    style.configure("TFrame",            background=p["bg_base"])
    style.configure("Surface.TFrame",    background=p["bg_surface"])
    style.configure("TLabelframe",       background=p["bg_surface"], bordercolor=p["accent_glow"])
    style.configure("TLabelframe.Label", background=p["bg_surface"], foreground=p["accent_soft"],
                    font=FONT_BODY_BOLD)

    style.configure("TLabel", background=p["bg_surface"], foreground=p["text_primary"], font=FONT_BODY)
    style.configure("secondary.TLabel", background=p["bg_surface"], foreground=p["text_secondary"],
                    font=FONT_SMALL)
    # Labels sitting straight on the window background (header, footer, progress area)
    style.configure("Base.TLabel",      background=p["bg_base"], foreground=p["text_primary"])
    style.configure("BaseDim.TLabel",   background=p["bg_base"], foreground=p["text_secondary"],
                    font=FONT_SMALL)
    style.configure("Title.TLabel",     background=p["bg_base"], foreground=p["text_primary"],
                    font=FONT_TITLE)
    style.configure("Subtitle.TLabel",  background=p["bg_base"], foreground=p["accent_soft"],
                    font=FONT_BODY)
    style.configure("Footer.TLabel",    background=p["bg_base"], foreground=p["text_secondary"],
                    font=FONT_TINY)
    style.configure("Link.TLabel",      background=p["bg_base"], foreground=p["accent_soft"],
                    font=(FONT_FAMILY, 9, "underline"))
    # The effect description box: a dark well like the inputs
    style.configure("Well.TLabel",      background=p["bg_input"], foreground=p["text_primary"],
                    font=FONT_BODY, padding=(10, 6))

    # ── Buttons ──
    style.configure("TButton", font=FONT_BODY, background=p["bg_button"], foreground=p["text_primary"],
                    bordercolor=p["accent_glow"], focuscolor=p["accent_neon"], padding=(10, 4))
    style.map("TButton",
              background=[("disabled", p["bg_surface"]), ("pressed", p["bg_input"]),
                          ("active", p["bg_button_hot"])],
              foreground=[("disabled", p["text_secondary"])],
              bordercolor=[("active", p["accent_neon"])])

    for name in ("success", "danger"):
        style.configure(f"{name}.TButton", background=p[name], foreground=p["ink"],
                        bordercolor=p[name], font=FONT_BIG_BOLD, padding=(10, 6))
        style.map(f"{name}.TButton",
                  background=[("disabled", p["bg_surface"]), ("active", p["accent_yellow"])],
                  foreground=[("disabled", p["text_secondary"])],
                  bordercolor=[("disabled", p["accent_glow"]), ("active", p["accent_yellow"])])

    # ── Inputs ──
    for name in ("TEntry", "TCombobox"):
        style.configure(name, fieldbackground=p["bg_input"], foreground=p["text_primary"],
                        bordercolor=p["accent_glow"], insertcolor=p["text_primary"],
                        arrowcolor=p["accent_neon"], background=p["bg_input"])
        style.map(name,
                  fieldbackground=[("readonly", p["bg_input"]), ("disabled", p["bg_surface"])],
                  foreground=[("readonly", p["text_primary"]), ("disabled", p["text_secondary"])],
                  bordercolor=[("focus", p["accent_neon"]), ("hover", p["accent_neon"])],
                  # readonly combobox text gets "selected" on focus; keep it a calm well, not a lime bar
                  selectbackground=[("readonly", p["bg_input"])],
                  selectforeground=[("readonly", p["text_primary"])])

    for name in ("TRadiobutton", "TCheckbutton"):
        style.configure(name, background=p["bg_surface"], foreground=p["text_primary"], font=FONT_BODY)
        style.map(name,
                  background=[("active", p["bg_surface"])],
                  foreground=[("disabled", p["text_secondary"]), ("active", p["accent_soft"])])

    # ── Progress, separators, scrollbars ──
    # ttkbootstrap's progressbar is a recoloured rounded image with a stray end-cap and a trough
    # colour we can't set. A flat clam bar fits the LCD look better: lime fill in a dark well.
    if "Neon.Horizontal.Progressbar.trough" not in style.element_names():
        style.element_create("Neon.Horizontal.Progressbar.trough", "from", "clam")
        style.element_create("Neon.Horizontal.Progressbar.pbar", "from", "clam")
    style.layout("Neon.Horizontal.TProgressbar", [
        ("Neon.Horizontal.Progressbar.trough", {"sticky": "nswe", "children": [
            ("Neon.Horizontal.Progressbar.pbar", {"side": "left", "sticky": "ns"})]})])
    style.configure("Neon.Horizontal.TProgressbar", background=p["accent_neon"],
                    troughcolor=p["bg_input"], bordercolor=p["accent_glow"],
                    lightcolor=p["accent_neon"], darkcolor=p["accent_neon"], thickness=16)

    style.configure("TSeparator", background=p["accent_glow"])
    style.configure("Neon.TSeparator", background=p["accent_neon"])
    # Scrollbars are image-based too; use them with bootstyle="secondary-round" (teal thumb)
