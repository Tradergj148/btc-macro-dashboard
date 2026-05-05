"""Micro page — funding, OI, ETF flows, DVOL, microstructure composite.

Layer 3 of the compass: BTC-native flow & positioning.
"""
from __future__ import annotations

# Path bootstrap ──────────────────────────────────────────────────────
import sys
from pathlib import Path
_APP_DIR = Path(__file__).resolve().parents[1]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# ─────────────────────────────────────────────────────────────────────

import plotly.graph_objects as go
import streamlit as st

from _shared.page    import setup_page
from _shared.loaders import load
from _shared.charts  import bbg_layout, line_panel, bar_panel
from _shared.style   import ORANGE, ORANGE_DIM, GREEN, RED, CYAN, YELLOW

setup_page("Micro")
st.markdown("<h1>BTC FLOWS / MICRO — LAYER 3</h1>", unsafe_allow_html=True)

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
        # Per-exchange + annualised funding
        exch_cols = [c for c in funding.columns
                     if c in ("binance", "bybit", "okx", "funding_blend")]
        if exch_cols:
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
                                        font=dict(color=ORANGE, size=10)))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

        # Z-score panel with ±2σ alert bands
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
                fig.add_hrect(y0=-5, y1=-2, fillcolor=GREEN, opacity=0.06, line_width=0)
                fig.update_layout(**bbg_layout(
                    title="FUNDING Z-SCORE  (60d window, ±2σ = extremes)",
                    height=200))
                st.plotly_chart(fig, width='stretch',
                                config={"displayModeBar": False})

        # Cumulative funding paid
        if "funding_blend" in funding.columns:
            f = funding["funding_blend"].dropna()
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
