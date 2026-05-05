"""Options page — term structure, skew, GEX with dealer pain zone.

Layer 6 (options-derived vol outlook).
"""
from __future__ import annotations

# Path bootstrap ──────────────────────────────────────────────────────
import sys
from pathlib import Path
_APP_DIR = Path(__file__).resolve().parents[1]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# ─────────────────────────────────────────────────────────────────────

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _shared.page    import setup_page
from _shared.loaders import load, load_summary
from _shared.charts  import bbg_layout
from _shared.style   import (
    ORANGE, ORANGE_DIM, WHITE, GREEN, RED, YELLOW,
)

summary = setup_page("Options")
st.markdown("<h1>OPTIONS — LAYER 6</h1>", unsafe_allow_html=True)

opt_summary  = (summary.get("components", {}) or {}).get("options")
opt_breakdown = (summary.get("components", {}) or {}).get("options_breakdown", {}) or {}

# ----- header strip with three score readouts -----
h1, h2, h3, h4 = st.columns([1, 1, 1, 1])
with h1:
    st.markdown(
        f"<div class='panel'><div class='panel-title'>OPTIONS COMPOSITE</div>"
        f"<div style='font-size:24px;color:{ORANGE};text-align:center;font-weight:700;'>"
        f"{opt_summary:+.3f}</div></div>" if isinstance(opt_summary, (int, float))
        else "<div class='panel'><div class='panel-title'>OPTIONS COMPOSITE</div>"
             "<div style='font-size:24px;color:#888;text-align:center;'>—</div></div>",
        unsafe_allow_html=True)
for col, lbl, key in [(h2, "TERM", "term"), (h3, "SKEW", "skew"), (h4, "GEX", "gex")]:
    with col:
        v = opt_breakdown.get(key)
        color = ORANGE if not isinstance(v, (int, float)) else (
            GREEN if v > 0.2 else RED if v < -0.2 else ORANGE)
        disp = f"{v:+.3f}" if isinstance(v, (int, float)) else "—"
        st.markdown(
            f"<div class='panel'><div class='panel-title'>{lbl} SCORE</div>"
            f"<div style='font-size:22px;color:{color};text-align:center;font-weight:700;'>{disp}</div></div>",
            unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ----- Term structure + Skew curve side by side -----
cA, cB = st.columns(2)
with cA:
    term = load("options_term")
    if not term.empty and {"dte_days", "atm_iv"}.issubset(term.columns):
        df = term.dropna(subset=["atm_iv", "dte_days"]).sort_values("dte_days")
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
        fig.update_xaxes(title=dict(text="DAYS TO EXPIRY", font=dict(color=ORANGE, size=10)))
        fig.update_yaxes(title=dict(text="IMPLIED VOL %", font=dict(color=ORANGE, size=10)))
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Run pipeline to populate term structure.")

with cB:
    skew = load("options_skew")
    if not skew.empty and {"dte_days", "iv_call25", "iv_put25", "iv_atm"}.issubset(skew.columns):
        df = skew.dropna().sort_values("dte_days")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_call25"]*100,
            mode="lines+markers", line=dict(color=GREEN, width=2), name="25d CALL"))
        fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_atm"]*100,
            mode="lines+markers", line=dict(color=ORANGE, width=2), name="ATM"))
        fig.add_trace(go.Scatter(x=df["dte_days"], y=df["iv_put25"]*100,
            mode="lines+markers", line=dict(color=RED, width=2), name="25d PUT"))
        fig.update_layout(**bbg_layout(
            title="SKEW CURVE  (25d CALL / ATM / 25d PUT, % vol)",
            height=320))
        fig.update_xaxes(title=dict(text="DAYS TO EXPIRY", font=dict(color=ORANGE, size=10)))
        fig.update_yaxes(title=dict(text="IMPLIED VOL %", font=dict(color=ORANGE, size=10)))
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Run pipeline to populate skew curve.")

# ----- 25d skew (RR) per expiry — clipped to ≤180d for legibility -----
skew = load("options_skew")
if not skew.empty and "skew_25d" in skew.columns:
    df = skew.dropna(subset=["skew_25d", "dte_days"]).sort_values("dte_days")
    df_short = df[df["dte_days"] <= 180].copy()
    if df_short.empty:
        df_short = df.head(8)

    fig = go.Figure()
    colors = [GREEN if v >= 0 else RED for v in df_short["skew_25d"].values]
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
                                 font=dict(color=ORANGE, size=10)))
    fig.update_yaxes(title=dict(text="RR  (vol pts)",
                                 font=dict(color=ORANGE, size=10)))
    fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

