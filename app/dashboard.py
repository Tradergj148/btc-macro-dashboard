"""Bloomberg-Terminal styled Streamlit dashboard.

Run:    streamlit run app/dashboard.py
Refresh data:  python -m src.pipeline
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# ============================================================
#  CLASSIC BLOOMBERG TERMINAL PALETTE
#  - Signature orange #FA8B1F (warm, slightly red-leaning)
#  - Pure black background
#  - White-dominant data values
#  - Cyan for tickers / symbols
#  - Yellow for highlights / warnings
#  - Bright green/red for up/down
# ============================================================
ORANGE      = "#FA8B1F"
ORANGE_DIM  = "#A85708"
ORANGE_DEEP = "#C76A11"
BG          = "#000000"
PANEL_BG    = "#070707"
GRID        = "#1A1A1A"
WHITE       = "#FFFFFF"
TEXT        = "#FFFFFF"
TEXT_DIM    = "#9A9A9A"
GREEN       = "#00FF66"
RED         = "#FF1F1F"
CYAN        = "#22D3EE"
YELLOW      = "#FFEB3B"
MAGENTA     = "#FF44FF"

st.set_page_config(
    page_title="BTC // MACRO LIQUIDITY TERMINAL",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
#  GLOBAL CSS
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"], .stApp, .main, .block-container {{
    background-color: {BG} !important;
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace !important;
    font-size: 12px !important;
}}
.block-container {{
    padding-top: 0.4rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}
h1, h2, h3, h4 {{
    font-family: 'JetBrains Mono', monospace !important;
    color: {ORANGE} !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid {ORANGE_DIM};
    padding-bottom: 4px !important;
    margin-top: 8px !important;
    margin-bottom: 8px !important;
}}
h1 {{ font-size: 18px !important; }}
h2 {{ font-size: 15px !important; }}
h3 {{ font-size: 13px !important; }}
hr {{ border-color: {ORANGE_DIM} !important; }}

/* ===== TOP HEADER: solid orange with black text (Bloomberg trademark) ===== */
.topbar {{
    background: {ORANGE};
    color: {BG};
    padding: 6px 14px;
    font-weight: 700;
    letter-spacing: 0.18em;
    font-size: 13px;
    margin-bottom: 0;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid {BG};
}}
.topbar .right {{
    background: {BG};
    color: {ORANGE};
    padding: 2px 10px;
    border: 1px solid {BG};
    font-weight: 700;
}}

/* ===== Function-key strip ===== */
.fnstrip {{
    background: {BG};
    border-bottom: 1px solid {ORANGE_DIM};
    padding: 4px 8px;
    display: flex;
    gap: 6px;
    margin-bottom: 6px;
}}
.fnkey {{
    background: {ORANGE};
    color: {BG};
    padding: 1px 7px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.1em;
}}
.fnlbl {{
    color: {WHITE};
    font-size: 10px;
    margin-right: 8px;
    letter-spacing: 0.05em;
}}

/* ===== Status bar ===== */
.statusbar {{
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 5px 10px;
    font-size: 10px;
    color: {WHITE};
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    letter-spacing: 0.05em;
}}
.statusbar b {{ color: {ORANGE}; }}
.statusbar .dim {{ color: {TEXT_DIM}; }}

/* ===== Panels ===== */
.panel {{
    border: 1px solid {ORANGE_DIM};
    background: {PANEL_BG};
    padding: 8px 10px;
    margin-bottom: 6px;
}}
.panel-title {{
    color: {BG};
    background: {ORANGE};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.18em;
    padding: 3px 8px;
    margin: -8px -10px 8px -10px;
    text-transform: uppercase;
}}

/* ===== Key-value rows ===== */
.kv {{ display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dotted {GRID}; font-size: 11px; }}
.kv .k {{ color: {ORANGE}; letter-spacing: 0.05em; }}
.kv .v {{ color: {WHITE}; font-weight: 500; }}
.pos {{ color: {GREEN} !important; }}
.neg {{ color: {RED}   !important; }}
.neu {{ color: {WHITE} !important; }}
.tic {{ color: {CYAN}  !important; }}
.hl  {{ color: {YELLOW} !important; }}

/* ===== Bias banner ===== */
.bias-banner {{
    padding: 14px 8px;
    text-align: center;
    border: 1px solid {ORANGE};
    background: {PANEL_BG};
    margin-bottom: 6px;
    position: relative;
}}
.bias-banner::before {{
    content: 'REGIME';
    position: absolute;
    top: -8px; left: 8px;
    background: {BG};
    color: {ORANGE};
    font-size: 9px;
    padding: 0 6px;
    letter-spacing: 0.2em;
}}
.bias-banner .value {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.1em;
    margin-top: 2px;
}}
.bias-banner .sub {{
    font-size: 11px;
    color: {WHITE};
    margin-top: 6px;
    letter-spacing: 0.05em;
}}
.bias-banner .sub b {{ color: {WHITE}; }}

/* ===== Tabs ===== */
button[data-baseweb="tab"] {{
    background: {BG} !important;
    color: {ORANGE} !important;
    border: 1px solid {ORANGE_DIM} !important;
    border-bottom: none !important;
    border-radius: 0 !important;
    margin-right: 2px !important;
    padding: 6px 16px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    background: {ORANGE} !important;
    color: {BG} !important;
    border-color: {ORANGE} !important;
}}
div[data-baseweb="tab-panel"] {{
    border: 1px solid {ORANGE_DIM};
    padding: 10px;
    background: {BG};
}}
div[data-baseweb="tab-list"] {{ border-bottom: 1px solid {ORANGE_DIM}; }}

/* ===== Streamlit info / alert ===== */
div[data-testid="stAlert"] {{
    background: {PANEL_BG} !important;
    border: 1px solid {ORANGE} !important;
    color: {ORANGE} !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 0 !important;
}}
div[data-testid="stAlert"] * {{ color: {ORANGE} !important; }}

/* ===== Hide Streamlit chrome ===== */
#MainMenu, header, footer {{ visibility: hidden; }}
.stDeployButton {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}

/* ===== Tables ===== */
.dataframe, .stDataFrame {{
    background: {PANEL_BG} !important;
    color: {WHITE} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
}}

/* ===== Scrollbars ===== */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {ORANGE_DIM}; }}


/* ===== TRADING SESSIONS PANEL ===== */
.sessions-panel {{
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 8px 12px;
    margin-bottom: 8px;
    position: relative;
}}
.sessions-title {{
    color: {ORANGE};
    font-size: 10px;
    letter-spacing: 0.18em;
    font-weight: 700;
    margin-bottom: 8px;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.sessions-title .now-badge {{
    color: {YELLOW};
    font-size: 11px;
    letter-spacing: 0.10em;
}}
.sessions-rows {{ position: relative; }}
.session-row {{
    display: flex;
    align-items: center;
    margin: 3px 0;
    height: 18px;
    position: relative;
}}
.session-label {{
    color: currentColor;
    font-size: 9px;
    width: 110px;
    text-align: right;
    margin-right: 12px;
    letter-spacing: 0.10em;
    font-weight: 700;
    flex-shrink: 0;
}}
/* session label color is inherited from row */
.session-track {{
    flex: 1;
    height: 14px;
    background: {GRID};
    position: relative;
    border-radius: 1px;
}}
.session-block {{
    position: absolute;
    height: 100%;
    top: 0;
    border-radius: 1px;
    opacity: 0.55;
    transition: opacity .2s;
}}
.session-row.active .session-block {{
    opacity: 1.0;
    box-shadow: 0 0 6px currentColor;
}}
.session-time-text {{
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    font-size: 8px;
    color: {WHITE};
    white-space: nowrap;
    pointer-events: none;
    font-weight: 600;
    text-shadow: 0 0 2px black;
}}
.session-active-badge {{
    background: {GREEN};
    color: {BG};
    font-weight: 700;
    font-size: 8px;
    letter-spacing: 0.15em;
    padding: 1px 5px;
    margin-left: 6px;
    flex-shrink: 0;
    width: 60px;
    text-align: center;
}}
.session-pending-badge {{
    color: {TEXT_DIM};
    font-size: 8px;
    margin-left: 6px;
    width: 60px;
    text-align: center;
    flex-shrink: 0;
}}
/* single vertical DASHED NOW-line that spans every row (vol intensity + 4 sessions) */
.sessions-now-line {{
    position: absolute;
    top: 0;
    bottom: 0;
    /* track region in every row goes from 122px (label+gap) to (100% - 66px) (badge+gap) */
    left: calc(122px + (100% - 188px) * var(--now-pct, 0));
    width: 0;
    border-left: 2px dashed {YELLOW};
    z-index: 12;
    pointer-events: none;
}}
.sessions-now-line::before {{
    content: '';
    position: absolute;
    top: -4px;
    left: -5px;
    width: 8px;
    height: 8px;
    background: {YELLOW};
    border-radius: 50%;
    box-shadow: 0 0 4px {YELLOW};
}}
.sessions-now-line::after {{
    content: 'NOW';
    position: absolute;
    top: -14px;
    left: -14px;
    color: {YELLOW};
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-shadow: 0 0 2px black;
}}
.session-axis {{
    margin-left: 122px;
    margin-top: 2px;
    color: {WHITE};
    font-size: 8px;
    display: flex;
    justify-content: space-between;
}}


/* ===== VOLUME INTENSITY OVERLAP TRACK ===== */
.vol-intensity-row {{
    display: flex;
    align-items: center;
    margin: 6px 0 8px 0;
    height: 22px;
    position: relative;
    border-bottom: 1px dotted {ORANGE_DIM};
    padding-bottom: 6px;
}}
.vol-intensity-label {{
    color: {ORANGE};
    font-size: 9px;
    width: 110px;
    text-align: right;
    margin-right: 12px;
    letter-spacing: 0.10em;
    font-weight: 700;
    flex-shrink: 0;
}}
.vol-intensity-track {{
    flex: 1;
    height: 18px;
    background: {GRID};
    position: relative;
    border-radius: 1px;
}}
.vol-zone {{
    position: absolute;
    height: 100%;
    top: 0;
    border-right: 1px solid {BG};
}}
.vol-zone-text {{
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    font-size: 7px;
    color: {WHITE};
    white-space: nowrap;
    pointer-events: none;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-shadow: 0 0 2px black;
}}
.vol-intensity-meter {{
    width: 60px;
    margin-left: 6px;
    flex-shrink: 0;
    text-align: center;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.10em;
    padding: 1px 5px;
}}


/* ===== COMPACT REGIME STRIP (6 cells, fully responsive) ===== */
.regime-strip {{
    display: flex;
    flex-wrap: nowrap;
    gap: 4px;
    margin: 8px 0;
    overflow: hidden;
}}
.regime-cell {{
    flex: 1 1 0;
    min-width: 0;
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 8px 6px 6px 6px;
    text-align: center;
    position: relative;
}}
.regime-cell.composite {{
    flex: 1.6 1 0;
    border: 2px solid {ORANGE};
    background: linear-gradient(180deg, rgba(250,139,31,0.08), {PANEL_BG} 60%);
}}
.regime-cell .rc-label {{
    color: {ORANGE};
    font-size: 9px;
    letter-spacing: 0.18em;
    font-weight: 700;
    text-transform: uppercase;
    line-height: 1;
}}
.regime-cell.composite .rc-label {{
    font-size: 10px;
    letter-spacing: 0.20em;
}}
.regime-cell .rc-bias {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.10em;
    margin-top: 4px;
    line-height: 1;
}}
.regime-cell.composite .rc-bias {{
    font-size: 14px;
    margin-top: 6px;
}}
.regime-cell .rc-score {{
    font-size: 18px;
    font-weight: 700;
    margin: 4px 0 4px;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
}}
.regime-cell.composite .rc-score {{
    font-size: 26px;
    margin: 6px 0;
}}
.regime-cell .rc-bar {{
    position: relative;
    height: 5px;
    background: {GRID};
    border-radius: 1px;
    margin: 4px 4px 2px;
    overflow: visible;
}}
.regime-cell .rc-bar::before {{
    content: '';
    position: absolute;
    left: 50%;
    top: -2px; bottom: -2px;
    width: 1px;
    background: {ORANGE_DIM};
}}
.regime-cell .rc-marker {{
    position: absolute;
    width: 8px;
    height: 12px;
    top: -3.5px;
    margin-left: -4px;
    border-radius: 1px;
}}
.regime-cell .rc-strength {{
    color: {TEXT_DIM};
    font-size: 8px;
    margin-top: 4px;
    letter-spacing: 0.15em;
    font-weight: 700;
}}
.regime-cell .rc-pos {{
    background: {YELLOW};
    color: {BG};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.15em;
    padding: 2px 6px;
    margin: 6px auto 0;
    display: inline-block;
}}

</style>
""", unsafe_allow_html=True)


