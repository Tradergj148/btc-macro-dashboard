"""Plotly + KV-table chart helpers.

Centralised so every page renders consistently themed widgets.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from _shared.style import (
    BG, PANEL_BG, GRID, ORANGE, ORANGE_DIM, WHITE,
    GREEN, RED, CYAN, YELLOW, MAGENTA,
)


def bbg_layout(title: str = "", height: int = 260) -> dict:
    """Standard Bloomberg-Terminal Plotly layout dict."""
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="JetBrains Mono, monospace", color=WHITE, size=10),
        title=dict(text=f"<b>{title.upper()}</b>", x=0.01, y=0.97,
                   font=dict(color=ORANGE, size=11)),
        margin=dict(l=44, r=10, t=28, b=28),
        height=height,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=WHITE,
                   showline=True, linecolor=ORANGE_DIM, tickfont=dict(size=9, color=WHITE)),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=WHITE,
                   showline=True, linecolor=ORANGE_DIM, tickfont=dict(size=9, color=WHITE)),
        legend=dict(font=dict(color=WHITE, size=9), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PANEL_BG, font_color=ORANGE,
                        bordercolor=ORANGE, font_family="JetBrains Mono"),
    )


def gauge(value, title: str) -> go.Figure:
    """Single-value gauge in Bloomberg orange palette. ±1 range."""
    val = float(value or 0)
    color = ORANGE
    if val > 0.2:  color = GREEN
    if val < -0.2: color = RED
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"valueformat": "+.2f", "font": {"color": color, "size": 26,
                                                 "family": "JetBrains Mono"}},
        gauge={
            "axis": {"range": [-1, 1], "tickwidth": 1, "tickcolor": ORANGE_DIM,
                     "tickfont": {"color": WHITE, "size": 9}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": BG,
            "borderwidth": 1, "bordercolor": ORANGE_DIM,
            "steps": [
                {"range": [-1.0, -0.5], "color": "#3a0606"},
                {"range": [-0.5, -0.2], "color": "#280303"},
                {"range": [-0.2,  0.2], "color": "#171717"},
                {"range": [ 0.2,  0.5], "color": "#072808"},
                {"range": [ 0.5,  1.0], "color": "#0c3a0e"},
            ],
            "threshold": {"line": {"color": ORANGE, "width": 2},
                          "thickness": 0.85, "value": val},
        },
        title={"text": f"<b>{title.upper()}</b>",
               "font": {"color": ORANGE, "size": 11,
                        "family": "JetBrains Mono"}},
    ))
    fig.update_layout(**bbg_layout(height=200))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    return fig


def line_panel(df: pd.DataFrame, title: str, height: int = 240,
               cols=None, palette=None) -> go.Figure:
    """Multi-line chart with the standard palette rotation."""
    palette = palette or [ORANGE, CYAN, GREEN, RED, YELLOW, MAGENTA, "#9B7DFF", "#FF8800"]
    fig = go.Figure()
    if isinstance(df, pd.Series):
        df = df.to_frame()
    use = cols or list(df.columns)
    for i, c in enumerate(use):
        if c not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df.index, y=df[c], mode="lines", name=c.upper(),
            line=dict(color=palette[i % len(palette)], width=1.2),
        ))
    fig.update_layout(**bbg_layout(title=title, height=height))
    return fig


def bar_panel(s: pd.Series, title: str, height: int = 220) -> go.Figure:
    """Coloured bar chart (green +ve / red -ve)."""
    colors = [GREEN if v >= 0 else RED for v in s.values]
    fig = go.Figure(go.Bar(x=s.index, y=s.values, marker_color=colors,
                           marker_line_width=0))
    fig.update_layout(**bbg_layout(title=title, height=height))
    return fig


def small_multiples(raw_df, cols, title, palette=None, ncols=2,
                    panel_height=180):
    """2-D grid of mini line charts; each column gets its own y-scale."""
    palette = palette or [ORANGE, CYAN, GREEN, RED, YELLOW, MAGENTA,
                          "#9B7DFF", "#FF8800"]
    cols = [c for c in cols if c in raw_df.columns]
    if not cols:
        return None
    nrows = (len(cols) + ncols - 1) // ncols
    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=[c.upper() for c in cols],
        horizontal_spacing=0.06, vertical_spacing=0.12,
    )
    for i, c in enumerate(cols):
        r, col_i = i // ncols + 1, i % ncols + 1
        fig.add_trace(go.Scatter(
            x=raw_df.index, y=raw_df[c], mode="lines",
            line=dict(color=palette[i % len(palette)], width=1.2),
            showlegend=False, name=c.upper(),
        ), row=r, col=col_i)
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="JetBrains Mono, monospace", color=WHITE, size=10),
        title=dict(text=f"<b>{title.upper()}</b>", x=0.01, y=0.99,
                   font=dict(color=ORANGE, size=11)),
        height=nrows * panel_height + 40,
        margin=dict(l=44, r=10, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=GRID, color=WHITE, linecolor=ORANGE_DIM,
                     tickfont=dict(size=9, color=WHITE))
    fig.update_yaxes(gridcolor=GRID, color=WHITE, linecolor=ORANGE_DIM,
                     tickfont=dict(size=9, color=WHITE))
    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(color=ORANGE, size=10, family="JetBrains Mono")
    return fig


# ============================================================
#  KV-table panel + formatters
# ============================================================
def kv_html(rows, title: str = "STRATEGY VITALS") -> str:
    """Build the orange-bordered KV-rows panel.

    `rows` is a list of (key, value, css_class) tuples where css_class
    is one of 'pos' / 'neg' / 'neu' / 'tic' / 'hl'.
    """
    inner = "".join([
        f"<div class='kv'><span class='k'>{k}</span>"
        f"<span class='v {cls}'>{v}</span></div>"
        for k, v, cls in rows
    ])
    return f"<div class='panel'><div class='panel-title'>{title}</div>{inner}</div>"


def fmt_pct(x):
    return f"{x*100:+.2f}%" if isinstance(x, (int, float)) else "—"


def fmt_num(x, dp=3):
    return f"{x:+.{dp}f}" if isinstance(x, (int, float)) else "—"


def pos_class(v):
    if isinstance(v, (int, float)):
        if v > 0:  return "pos"
        if v < 0:  return "neg"
    return "neu"
