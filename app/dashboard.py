"""Streamlit dashboard — `streamlit run app/dashboard.py`

Reads parquet snapshots written by `src/pipeline.py`. Use the Reload button
or run the pipeline again to refresh data.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


# ---------- helpers ----------
@st.cache_data(ttl=600)
def load(name: str) -> pd.DataFrame:
    p = DATA / f"{name}.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(ttl=600)
def load_summary() -> dict:
    p = DATA / "summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def gauge(value: float, title: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".2f"},
            gauge={
                "axis": {"range": [-1, 1]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [-1, -0.5], "color": "#7a0d0d"},
                    {"range": [-0.5, -0.2], "color": "#c75450"},
                    {"range": [-0.2, 0.2], "color": "#cccccc"},
                    {"range": [0.2, 0.5], "color": "#86c476"},
                    {"range": [0.5, 1], "color": "#1d6d2c"},
                ],
            },
            title={"text": title},
        )
    )
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def bias_color(bias: str) -> str:
    return {
        "STRONG BULLISH": "#1d6d2c",
        "BULLISH": "#86c476",
        "NEUTRAL": "#888888",
        "BEARISH": "#c75450",
        "STRONG BEARISH": "#7a0d0d",
    }.get(bias, "#888888")


# ---------- page config ----------
st.set_page_config(page_title="BTC Macro Liquidity Release Valve", layout="wide")
st.title("Bitcoin — Macro Liquidity Release Valve Dashboard")
st.caption("Systematic framework based on Capital Flows Research methodology.")

summary = load_summary()
regime_df = load("regime_score")
macro_s = load("macro_score")
rc_s = load("risk_curve_score")
micro_s = load("micro_score")
ll_s = load("leadlag_score")

# ---------- top header ----------
c1, c2, c3, c4 = st.columns([1.4, 1, 1, 1])
with c1:
    if summary:
        bias = summary.get("bias", "—")
        st.markdown(
            f"<div style='padding:14px;border-radius:10px;"
            f"background:{bias_color(bias)};color:white;text-align:center;'>"
            f"<h2 style='margin:0;'>Bias: {bias}</h2>"
            f"<p style='margin:0;'>Regime score: <b>{summary['regime_score']:.2f}</b><br>"
            f"Suggested position: <b>{summary['position_weight']*100:.0f}% of unit</b></p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Run `python -m src.pipeline` first to populate data.")
with c2: st.plotly_chart(gauge(summary.get("components", {}).get("macro", 0) or 0, "Macro"), use_container_width=True)
with c3: st.plotly_chart(gauge(summary.get("components", {}).get("risk_curve", 0) or 0, "Risk Curve"), use_container_width=True)
with c4: st.plotly_chart(gauge(summary.get("components", {}).get("micro", 0) or 0, "Microstructure"), use_container_width=True)

st.markdown("---")

# ---------- composite line ----------
if not regime_df.empty:
    fig = px.line(regime_df.tail(500), title="Composite Regime Score (last 500d)")
    fig.add_hrect(y0=0.2, y1=1, fillcolor="green", opacity=0.07)
    fig.add_hrect(y0=-1, y1=-0.2, fillcolor="red", opacity=0.07)
    st.plotly_chart(fig, use_container_width=True)

# ---------- tabs per layer ----------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Macro", "Risk Curve", "BTC Flows / Microstructure",
     "Lead/Lag", "Alerts", "Backtest"]
)

with tab1:
    st.subheader("Macro liquidity components")
    raw = load("macro_raw")
    if not raw.empty:
        st.line_chart(raw[[c for c in raw.columns if c in
                           ("real_yield_10y", "breakeven_5y", "fed_balance_sheet",
                            "rrp", "tga", "dxy", "m2_us")]].tail(2000))
    if not macro_s.empty:
        st.line_chart(macro_s.tail(1000))

with tab2:
    st.subheader("Risk curve components")
    rc = load("risk_curve_raw")
    if not rc.empty:
        cols = [c for c in ("hy_oas", "vix", "arkk", "spy", "iwm", "soxx") if c in rc.columns]
        if cols:
            st.line_chart(rc[cols].tail(1000))
    if not rc_s.empty:
        st.line_chart(rc_s.tail(1000))

with tab3:
    st.subheader("BTC flows & microstructure")
    cA, cB = st.columns(2)
    with cA:
        etf = load("etf_flows")
        if not etf.empty:
            st.markdown("**Spot BTC ETF net flows ($m, Total)**")
            st.bar_chart(etf["Total"].tail(60))
    with cB:
        funding = load("funding")
        if not funding.empty and "funding_blend" in funding:
            st.markdown("**Perp funding rate (blended, daily mean)**")
            st.line_chart(funding["funding_blend"].tail(180))

    cC, cD = st.columns(2)
    with cC:
        oi = load("open_interest")
        if not oi.empty:
            st.markdown("**Binance BTC perp open interest (USD)**")
            st.line_chart(oi.tail(180))
    with cD:
        dvol = load("dvol")
        if not dvol.empty:
            st.markdown("**Deribit DVOL (BTC implied vol index)**")
            st.line_chart(dvol.tail(365))

    if not micro_s.empty:
        st.markdown("**Micro composite score**")
        st.line_chart(micro_s.tail(1000))

with tab4:
    st.subheader("Lead/Lag proxies")
    ll = load("leadlag_raw")
    if not ll.empty:
        cols = [c for c in ("mstr", "coin", "mara", "riot", "clsk", "btc_cme") if c in ll.columns]
        if cols:
            norm = ll[cols] / ll[cols].iloc[0]
            st.line_chart(norm.tail(500))
    if not ll_s.empty:
        st.line_chart(ll_s.tail(1000))

with tab5:
    st.subheader("Active alerts (positioning extremes)")
    alerts = load("alerts")
    if alerts.empty:
        st.info("No alerts file yet.")
    else:
        latest = alerts.iloc[-1]
        for k, v in latest.items():
            if isinstance(v, (bool,)):
                color = "🟥" if v else "⬜"
                st.write(f"{color} **{k}**: {v}")

with tab6:
    st.subheader("Backtest — composite signal vs BTC buy & hold")
    bt = load("backtest")
    if not bt.empty and {"equity", "bh_equity"}.issubset(bt.columns):
        st.line_chart(bt[["equity", "bh_equity"]].tail(2000))
        if summary.get("backtest_stats"):
            st.json(summary["backtest_stats"])
    else:
        st.info("Run the pipeline to generate backtest output.")

st.markdown("---")
st.caption("Sources: FRED, Yahoo Finance, CoinGecko, Binance, Bybit, Deribit, Farside. "
           "Free / public APIs only. Educational use — not investment advice.")