# ============================================================
#  Plotly base layout helper
# ============================================================
def bbg_layout(title: str = "", height: int = 260) -> dict:
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
    palette = palette or [ORANGE, CYAN, GREEN, RED, YELLOW, MAGENTA, "#9B7DFF", "#FF8800"]
    fig = go.Figure()
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
#  DATA LOADERS
# ============================================================
@st.cache_data(ttl=600)
def load(name: str) -> pd.DataFrame:
    p = DATA / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_summary() -> dict:
    p = DATA / "summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


# ============================================================
#  HEADER + FUNCTION KEYS + STATUS BAR
# ============================================================
summary = load_summary()
asof = summary.get("asof", "—")
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

regime = summary.get("regime_score")
bias   = summary.get("bias", "—")
posw   = summary.get("position_weight")
comps  = summary.get("components", {}) or {}
btstats = summary.get("backtest_stats", {}) or {}

st.markdown(f"""
<div class="topbar">
    <div>BTC&nbsp;&lt;CRNCY&gt;&nbsp;&nbsp;MACRO LIQUIDITY TERMINAL &nbsp;·&nbsp; v0.1</div>
    <div class="right">{now}</div>
</div>
<div class="fnstrip">
    <span class="fnkey">F1</span><span class="fnlbl">REGIME</span>
    <span class="fnkey">F2</span><span class="fnlbl">MACRO</span>
    <span class="fnkey">F3</span><span class="fnlbl">RISK</span>
    <span class="fnkey">F4</span><span class="fnlbl">FLOWS</span>
    <span class="fnkey">F5</span><span class="fnlbl">LEAD/LAG</span>
    <span class="fnkey">F6</span><span class="fnlbl">ALERTS</span>
    <span class="fnkey">F7</span><span class="fnlbl">BACKTEST</span>
</div>
<div class="statusbar">
    <div><b>USER</b> <span>TRADERGJ148@AETHEION</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>FRAMEWORK</b> <span>CAPITAL FLOWS RESEARCH</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>MODE</b> <span>MONITOR</span></div>
    <div><b>DATA AS-OF</b> <span>{asof}</span></div>
</div>
""", unsafe_allow_html=True)