# ----- GEX by strike (bar chart, signed, with spot + pain zone) -----
gex = load("options_gex_by_strike")
if not gex.empty and {"strike", "gex_usd_per_pct"}.issubset(gex.columns):
    gex_hist = load("options_gex_history")
    spot = (float(gex_hist["spot"].iloc[-1])
            if not gex_hist.empty and "spot" in gex_hist.columns else None)

    df = gex.sort_values("strike").copy()
    colors = [GREEN if v >= 0 else RED for v in df["gex_usd_per_pct"].values]

    pain_lo = pain_hi = None
    pain_strike = None
    if spot is not None and len(df) > 0:
        near = df[(df["strike"] >= spot * 0.75) &
                  (df["strike"] <= spot * 1.25)]
        neg = near[near["gex_usd_per_pct"] < 0]
        if not neg.empty:
            pain_lo = float(neg["strike"].min())
            pain_hi = float(neg["strike"].max())
            pain_strike = float(
                neg.loc[neg["gex_usd_per_pct"].idxmin(), "strike"])

    fig = go.Figure(go.Bar(
        x=df["strike"], y=df["gex_usd_per_pct"]/1e6,
        marker_color=colors, marker_line_width=0,
        hovertemplate="strike %{x:,.0f}<br>GEX %{y:+.2f} M$<extra></extra>"))

    if pain_lo is not None:
        fig.add_vrect(
            x0=pain_lo, x1=pain_hi,
            fillcolor=RED, opacity=0.10, line_width=0,
            annotation_text=f"DEALER PAIN ZONE  {pain_lo:,.0f}–{pain_hi:,.0f}",
            annotation_position="top left",
            annotation=dict(font=dict(color=RED, size=10,
                                      family="JetBrains Mono")),
        )
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
                                 font=dict(color=ORANGE, size=10)))
    fig.update_yaxes(title=dict(text="GEX  ($M / 1%)",
                                 font=dict(color=ORANGE, size=10)))
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
    cA, cB = st.columns([2, 1])
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
        fig.update_yaxes(title=dict(text="GEX TOTAL  ($M / 1%)",
                                    font=dict(color=ORANGE, size=10)))
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
if not chain.empty and {"strike", "expiry", "type", "open_interest"}.issubset(chain.columns):
    gex_hist2 = load("options_gex_history")
    spot = (float(gex_hist2["spot"].iloc[-1])
            if not gex_hist2.empty and "spot" in gex_hist2.columns
            else float(chain["strike"].median()))
    lo, hi = spot * 0.5, spot * 1.7
    df = chain[(chain["strike"] >= lo) & (chain["strike"] <= hi)].copy()
    df["expiry_str"] = pd.to_datetime(df["expiry"]).dt.strftime("%d%b%y")
    first_expiries = sorted(df["expiry_str"].unique(),
                            key=lambda s: pd.to_datetime(s, format="%d%b%y"))[:8]
    df = df[df["expiry_str"].isin(first_expiries)]

    cA, cB = st.columns(2)
    for col, opt_type, label, cmap in [(cA, "C", "CALLS", "Greens"),
                                       (cB, "P", "PUTS",  "Reds")]:
        with col:
            sub = df[df["type"] == opt_type]
            if sub.empty:
                continue
            pivot = sub.pivot_table(index="strike", columns="expiry_str",
                                    values="open_interest", aggfunc="sum").fillna(0)
            pivot = pivot[[e for e in first_expiries if e in pivot.columns]]
            fig = go.Figure(go.Heatmap(
                z=pivot.values, x=pivot.columns, y=pivot.index,
                colorscale=cmap, showscale=True,
                hovertemplate="strike %{y:,.0f}<br>expiry %{x}<br>OI %{z:,.0f}<extra></extra>",
            ))
            fig.update_layout(**bbg_layout(
                title=f"{label} OPEN INTEREST  (contracts, strike × expiry)",
                height=380))
            fig.update_xaxes(title=dict(text="EXPIRY",
                                        font=dict(color=ORANGE, size=10)))
            fig.update_yaxes(title=dict(text="STRIKE",
                                        font=dict(color=ORANGE, size=10)))
            if spot:
                fig.add_hline(y=spot, line_color=YELLOW, line_width=1.5,
                    line_dash="dash")
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
