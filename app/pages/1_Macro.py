"""Macro page — global liquidity, central banks, FX, real yields, breakeven.

Layer 1 of the compass.
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
from _shared.charts  import bbg_layout, line_panel, small_multiples
from _shared.style   import (
    ORANGE, ORANGE_DIM, CYAN, GREEN, RED, YELLOW, MAGENTA, TEXT_DIM,
)

setup_page("Macro")
st.markdown("<h1>MACRO LIQUIDITY — LAYER 1</h1>", unsafe_allow_html=True)

raw = load("macro_raw")
if raw.empty:
    st.info("Macro data not yet pulled. Run `python -m src.pipeline`.")
    st.stop()

ms = load("macro_score")

c_a, c_b = st.columns([2, 1])
with c_a:
    sm = small_multiples(raw.tail(2500),
        ["real_yield_10y", "breakeven_5y", "fed_balance_sheet",
         "dxy", "m2_us", "rrp"],
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

# ---------- FED NET LIQUIDITY ----------
if {"fed_balance_sheet", "rrp", "tga"}.issubset(raw.columns):
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
                                font=dict(color=ORANGE, size=10)))
    st.plotly_chart(fig, width='stretch',
                    config={"displayModeBar": False})

    # Per-CB stacked breakdown
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
                                    font=dict(color=ORANGE, size=10)))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

    # Latest snapshot panel
    latest = gnl.iloc[-1]
    rows_html = []
    for c in cb_cols:
        val = latest.get(c)
        if isinstance(val, (int, float)) and val == val:
            rows_html.append(
                f"<div class='kv'><span class='k'>{cb_label.get(c, c.upper())}</span>"
                f"<span class='v neu'>{val:,.0f} $BN</span></div>")
    agg_val = latest.get("global_net_liquidity_usd_bn")
    if isinstance(agg_val, (int, float)) and agg_val == agg_val:
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
fx_cols = [c for c in
           ("dxy", "eurusd", "usdjpy", "gbpusd", "usdcad",
            "audusd", "nzdusd", "usdcnh")
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