# ============================================================
#  TRADING SESSIONS PANEL (NY time / ET)
# ============================================================
SESSIONS = [
    {"label": "ASIA RANGE",   "start": 20.0, "end": 24.0, "color": "#7E8C9B"},
    {"label": "LONDON",       "start":  2.0, "end":  5.0, "color": "#FF6B8A"},
    {"label": "NEW YORK AM",  "start":  9.5, "end": 12.0, "color": "#88E090"},
    {"label": "NEW YORK PM",  "start": 13.5, "end": 16.0, "color": "#C8A2D6"},
]

def _render_sessions_panel():
    try:
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.now(timezone.utc)
    hour_dec = now_et.hour + now_et.minute / 60.0
    current_pct = hour_dec / 24.0 * 100.0

    active = None
    for s in SESSIONS:
        if s["start"] <= hour_dec < s["end"]:
            active = s["label"]; break

    def _hm(h):
        hr = int(h); mn = int(round((h - hr) * 60))
        return f"{hr:02d}:{mn:02d}"

    rows_html = ""
    for s in SESSIONS:
        start_pct = s["start"] / 24 * 100
        width_pct = (s["end"] - s["start"]) / 24 * 100
        mid_pct   = start_pct + width_pct / 2
        is_active = (active == s["label"])
        active_cls = "active" if is_active else ""
        time_text = f"{_hm(s['start'])} – {_hm(s['end'] if s['end']<24 else 0)}"
        badge = ('<div class="session-active-badge">ACTIVE</div>' if is_active
                 else '<div class="session-pending-badge">—</div>')
        rows_html += (
            f'<div class="session-row {active_cls}" style="color:{s["color"]};">'
            f'<div class="session-label">{s["label"]}</div>'
            f'<div class="session-track">'
            f'<div class="session-block" style="left:{start_pct:.2f}%;width:{width_pct:.2f}%;background:{s["color"]};"></div>'
            f'<div class="session-time-text" style="left:{mid_pct:.2f}%;">{time_text}</div>'
            f'</div>'
            f'{badge}'
            f'</div>'
        )

    axis = ('<div class="session-axis">'
            '<span>00:00</span><span>06:00</span>'
            '<span>12:00</span><span>18:00</span><span>00:00</span></div>')

    # ---------- OPENING-SOON countdown ----------
    # Look for the next session whose start is within +/-15 minutes
    OPENING_WINDOW_MIN = 15
    opening_soon = None
    for s in SESSIONS:
        delta_min = (s["start"] - hour_dec) * 60.0
        if 0 <= delta_min <= OPENING_WINDOW_MIN:
            opening_soon = (s["label"], delta_min, s["color"])
            break
    if active:
        active_text = f"  ·  {active} ACTIVE"
    elif opening_soon:
        lbl, mins, col = opening_soon
        m = int(mins); s_ = int((mins - m) * 60)
        active_text = (
            f"  ·  <span style=\"color:{col};font-weight:700;\">{lbl} OPENS IN "
            f"{m:02d}:{s_:02d}</span>"
        )
    else:
        active_text = "  ·  Off-hours"
    # ---- VOLUME INTENSITY OVERLAP ZONES ----
    # Each zone: (start_hour, end_hour, label, intensity_0_to_1, color)
    VOL_ZONES = [
        ( 0.0,  2.0, "ASIA TAIL",        0.30, "#3F4A55"),   # post-Tokyo, no overlap
        ( 2.0,  8.0, "TOKYO+LONDON",     0.55, "#5A8C9B"),   # mid-overlap
        ( 8.0, 12.0, "LONDON+NY  ★PEAK", 1.00, "#FA8B1F"),   # highest volume
        (12.0, 13.5, "NY LUNCH",         0.70, "#C8A2D6"),   # London trailing
        (13.5, 16.0, "NY MAIN",          0.85, "#88E090"),   # NY afternoon
        (16.0, 20.0, "POST-NY GAP",      0.25, "#2A2A2A"),   # quiet, low vol
        (20.0, 24.0, "ASIA OPEN",        0.50, "#7E8C9B"),   # Tokyo/Sydney start
    ]
    # find current vol zone
    current_vol = next((z for z in VOL_ZONES if z[0] <= hour_dec < z[1]), None)
    cur_label = current_vol[2] if current_vol else "—"
    cur_intensity = current_vol[3] if current_vol else 0
    cur_color = current_vol[4] if current_vol else "#444"

    vol_zones_html = ""
    for s, e, lbl, intensity, color in VOL_ZONES:
        start_pct = s / 24 * 100
        width_pct = (e - s) / 24 * 100
        mid_pct = start_pct + width_pct / 2
        opacity = 0.35 + intensity * 0.65   # 0.35..1.00
        is_now = current_vol is not None and current_vol[0] == s
        glow = "box-shadow: 0 0 8px currentColor;" if is_now else ""
        vol_zones_html += (
            f'<div class="vol-zone" style="left:{start_pct:.2f}%;width:{width_pct:.2f}%;'
            f'background:{color};opacity:{opacity:.2f};color:{color};{glow}"></div>'
            f'<div class="vol-zone-text" style="left:{mid_pct:.2f}%;">{lbl}</div>'
        )

    # intensity meter for the current zone
    if cur_intensity >= 0.85:
        meter_text, meter_color = "PEAK VOL", "#FA8B1F"
    elif cur_intensity >= 0.65:
        meter_text, meter_color = "HIGH VOL", "#88E090"
    elif cur_intensity >= 0.40:
        meter_text, meter_color = "MED VOL",  "#C8A2D6"
    else:
        meter_text, meter_color = "LOW VOL",  "#7E8C9B"

    vol_intensity_html = (
        f'<div class="vol-intensity-row">'
        f'<div class="vol-intensity-label">VOL INTENSITY</div>'
        f'<div class="vol-intensity-track">'
        f'{vol_zones_html}'
        f'</div>'
        f'<div class="vol-intensity-meter" style="background:{meter_color};color:#000;">{meter_text}</div>'
        f'</div>'
    )

    # ---------- LOW LIQUIDITY warning strip ----------
    low_warn_html = ""
    if cur_intensity < 0.40:
        low_warn_html = (
            f'<div style="background:rgba(255,235,59,0.10);'
            f'border:1px solid {YELLOW};color:{YELLOW};'
            f'padding:4px 10px;font-size:10px;letter-spacing:0.12em;'
            f'font-weight:700;margin-bottom:8px;text-align:center;">'
            f'⚠️  LOW LIQUIDITY WINDOW ({cur_label}) — WIDER SPREADS · FALSE BREAKOUTS LIKELY · DEFER FRESH ENTRIES'
            f'</div>'
        )

    # single dashed NOW-line spanning every row (var carries fraction 0..1)
    now_line_html = (
        f'<div class="sessions-now-line" '
        f'style="--now-pct:{current_pct/100.0:.4f};"></div>'
    )
    panel_html = (
        f'<div class="sessions-panel">'
        f'<div class="sessions-title">'
        f'<span>TRADING SESSIONS &amp; VOL INTENSITY — NY TIME (ET)</span>'
        f'<span class="now-badge">NOW: {now_et.strftime("%H:%M")} ET'
        f'  ·  {cur_label} ({meter_text})'
        f'  {active_text}</span>'
        f'</div>'
        f'<div class="sessions-rows">'
        f'  {vol_intensity_html}'
        f'  {rows_html}'
        f'  {now_line_html}'
        f'</div>'
        f'{axis}'
        f'</div>'
        f'{low_warn_html}'
    )
    st.markdown(panel_html, unsafe_allow_html=True)

