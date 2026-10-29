"""Charte graphique commune aux figures du projet."""
PALETTE = {
    "primary": "#1F4E79",   # bleu du rapport
    "accent": "#C55A11",    # orange
    "muted": "#8EA9C1",
    "low": "#548235",
    "medium": "#BF9000",
    "high": "#C00000",
    "ok": "#2A9D8F",
    "warn": "#BF9000",
    "crit": "#C00000",
}


def style_axes(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors="#334155", labelsize=9)
    ax.grid(axis="y", color="#e2e8f0", lw=0.8)
    ax.set_axisbelow(True)


def use_report_style() -> None:
    """Police et couleurs alignées sur le rapport (Carlito ≈ Calibri)."""
    import matplotlib as mpl
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    family = ["Carlito"] if "Carlito" in installed else ["DejaVu Sans"]
    mpl.rcParams.update({"font.family": family, "font.size": 10.5,
                         "axes.titlesize": 12, "axes.labelcolor": "#404040", "text.color": "#222222"})
