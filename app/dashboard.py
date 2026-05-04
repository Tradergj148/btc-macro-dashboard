"""Bloomberg-Terminal styled Streamlit dashboard.

Run:    streamlit run app/dashboard.py
Refresh data:  python -m src.pipeline
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
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
    <div><b>USER</b> <span>GUILLE@AETHEION</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>FRAMEWORK</b> <span>CAPITAL FLOWS RESEARCH</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>MODE</b> <span>MONITOR</span></div>
    <div><b>DATA AS-OF</b> <span>{asof}</span></div>
</div>
""", unsafe_allow_html=True)


# ============================================================
#  HEADLINE — bias banner + 4 gauges
# ============================================================
bias_color = {
    "STRONG BULLISH": GREEN, "BULLISH": GREEN,
    "NEUTRAL": ORANGE,
    "BEARISH": RED, "STRONG BEARISH": RED,
}.get(bias, ORANGE)

c1, c2, c3, c4, c5 = st.columns([1.3, 1, 1, 1, 1])

with c1:
    sc_str = f"{regime:+.3f}" if isinstance(regime, (int, float)) else "—"
    pw_str = f"{posw*100:+.0f}%" if isinstance(posw, (int, float)) else "—"
    st.markdown(f"""
    <div class="bias-banner">
        <div class="value" style="color:{bias_color};">{bias}</div>
        <div class="sub">SCORE <b style="color:{bias_color}">{sc_str}</b>
            &nbsp;·&nbsp; POS&nbsp;<b style="color:{bias_color}">{pw_str}</b></div>
    </div>
    """, unsafe_allow_html=True)

with c2: st.plotly_chart(gauge(comps.get("macro"),      "MACRO"),       width='stretch', config={"displayModeBar": False})
with c3: st.plotly_chart(gauge(comps.get("risk_curve"), "RISK CURVE"),  width='stretch', config={"displayModeBar": False})
with c4: st.plotly_chart(gauge(comps.get("micro"),      "MICRO"),       width='stretch', config={"displayModeBar": False})
with c5: st.plotly_chart(gauge(comps.get("leadlag"),    "LEAD/LAG"),    width='stretch', config={"displayModeBar": False})


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
tab_macro, tab_risk, tab_micro, tab_ll, tab_alerts, tab_bt = st.tabs(
    ["MACRO", "RISK CURVE", "BTC FLOWS / MICRO", "LEAD/LAG", "ALERTS", "BACKTEST"]
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
        if not funding.empty and "funding_blend" in funding.columns:
            st.plotly_chart(line_panel(funding[["funding_blend"]].tail(180),
                                       "PERP FUNDING BLENDED (180D)",
                                       palette=[ORANGE]),
                            width='stretch',
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