_render_sessions_panel()


# ============================================================
#  HEADLINE — bias banner + 4 gauges
# ============================================================
bias_color = {
    "STRONG BULLISH": GREEN, "BULLISH": GREEN,
    "NEUTRAL": ORANGE,
    "BEARISH": RED, "STRONG BEARISH": RED,
}.get(bias, ORANGE)

def _bias_word(v):
    if v is None or (isinstance(v, float) and v != v):
        return "—", TEXT_DIM
    if v >  0.50:  return "STRONG BULL", GREEN
    if v >  0.20:  return "BULLISH",     GREEN
    if v > -0.20:  return "NEUTRAL",     ORANGE
    if v > -0.50:  return "BEARISH",     RED
    return "STRONG BEAR", RED

def _strength_word(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    a = abs(v)
    if a > 0.50: return "STRONG"
    if a > 0.20: return "MODERATE"
    if a > 0.05: return "WEAK"
    return "FLAT"

def _cell_html(label, score, is_composite=False, posw=None):
    if score is None or (isinstance(score, float) and score != score):
        score_str = "—"
        bias_word, bias_color = "—", TEXT_DIM
        marker_pct = 50.0
        strength = ""
    else:
        score_str = f"{score:+.3f}"
        bias_word, bias_color = _bias_word(score)
        marker_pct = max(0, min(100, (score + 1) * 50))
        strength = _strength_word(score)
    cls = "regime-cell composite" if is_composite else "regime-cell"
    pos_html = ""
    if is_composite and posw is not None and isinstance(posw, (int, float)):
        pos_html = f'<div class="rc-pos">POS {posw*100:+.0f}% LONG</div>'
    border_color = ORANGE if is_composite else bias_color
    return (
        f'<div class="{cls}" style="border-color:{border_color};">'
        f'<div class="rc-label">{label}</div>'
        f'<div class="rc-bias" style="color:{bias_color};">{bias_word}</div>'
        f'<div class="rc-score" style="color:{bias_color};">{score_str}</div>'
        f'<div class="rc-bar">'
        f'<div class="rc-marker" style="left:{marker_pct:.1f}%;background:{bias_color};box-shadow:0 0 4px {bias_color};"></div>'
        f'</div>'
        f'<div class="rc-strength">{strength}</div>'
        f'{pos_html}'
        f'</div>'
    )

strip_html = (
    f'<div class="regime-strip">'
    f'{_cell_html("REGIME COMPOSITE", regime, is_composite=True, posw=posw)}'
    f'{_cell_html("MACRO",      comps.get("macro"))}'
    f'{_cell_html("RISK CURVE", comps.get("risk_curve"))}'
    f'{_cell_html("MICRO",      comps.get("micro"))}'
    f'{_cell_html("LEAD/LAG",   comps.get("leadlag"))}'
    f'{_cell_html("OPTIONS",    comps.get("options"))}'
    f'</div>'
)
st.markdown(strip_html, unsafe_allow_html=True)


# ============================================================
#  KEY-VALUE STATS PANEL
# ============================================================
def kv_html(rows):
    inner = "".join([
        f"<div class='kv'><span class='k'>{k}</span>"
        f"<span class='v {cls}'>{v}</span></div>"
        for k, v, cls in rows
    ])
    return f"<div class='panel'><div class='panel-title'>STRATEGY VITALS</div>{inner}</div>"


def fmt_pct(x):
    return f"{x*100:+.2f}%" if isinstance(x, (int, float)) else "—"


def fmt_num(x, dp=3):
    return f"{x:+.{dp}f}" if isinstance(x, (int, float)) else "—"


def pos_class(v):
    if isinstance(v, (int, float)):
        if v > 0:  return "pos"
        if v < 0:  return "neg"
    return "neu"


stats_rows = [
    ("REGIME SCORE",         fmt_num(regime),                                pos_class(regime)),
    ("MACRO COMPONENT",      fmt_num(comps.get("macro")),                    pos_class(comps.get("macro"))),
    ("RISK CURVE",           fmt_num(comps.get("risk_curve")),               pos_class(comps.get("risk_curve"))),
    ("MICRO COMPONENT",      fmt_num(comps.get("micro")),                    pos_class(comps.get("micro"))),
    ("LEAD/LAG",             fmt_num(comps.get("leadlag")),                  pos_class(comps.get("leadlag"))),
    ("EXTREMES",             fmt_num(comps.get("extremes")),                 pos_class(comps.get("extremes"))),
    ("STRATEGY RETURN",      fmt_pct(btstats.get("strategy_total_return")),  pos_class(btstats.get("strategy_total_return"))),
    ("BUY-HOLD RETURN",      fmt_pct(btstats.get("buyhold_total_return")),   pos_class(btstats.get("buyhold_total_return"))),
    ("STRATEGY SHARPE",      fmt_num(btstats.get("strategy_sharpe"), 2),     pos_class(btstats.get("strategy_sharpe"))),
    ("STRATEGY MAX DD",      fmt_pct(btstats.get("strategy_max_drawdown")),  pos_class(btstats.get("strategy_max_drawdown"))),
    ("BUY-HOLD MAX DD",      fmt_pct(btstats.get("buyhold_max_drawdown")),   pos_class(btstats.get("buyhold_max_drawdown"))),
    ("BACKTEST DAYS",        f"{btstats.get('n_days','—')}",                 "neu"),
]

left, right = st.columns([3, 1])

with left:
    regime_df = load("regime_score")
    if not regime_df.empty:
        col = regime_df.columns[0]
        df = regime_df.rename(columns={col: "REGIME"}).tail(750)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["REGIME"], mode="lines",
            line=dict(color=ORANGE, width=1.6),
            fill="tozeroy", fillcolor="rgba(250,139,31,0.12)",
            name="REGIME",
        ))
        fig.add_hrect(y0=0.2, y1=1, fillcolor=GREEN, opacity=0.05, line_width=0)
        fig.add_hrect(y0=-1, y1=-0.2, fillcolor=RED, opacity=0.05, line_width=0)
        fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
        fig.update_layout(**bbg_layout(title="COMPOSITE REGIME SCORE — 750D",
                                       height=320))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})
    else:
        st.info("Run `python -m src.pipeline` to populate data.")

with right:
    st.markdown(kv_html(stats_rows), unsafe_allow_html=True)


