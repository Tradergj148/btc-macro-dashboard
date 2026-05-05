"""Compass — BTC Macro→Micro liquidity compass landing page.

Run:    streamlit run app/Compass.py
Refresh data:  python -m src.pipeline

This is the synthesis view. The 6-cell regime strip in the top chrome shows
where we are; this page expands it with: bias banner, 750-day composite
trajectory, strategy vitals KV table, and the sessions panel.
"""
from __future__ import annotations

# Path bootstrap (must run before any _shared import) ──────────────────
import sys
from pathlib import Path
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# ──────────────────────────────────────────────────────────────────────

import plotly.graph_objects as go
import streamlit as st

from _shared.page    import setup_page
from _shared.loaders import load
from _shared.charts  import (
    bbg_layout, kv_html, fmt_pct, fmt_num, pos_class,
)
from _shared.style   import ORANGE, ORANGE_DIM, GREEN, RED
from _shared.sessions import render_sessions_panel

summary = setup_page("Compass")

# Pull synthesis values up front
regime  = summary.get("regime_score")
bias    = summary.get("bias", "—")
posw    = summary.get("position_weight")
comps   = summary.get("components", {}) or {}
btstats = summary.get("backtest_stats", {}) or {}

# ============================================================
#  Sessions panel (NY ET clock + vol intensity)
# ============================================================
render_sessions_panel()


# ============================================================
#  Bias banner — one-line decisive read
# ============================================================
bias_color = {
    "STRONG BULLISH": GREEN, "BULLISH": GREEN,
    "NEUTRAL": ORANGE,
    "BEARISH": RED, "STRONG BEARISH": RED,
}.get(bias, ORANGE)

st.markdown(f"""
<div class="bias-banner">
    <div class="value" style="color:{bias_color};">{bias}</div>
    <div class="sub">REGIME SCORE <b>{fmt_num(regime)}</b>
        &nbsp;·&nbsp; SUGGESTED POS <b>{posw*100:+.0f}%</b>
        &nbsp;·&nbsp; FRAMEWORK <b>CAPITAL FLOWS RESEARCH</b></div>
</div>
""" if isinstance(posw, (int, float)) else f"""
<div class="bias-banner">
    <div class="value" style="color:{bias_color};">{bias}</div>
    <div class="sub">REGIME SCORE <b>{fmt_num(regime)}</b></div>
</div>
""", unsafe_allow_html=True)


# ============================================================
#  Composite trajectory + strategy-vitals KV
# ============================================================
stats_rows = [
    ("REGIME SCORE",         fmt_num(regime),                                pos_class(regime)),
    ("MACRO COMPONENT",      fmt_num(comps.get("macro")),                    pos_class(comps.get("macro"))),
    ("RISK CURVE",           fmt_num(comps.get("risk_curve")),               pos_class(comps.get("risk_curve"))),
    ("MICRO COMPONENT",      fmt_num(comps.get("micro")),                    pos_class(comps.get("micro"))),
    ("LEAD/LAG",             fmt_num(comps.get("leadlag")),                  pos_class(comps.get("leadlag"))),
    ("OPTIONS",              fmt_num(comps.get("options")),                  pos_class(comps.get("options"))),
    ("EXTREMES",             fmt_num(comps.get("extremes")),                 pos_class(comps.get("extremes"))),
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
    st.markdown(kv_html(stats_rows, title="REGIME COMPONENTS"),
                unsafe_allow_html=True)


# ============================================================
#  Drill-down hint
# ============================================================
st.markdown(f"""
<div style="margin-top:12px;padding:8px 12px;border:1px dotted {ORANGE_DIM};
     background:#070707;color:#9A9A9A;font-size:10px;letter-spacing:0.10em;">
    USE THE SIDEBAR NAV TO DRILL INTO EACH LAYER
    &nbsp;→&nbsp; <span style="color:#FA8B1F;">MACRO</span>
    &nbsp;·&nbsp; <span style="color:#FA8B1F;">RISK CURVE</span>
    &nbsp;·&nbsp; <span style="color:#FA8B1F;">MICRO</span>
    &nbsp;·&nbsp; <span style="color:#FA8B1F;">OPTIONS</span>
    &nbsp;·&nbsp; <span style="color:#FA8B1F;">LEAD/LAG</span>
    &nbsp;·&nbsp; <span style="color:#FA8B1F;">SESSIONS</span>
</div>
""", unsafe_allow_html=True)