# ============================================================
#  TABS — one per layer
# ============================================================
tab_macro, tab_risk, tab_micro, tab_opt, tab_ll, tab_alerts, tab_bt = st.tabs(
    ["MACRO", "RISK CURVE", "BTC FLOWS / MICRO", "OPTIONS", "LEAD/LAG", "ALERTS", "BACKTEST"]
)

with tab_macro:
    raw = load("macro_raw")
    if not raw.empty:
        ms = load("macro_score")
        c_a, c_b = st.columns([2, 1])
        with c_a:
            sm = small_multiples(raw.tail(2500),
                ["real_yield_10y","breakeven_5y","fed_balance_sheet",
                 "dxy","m2_us","rrp"],
                "MACRO LIQUIDITY COMPONENTS",
                ncols=2, panel_height=160)
            if sm is not None:
                st.plotly_chart(sm, width='stretch',
                                config={"displayModeBar": False})
        with c_b:
            if not ms.empty:
                st.plotly_chart(line_panel(ms.tail(1000), "MACRO SCORE"),
                                width='stretch',
                                config={"displayModeBar": False})

        if {"fed_balance_sheet","rrp","tga"}.issubset(raw.columns):
            net = (raw["fed_balance_sheet"] - raw["rrp"] - raw["tga"]).rename("NET_LIQ")
            st.plotly_chart(
                line_panel(net.tail(2000).to_frame(),
                           "FED NET LIQUIDITY (WALCL − RRP − TGA)",
                           palette=[ORANGE]),
                width='stretch', config={"displayModeBar": False})

        # ---------- GLOBAL LIQUIDITY (Layer 1B) ----------
        gnl = load("global_net_liquidity")
        if not gnl.empty and "global_net_liquidity_usd_bn" in gnl.columns:
            st.markdown(
                "<h3 style='margin-top:18px;'>GLOBAL CENTRAL BANK LIQUIDITY</h3>",
                unsafe_allow_html=True)

            # ---- Aggregated Global Net Liquidity line ----
            agg = gnl["global_net_liquidity_usd_bn"].dropna().tail(2500)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=agg.index, y=agg.values, mode="lines",
                line=dict(color=ORANGE, width=1.6),
                fill="tozeroy", fillcolor="rgba(250,139,31,0.10)",
                name="GLOBAL NET LIQUIDITY",
            ))
            fig.update_layout(**bbg_layout(
                title="GLOBAL NET LIQUIDITY — SUM OF CB ASSETS IN USD ($BN)",
                height=300))
            fig.update_yaxes(title=dict(text="USD BILLIONS",
                                        font=dict(color=ORANGE,size=10)))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

            # ---- Per-CB stacked breakdown ----
            cb_cols = [c for c in gnl.columns
                       if c.endswith("_usd_bn")
                       and c != "global_net_liquidity_usd_bn"]
            if cb_cols:
                fig = go.Figure()
                cb_palette = {"fed_usd_bn":  ORANGE,
                              "ecb_usd_bn":  CYAN,
                              "boj_usd_bn":  GREEN,
                              "boe_usd_bn":  YELLOW,
                              "boc_usd_bn":  MAGENTA,
                              "rba_usd_bn":  "#FF8800",
                              "rbnz_usd_bn": "#9B7DFF",
                              "pboc_usd_bn": "#FF44FF"}
                cb_label   = {"fed_usd_bn":  "FED",
                              "ecb_usd_bn":  "ECB",
                              "boj_usd_bn":  "BOJ",
                              "boe_usd_bn":  "BOE",
                              "boc_usd_bn":  "BoC",
                              "rba_usd_bn":  "RBA",
                              "rbnz_usd_bn": "RBNZ",
                              "pboc_usd_bn": "PBOC*"}
                df_stack = gnl[cb_cols].tail(2500)
                for c in cb_cols:
                    fig.add_trace(go.Scatter(
                        x=df_stack.index, y=df_stack[c],
                        mode="lines", stackgroup="cb",
                        name=cb_label.get(c, c.upper()),
                        line=dict(color=cb_palette.get(c, ORANGE), width=0.8),
                    ))
                fig.update_layout(**bbg_layout(
                    title="PER-CB CONTRIBUTION TO GLOBAL LIQUIDITY  (USD $BN, STACKED)",
                    height=320))
                fig.update_yaxes(title=dict(text="USD BILLIONS",
                                            font=dict(color=ORANGE,size=10)))
                st.plotly_chart(fig, width='stretch',
                                config={"displayModeBar": False})

            # ---- Latest snapshot panel ----
            latest = gnl.iloc[-1]
            rows_html = []
            for c in cb_cols:
                val = latest.get(c)
                if isinstance(val,(int,float)) and val == val:
                    rows_html.append(
                        f"<div class='kv'><span class='k'>{cb_label.get(c, c.upper())}</span>"
                        f"<span class='v neu'>{val:,.0f} $BN</span></div>")
            agg_val = latest.get("global_net_liquidity_usd_bn")
            if isinstance(agg_val,(int,float)) and agg_val == agg_val:
                rows_html.append(
                    f"<div class='kv' style='border-top:1px solid {ORANGE_DIM};margin-top:4px;padding-top:6px;'>"
                    f"<span class='k' style='font-weight:700;'>TOTAL GLOBAL</span>"
                    f"<span class='v' style='color:{ORANGE};font-weight:700;'>"
                    f"{agg_val:,.0f} $BN</span></div>")
            if rows_html:
                st.markdown(
                    f"<div class='panel'><div class='panel-title'>"
                    f"GLOBAL CB SNAPSHOT</div>"
                    f"{''.join(rows_html)}"
                    f"<div style='font-size:9px;color:{TEXT_DIM};margin-top:6px;'>"
                    f"* PBOC value is a proxy via M3 monetary aggregate "
                    f"(true PBOC balance sheet not free / available real-time)."
                    f"</div></div>",
                    unsafe_allow_html=True)

        # ---------- FX MAJORS DASHBOARD (Layer 1C) ----------
        if not raw.empty:
            fx_cols = [c for c in
                       ("dxy","eurusd","usdjpy","gbpusd","usdcad","audusd","nzdusd","usdcnh")
                       if c in raw.columns]
            if fx_cols:
                st.markdown(
                    "<h3 style='margin-top:18px;'>FX MAJORS (LIQUIDITY TRANSMISSION)</h3>",
                    unsafe_allow_html=True)
                sm = small_multiples(raw.tail(1500), fx_cols,
                    "FX MAJORS — DAILY",
                    ncols=2, panel_height=140)
                if sm is not None:
                    st.plotly_chart(sm, width='stretch',
                                    config={"displayModeBar": False})

    else:
        st.info("Macro data not yet pulled. Run `python -m src.pipeline`.")

with tab_risk:
    rc = load("risk_curve_raw")
    rs = load("risk_curve_score")
    if not rc.empty:
        c_a, c_b = st.columns(2)
        with c_a:
            sm = small_multiples(rc.tail(1500),
                ["hy_oas","vix","arkk","spy","iwm","soxx"],
                "EQUITY/CREDIT RISK BAROMETERS",
                ncols=2, panel_height=140)
            if sm is not None:
                st.plotly_chart(sm, width='stretch',
                                config={"displayModeBar": False})
        with c_b:
            if not rs.empty:
                st.plotly_chart(line_panel(rs.tail(1000), "RISK CURVE SCORE"),
                                width='stretch',
                                config={"displayModeBar": False})
    else:
        st.info("Risk curve data not yet pulled.")

with tab_micro:
    cA, cB = st.columns(2)
    with cA:
        etf = load("etf_flows")
        if not etf.empty and "Total" in etf.columns:
            st.plotly_chart(bar_panel(etf["Total"].tail(60),
                                      "BTC SPOT ETF NET FLOWS — $M (60D)"),
                            width='stretch',
                            config={"displayModeBar": False})
        funding = load("funding")
        if not funding.empty:
            # === Per-exchange + annualised funding ===
            exch_cols = [c for c in funding.columns
                         if c in ("binance", "bybit", "okx", "funding_blend")]
            if exch_cols:
                # multiply 8h funding rate by 365*3 = 1095 to express APR (%)
                annu = funding[exch_cols].tail(180) * 1095 * 100
                fig = go.Figure()
                colors = {"binance": ORANGE, "bybit": CYAN, "okx": GREEN,
                          "funding_blend": YELLOW}
                for c in exch_cols:
                    fig.add_trace(go.Scatter(
                        x=annu.index, y=annu[c], mode="lines",
                        line=dict(color=colors.get(c, ORANGE),
                                  width=2 if c == "funding_blend" else 1),
                        name=c.upper(),
                    ))
                fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
                fig.add_hrect(y0=10, y1=100, fillcolor=RED, opacity=0.06,
                              line_width=0)
                fig.add_hrect(y0=-100, y1=-10, fillcolor=GREEN, opacity=0.06,
                              line_width=0)
                fig.update_layout(**bbg_layout(
                    title="PERP FUNDING — ANNUALISED %  (180D)",
                    height=240))
                fig.update_yaxes(title=dict(text="ANN. %",
                                            font=dict(color=ORANGE,size=10)))
                st.plotly_chart(fig, width='stretch',
                                config={"displayModeBar": False})

            # === Z-score panel with ±2σ alert bands ===
            if "funding_blend" in funding.columns:
                f = funding["funding_blend"].dropna()
                if len(f) > 30:
                    mu = f.rolling(60, min_periods=20).mean()
                    sd = f.rolling(60, min_periods=20).std()
                    z = ((f - mu) / sd.replace(0, float("nan"))).tail(180)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=z.index, y=z.values, mode="lines",
                        line=dict(color=ORANGE, width=1.5), name="z"))
                    fig.add_hline(y=2,  line_color=RED,   line_width=1, line_dash="dash")
                    fig.add_hline(y=-2, line_color=GREEN, line_width=1, line_dash="dash")
                    fig.add_hline(y=0,  line_color=ORANGE_DIM, line_width=0.7)
                    fig.add_hrect(y0=2, y1=5, fillcolor=RED, opacity=0.06, line_width=0)
                    fig.add_hrect(y0=-5,y1=-2,fillcolor=GREEN, opacity=0.06, line_width=0)
                    fig.update_layout(**bbg_layout(
                        title="FUNDING Z-SCORE  (60d window, ±2σ = extremes)",
                        height=200))
                    st.plotly_chart(fig, width='stretch',
                                    config={"displayModeBar": False})

            # === Cumulative funding paid (carry cost of being long all year) ===
            if "funding_blend" in funding.columns:
                f = funding["funding_blend"].dropna()
                # annualised continuously compounded
                cum = (f.tail(365) * 1095 * 100).cumsum() / 1095
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=cum.index, y=cum.values, mode="lines",
                    line=dict(color=ORANGE, width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(250,139,31,0.10)",
                    name="cumulative %",
                ))
                fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
                fig.update_layout(**bbg_layout(
                    title="CUMULATIVE FUNDING PAID  (long 1× since 365D, %)",
                    height=200))
                st.plotly_chart(fig, width='stretch',
                                config={"displayModeBar": False})
    with cB:
        oi = load("open_interest")
        if not oi.empty:
            st.plotly_chart(line_panel(oi.tail(180),
                                       "BINANCE BTC PERP OPEN INTEREST (USD)",
                                       palette=[GREEN]),
                            width='stretch',
                            config={"displayModeBar": False})
        dvol = load("dvol")
        if not dvol.empty:
            st.plotly_chart(line_panel(dvol.tail(365),
                                       "DERIBIT DVOL (BTC IMPLIED VOL)",
                                       palette=[CYAN]),
                            width='stretch',
                            config={"displayModeBar": False})

    ms = load("micro_score")
    if not ms.empty:
        st.plotly_chart(line_panel(ms.tail(1000), "MICROSTRUCTURE COMPOSITE",
                                   palette=[ORANGE]),
                        width='stretch',
                        config={"displayModeBar": False})

with tab_opt:
    """Layer 6: Options-derived vol outlook."""
    opt_summary = (summary.get("components", {}) or {}).get("options")
    opt_breakdown = (summary.get("components", {}) or {}).get("options_breakdown", {}) or {}

    # ----- header strip with three score readouts -----
    h1, h2, h3, h4 = st.columns([1, 1, 1, 1])
    with h1:
        st.markdown(
            f"<div class='panel'><div class='panel-title'>OPTIONS COMPOSITE</div>"
            f"<div style='font-size:24px;color:{ORANGE};text-align:center;font-weight:700;'>"
            f"{opt_summary:+.3f}</div></div>" if isinstance(opt_summary,(int,float))
            else "<div class='panel'><div class='panel-title'>OPTIONS COMPOSITE</div>"
                 "<div style='font-size:24px;color:#888;text-align:center;'>—</div></div>",
            unsafe_allow_html=True)
    for col, lbl, key in [(h2,"TERM","term"), (h3,"SKEW","skew"), (h4,"GEX","gex")]:
        with col:
            v = opt_breakdown.get(key)
            color = ORANGE if not isinstance(v,(int,float)) else (GREEN if v>0.2 else RED if v<-0.2 else ORANGE)
            disp = f"{v:+.3f}" if isinstance(v,(int,float)) else "—"
            st.markdown(
                f"<div class='panel'><div class='panel-title'>{lbl} SCORE</div>"
                f"<div style='font-size:22px;color:{color};text-align:center;font-weight:700;'>{disp}</div></div>",
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ----- Term structure + Skew curve side by side -----
    cA, cB = st.columns(2)
    with cA:
        term = load("options_term")
        if not term.empty and {"dte_days","atm_iv"}.issubset(term.columns):
            df = term.dropna(subset=["atm_iv","dte_days"]).sort_values("dte_days")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["dte_days"], y=df["atm_iv"]*100, mode="lines+markers",
                line=dict(color=ORANGE, width=2),
                marker=dict(color=ORANGE, size=8),
                name="ATM IV",
            ))
            fig.update_layout(**bbg_layout(
                title="ATM IV TERM STRUCTURE  (BTC, % vol)",
                height=320))
            fig.update_xaxes(title=dict(text="DAYS TO EXPIRY",font=dict(color=ORANGE,size=10)))
            fig.update_yaxes(title=dict(text="IMPLIED VOL %",font=dict(color=ORANGE,size=10)))
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("Run pipeline to populate term structure.")
    with cB:
        skew = load("options_skew")
        if not skew.empty and {"dte_days","iv_call25","iv_put25","iv_atm"}.issubset(skew.columns):
            df = skew.dropna().sort_values("dte_days")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_call25"]*100,
                mode="lines+markers", line=dict(color=GREEN,width=2), name="25d CALL"))
            fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_atm"]*100,
                mode="lines+markers", line=dict(color=ORANGE,width=2), name="ATM"))
            fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_put25"]*100,
                mode="lines+markers", line=dict(color=RED,width=2), name="25d PUT"))
            fig.update_layout(**bbg_layout(
                title="SKEW CURVE  (25d CALL / ATM / 25d PUT, % vol)",
                height=320))
            fig.update_xaxes(title=dict(text="DAYS TO EXPIRY",font=dict(color=ORANGE,size=10)))
            fig.update_yaxes(title=dict(text="IMPLIED VOL %",font=dict(color=ORANGE,size=10)))
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("Run pipeline to populate skew curve.")

    # ----- 25d skew (RR) per expiry — clipped to ≤180d for legibility -----
    if not skew.empty and "skew_25d" in skew.columns:
        df = skew.dropna(subset=["skew_25d","dte_days"]).sort_values("dte_days")
        df_short = df[df["dte_days"] <= 180].copy()   # focus where the action is
        if df_short.empty:
            df_short = df.head(8)                     # fallback if all > 180d

        fig = go.Figure()
        colors = [GREEN if v>=0 else RED for v in df_short["skew_25d"].values]
        fig.add_trace(go.Bar(
            x=df_short["dte_days"], y=df_short["skew_25d"]*100,
            marker_color=colors, marker_line_width=0,
            text=[f"{v*100:+.1f}" for v in df_short["skew_25d"].values],
            textposition="outside",
            textfont=dict(color=WHITE, size=9, family="JetBrains Mono"),
            hovertemplate="DTE %{x:.0f}d<br>RR %{y:+.2f} vol pts<extra></extra>",
        ))
        fig.update_layout(**bbg_layout(
            title="25-DELTA RISK REVERSAL ≤180D  (CALL_IV − PUT_IV, vol points)  +VE=GREED  -VE=FEAR",
            height=260))
        fig.update_xaxes(title=dict(text="DAYS TO EXPIRY",
                                     font=dict(color=ORANGE,size=10)))
        fig.update_yaxes(title=dict(text="RR  (vol pts)",
                                     font=dict(color=ORANGE,size=10)))
        fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    # ----- GEX by strike (bar chart, signed, with spot + pain zone) -----
    gex = load("options_gex_by_strike")
    if not gex.empty and {"strike","gex_usd_per_pct"}.issubset(gex.columns):
        gex_hist = load("options_gex_history")
        spot = (float(gex_hist["spot"].iloc[-1])
                if not gex_hist.empty and "spot" in gex_hist.columns else None)

        df = gex.sort_values("strike").copy()
        colors = [GREEN if v>=0 else RED for v in df["gex_usd_per_pct"].values]

        # ---- find dealer pain zone: contiguous run of negative GEX nearest spot ----
        pain_lo = pain_hi = None
        pain_strike = None
        if spot is not None and len(df) > 0:
            # focus on strikes within ±25% of spot
            near = df[(df["strike"] >= spot * 0.75) &
                      (df["strike"] <= spot * 1.25)]
            neg = near[near["gex_usd_per_pct"] < 0]
            if not neg.empty:
                pain_lo = float(neg["strike"].min())
                pain_hi = float(neg["strike"].max())
                # deepest negative-GEX strike (the actual magnet)
                pain_strike = float(
                    neg.loc[neg["gex_usd_per_pct"].idxmin(), "strike"])

        fig = go.Figure(go.Bar(
            x=df["strike"], y=df["gex_usd_per_pct"]/1e6,
            marker_color=colors, marker_line_width=0,
            hovertemplate="strike %{x:,.0f}<br>GEX %{y:+.2f} M$<extra></extra>"))

        # dealer pain zone (red translucent band)
        if pain_lo is not None:
            fig.add_vrect(
                x0=pain_lo, x1=pain_hi,
                fillcolor=RED, opacity=0.10, line_width=0,
                annotation_text=f"DEALER PAIN ZONE  {pain_lo:,.0f}–{pain_hi:,.0f}",
                annotation_position="top left",
                annotation=dict(font=dict(color=RED, size=10,
                                          family="JetBrains Mono")),
            )
        # deepest GEX strike marker
        if pain_strike is not None:
            fig.add_vline(
                x=pain_strike, line_color=RED, line_width=1.5, line_dash="dot",
                annotation_text=f"MAX-PAIN  {pain_strike:,.0f}",
                annotation_position="bottom",
                annotation=dict(font=dict(color=RED, size=10)),
            )

        fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
        if spot:
            fig.add_vline(x=spot, line_color=YELLOW, line_width=2,
                line_dash="dash",
                annotation_text=f"SPOT {spot:,.0f}",
                annotation_position="top",
                annotation=dict(font=dict(color=YELLOW, size=11)))

        fig.update_layout(**bbg_layout(
            title="GAMMA EXPOSURE BY STRIKE  ($M PER 1% SPOT MOVE)  [Option-B delta-bucketed]",
            height=340))
        fig.update_xaxes(title=dict(text="STRIKE  (USD)",
                                     font=dict(color=ORANGE,size=10)))
        fig.update_yaxes(title=dict(text="GEX  ($M / 1%)",
                                     font=dict(color=ORANGE,size=10)))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

        # ---- pain-zone summary panel ----
        if pain_lo is not None and spot is not None:
            in_pain = pain_lo <= spot <= pain_hi
            pain_color = RED if in_pain else GREEN
            pain_label = "INSIDE PAIN ZONE" if in_pain else "OUTSIDE PAIN ZONE"
            dist_to_max = abs(spot - pain_strike) / spot * 100 if pain_strike else 0
            st.markdown(
                f"<div class='panel'><div class='panel-title'>"
                f"DEALER GAMMA REGIME</div>"
                f"<div class='kv'><span class='k'>SPOT</span>"
                f"<span class='v neu'>{spot:,.0f}</span></div>"
                f"<div class='kv'><span class='k'>PAIN ZONE</span>"
                f"<span class='v neg'>{pain_lo:,.0f} – {pain_hi:,.0f}</span></div>"
                f"<div class='kv'><span class='k'>MAX-PAIN STRIKE</span>"
                f"<span class='v neg'>{pain_strike:,.0f}</span></div>"
                f"<div class='kv'><span class='k'>DISTANCE FROM MAX-PAIN</span>"
                f"<span class='v neu'>{dist_to_max:+.2f}%</span></div>"
                f"<div class='kv'><span class='k'>STATUS</span>"
                f"<span class='v' style='color:{pain_color};font-weight:700;'>{pain_label}</span></div>"
                f"</div>",
                unsafe_allow_html=True)

    # ----- GEX history time series -----
    gex_hist = load("options_gex_history")
    if not gex_hist.empty and "gex_total" in gex_hist.columns:
        df = gex_hist.dropna(subset=["gex_total"]).copy()
        if "asof" in df.columns:
            df["asof"] = pd.to_datetime(df["asof"])
            df = df.sort_values("asof")
        cA, cB = st.columns([2,1])
        with cA:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.get("asof", df.index), y=df["gex_total"]/1e6,
                mode="lines+markers",
                line=dict(color=ORANGE, width=2),
                marker=dict(color=ORANGE, size=6),
                name="GEX total",
            ))
            fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
            fig.update_layout(**bbg_layout(
                title="GEX HISTORY  ($M per 1% spot)  [accumulating from first run]",
                height=260))
            fig.update_yaxes(title=dict(text="GEX TOTAL  ($M / 1%)",font=dict(color=ORANGE,size=10)))
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        with cB:
            st.markdown("<div class='panel'><div class='panel-title'>GEX REGIME GUIDE</div>"
                f"<div style='color:{WHITE};font-size:11px;line-height:1.6;'>"
                f"<span style='color:{GREEN}'>POSITIVE GEX</span><br>"
                f"&nbsp;&nbsp;dealers long γ → SELL rallies, BUY dips<br>"
                f"&nbsp;&nbsp;<b>vol-suppressing, mean-reverting</b><br><br>"
                f"<span style='color:{RED}'>NEGATIVE GEX</span><br>"
                f"&nbsp;&nbsp;dealers short γ → BUY rallies, SELL dips<br>"
                f"&nbsp;&nbsp;<b>vol-amplifying, trend-following</b><br><br>"
                f"<span style='color:{YELLOW}'>ZERO CROSS</span><br>"
                f"&nbsp;&nbsp;regime change → vol regime breaks"
                f"</div></div>", unsafe_allow_html=True)

    # ----- OI heatmap (strike x expiry) -----
    chain = load("options_chain_latest")
    if not chain.empty and {"strike","expiry","type","open_interest"}.issubset(chain.columns):
        # filter to sensible strike range around spot
        gex_hist2 = load("options_gex_history")
        spot = float(gex_hist2["spot"].iloc[-1]) if not gex_hist2.empty and "spot" in gex_hist2.columns else float(chain["strike"].median())
        lo, hi = spot * 0.5, spot * 1.7
        df = chain[(chain["strike"] >= lo) & (chain["strike"] <= hi)].copy()
        df["expiry_str"] = pd.to_datetime(df["expiry"]).dt.strftime("%d%b%y")
        # keep only first 8 expiries for legibility
        first_expiries = sorted(df["expiry_str"].unique(), key=lambda s: pd.to_datetime(s, format="%d%b%y"))[:8]
        df = df[df["expiry_str"].isin(first_expiries)]

        cA, cB = st.columns(2)
        for col, opt_type, label, cmap in [(cA, "C", "CALLS", "Greens"), (cB, "P", "PUTS", "Reds")]:
            with col:
                sub = df[df["type"] == opt_type]
                if sub.empty: continue
                pivot = sub.pivot_table(index="strike", columns="expiry_str",
                                        values="open_interest", aggfunc="sum").fillna(0)
                # reorder columns by chronological expiry
                pivot = pivot[[e for e in first_expiries if e in pivot.columns]]
                fig = go.Figure(go.Heatmap(
                    z=pivot.values, x=pivot.columns, y=pivot.index,
                    colorscale=cmap, showscale=True,
                    hovertemplate="strike %{y:,.0f}<br>expiry %{x}<br>OI %{z:,.0f}<extra></extra>",
                ))
                fig.update_layout(**bbg_layout(
                    title=f"{label} OPEN INTEREST  (contracts, strike × expiry)",
                    height=380))
                fig.update_xaxes(title=dict(text="EXPIRY",font=dict(color=ORANGE,size=10)))
                fig.update_yaxes(title=dict(text="STRIKE",font=dict(color=ORANGE,size=10)))
                if spot:
                    fig.add_hline(y=spot, line_color=YELLOW, line_width=1.5,
                        line_dash="dash")
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


with tab_ll:
    ll = load("leadlag_raw")
    lls = load("leadlag_score")
    if not ll.empty:
        cols = [c for c in ("mstr","coin","mara","riot","clsk","btc_cme")
                if c in ll.columns]
        if cols:
            norm = ll[cols].dropna()
            norm = norm / norm.iloc[0]
            st.plotly_chart(line_panel(norm.tail(750),
                "PROXY UNIVERSE — INDEXED TO 100"),
                width='stretch', config={"displayModeBar": False})
    if not lls.empty:
        st.plotly_chart(line_panel(lls.tail(1000), "LEAD/LAG SCORE",
                                   palette=[ORANGE]),
                        width='stretch',
                        config={"displayModeBar": False})

with tab_alerts:
    alerts = load("alerts")
    st.markdown('<div class="panel"><div class="panel-title">'
                'POSITIONING-EXTREME TRIGGERS</div>', unsafe_allow_html=True)
    if alerts.empty:
        st.markdown(f"<div class='kv'><span class='k'>STATUS</span>"
                    f"<span class='v neu'>NO DATA</span></div>",
                    unsafe_allow_html=True)
    else:
        latest = alerts.iloc[-1]
        for k, v in latest.items():
            if isinstance(v, bool):
                cls = "neg" if v else "pos"
                state = "TRIGGERED" if v else "OK"
                st.markdown(f"<div class='kv'><span class='k'>{k.upper()}</span>"
                            f"<span class='v {cls}'>{state}</span></div>",
                            unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_bt:
    bt = load("backtest")
    if not bt.empty and {"equity", "bh_equity"}.issubset(bt.columns):
        df = bt[["equity", "bh_equity"]].rename(
            columns={"equity": "STRATEGY", "bh_equity": "BUY_HOLD"}
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["STRATEGY"], mode="lines",
            name="STRATEGY", line=dict(color=ORANGE, width=1.6)))
        fig.add_trace(go.Scatter(x=df.index, y=df["BUY_HOLD"], mode="lines",
            name="BUY_HOLD", line=dict(color=CYAN, width=1.0)))
        fig.update_layout(**bbg_layout(
            title="EQUITY CURVE — STRATEGY VS BUY-HOLD", height=380))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})
        if btstats:
            st.markdown('<div class="panel"><div class="panel-title">'
                        'BACKTEST STATS</div>', unsafe_allow_html=True)
            for k, v in btstats.items():
                if isinstance(v, float):
                    if "return" in k or "drawdown" in k:
                        s = f"{v*100:+.2f}%"
                    else:
                        s = f"{v:+.3f}"
                    cls = pos_class(v)
                else:
                    s = str(v); cls = "neu"
                st.markdown(f"<div class='kv'><span class='k'>{k.upper()}</span>"
                            f"<span class='v {cls}'>{s}</span></div>",
                            unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No backtest yet — run `python -m src.pipeline`.")


st.markdown(f"""
<div style='text-align:center; color:{TEXT_DIM}; font-size:10px;
            margin-top:14px; padding-top:6px; border-top:1px solid {ORANGE_DIM};'>
    <span style="color:{ORANGE}">SOURCES:</span>
    FRED · YAHOO · COINGECKO · BINANCE · BYBIT · DERIBIT · FARSIDE
    &nbsp;|&nbsp; FREE / PUBLIC APIs &nbsp;|&nbsp;
    <span style="color:{YELLOW}">EDUCATIONAL — NOT INVESTMENT ADVICE</span>
</div>
""", unsafe_allow_html=True)
