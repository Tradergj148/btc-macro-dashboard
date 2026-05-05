"""Macro Plumbing — market anatomy.

Conks-style flow & stress view of the dollar plumbing system.  Seven tabs in
priority order:

    FISCAL    — TGA dynamics: drawdown / refill / issuance mix
    FUNDING   — Repo / SRF / RRP / SOFR-IORB stress
    DEALERS   — UST swap spreads + cash-futures basis (balance-sheet pressure)
    FX BASIS  — Cross-currency basis (offshore $ stress)
    RV LEV    — RV-fund leverage / cash-futures basis dispersion
    RESERVES  — Reserves stress / deposit flows
    ANATOMY   — Regulatory rule structure + effective ratios per G-SIB

Phase A in this commit: FISCAL tab fully built; ANATOMY tab fully built (it's
mostly static).  The middle tabs render structured placeholders showing
exactly what data + visualisation lands there next.
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
from _shared.loaders import load
from _shared.charts  import bbg_layout, bar_panel, line_panel, kv_html
from _shared.style   import (
    ORANGE, ORANGE_DIM, WHITE, GREEN, RED, CYAN, YELLOW, MAGENTA, TEXT_DIM,
    PANEL_BG, GRID,
)

setup_page("Plumbing")
st.markdown("<h1>MACRO PLUMBING — MARKET ANATOMY</h1>",
            unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top:-4px;margin-bottom:10px;color:{TEXT_DIM};font-size:11px;
     letter-spacing:0.05em;line-height:1.5;">
    Where dollars sit, which balance sheet absorbs them next, and what's
    creaking under the surface. Conks-style flow &amp; stress lens — sequence
    matters: <span style="color:{ORANGE}">RESERVES → MMFs/RRP → BILLS →
    USTs → RISK</span>. When earlier layers saturate, the marginal dollar
    must travel further down.
</div>
""", unsafe_allow_html=True)

tab_fiscal, tab_funding, tab_dealers, tab_fx, tab_rv, tab_res, tab_anat = (
    st.tabs([
        "FISCAL  (TGA)",
        "FUNDING  (Repo/SRF/RRP)",
        "DEALERS  (Basis/Swap-Spreads)",
        "FX BASIS  (Offshore $)",
        "RV LEVERAGE",
        "RESERVES & DEPOSITS",
        "ANATOMY  (Reg Stack)",
    ])
)


# ============================================================
#  TAB 1 — FISCAL  (TGA dynamics, fully built)
# ============================================================
with tab_fiscal:
    tga = load("tga_balance")
    net = load("tga_net_flow")
    bvc = load("debt_bills_vs_coupons")

    if tga.empty:
        st.info(
            "TGA data not yet pulled. Run `python -m src.pipeline` to "
            "populate fiscal series via the Treasury FiscalData API."
        )
    else:
        # ---- Status row: 4 KPI cells ----
        s = tga.iloc[:, 0].dropna()
        last_val   = float(s.iloc[-1])
        d7_change  = (last_val - float(s.iloc[-8]))   if len(s) > 7  else 0.0
        d30_change = (last_val - float(s.iloc[-31]))  if len(s) > 30 else 0.0
        last_date  = s.index[-1]

        # Direction colour (TGA growing = drains system; shrinking = injects)
        def _flow_color(delta_musd):
            return GREEN if delta_musd < 0 else RED if delta_musd > 0 else ORANGE
        def _flow_word(delta_musd):
            return "INJECTING" if delta_musd < 0 else "DRAINING" if delta_musd > 0 else "FLAT"

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"<div class='panel'><div class='panel-title'>TGA BALANCE</div>"
                f"<div style='font-size:22px;color:{ORANGE};text-align:center;font-weight:700;'>"
                f"${last_val/1000:,.0f} BN</div>"
                f"<div style='font-size:9px;color:{TEXT_DIM};text-align:center;'>"
                f"{last_date.strftime('%Y-%m-%d')}</div></div>",
                unsafe_allow_html=True)
        with c2:
            col = _flow_color(d7_change)
            st.markdown(
                f"<div class='panel'><div class='panel-title'>7D Δ</div>"
                f"<div style='font-size:22px;color:{col};text-align:center;font-weight:700;'>"
                f"{d7_change/1000:+,.0f} BN</div>"
                f"<div style='font-size:9px;color:{col};text-align:center;letter-spacing:0.10em;'>"
                f"{_flow_word(d7_change)} SYSTEM</div></div>",
                unsafe_allow_html=True)
        with c3:
            col = _flow_color(d30_change)
            st.markdown(
                f"<div class='panel'><div class='panel-title'>30D Δ</div>"
                f"<div style='font-size:22px;color:{col};text-align:center;font-weight:700;'>"
                f"{d30_change/1000:+,.0f} BN</div>"
                f"<div style='font-size:9px;color:{col};text-align:center;letter-spacing:0.10em;'>"
                f"{_flow_word(d30_change)} SYSTEM</div></div>",
                unsafe_allow_html=True)
        with c4:
            # Conks heuristic: $750bn is Treasury's recent "operational target"
            target = 750_000  # USD millions
            gap = last_val - target
            gap_col = ORANGE if abs(gap) < 50_000 else (RED if gap > 0 else GREEN)
            st.markdown(
                f"<div class='panel'><div class='panel-title'>VS $750BN TARGET</div>"
                f"<div style='font-size:22px;color:{gap_col};text-align:center;font-weight:700;'>"
                f"{gap/1000:+,.0f} BN</div>"
                f"<div style='font-size:9px;color:{TEXT_DIM};text-align:center;'>"
                f"Treasury operational target (approx)</div></div>",
                unsafe_allow_html=True)

        # ---- TGA balance trajectory (full history) ----
        df = s.tail(2 * 365).rename("TGA").to_frame()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["TGA"]/1000, mode="lines",
            line=dict(color=ORANGE, width=1.6),
            fill="tozeroy", fillcolor="rgba(250,139,31,0.10)",
            name="TGA",
        ))
        fig.add_hline(y=750, line_color=YELLOW, line_width=1, line_dash="dash",
                      annotation_text="$750B target",
                      annotation_position="top left",
                      annotation=dict(font=dict(color=YELLOW, size=9)))
        fig.update_layout(**bbg_layout(
            title="TGA BALANCE — 2Y TRAJECTORY  ($BN)",
            height=300))
        fig.update_yaxes(title=dict(text="USD BILLIONS",
                                    font=dict(color=ORANGE, size=10)))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

        # ---- Daily TGA net flow (deposits − withdrawals) ----
        if not net.empty:
            netser = net.iloc[:, 0].dropna().tail(120) / 1000  # to USD bn
            colors = [GREEN if v < 0 else RED for v in netser.values]
            fig = go.Figure(go.Bar(
                x=netser.index, y=netser.values,
                marker_color=colors, marker_line_width=0,
                hovertemplate="%{x|%Y-%m-%d}<br>Net flow %{y:+.1f} $bn<extra></extra>",
            ))
            fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
            fig.update_layout(**bbg_layout(
                title="DAILY NET TGA FLOW  ($BN)  +VE = REFILL (DRAIN)  ·  -VE = DRAWDOWN (INJECT)",
                height=240))
            fig.update_yaxes(title=dict(text="USD BILLIONS / DAY",
                                        font=dict(color=ORANGE, size=10)))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

        # ---- Bills vs Coupons issuance mix ----
        if not bvc.empty:
            bv = bvc.tail(120).copy()
            # USD bn for legibility
            bv["bills_net_bn"]   = bv["bills_net_musd"]   / 1000
            bv["coupons_net_bn"] = bv["coupons_net_musd"] / 1000
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=bv.index, y=bv["bills_net_bn"],
                marker_color=CYAN, marker_line_width=0,
                name="BILLS NET (T-Bills)",
                hovertemplate="%{x|%Y-%m-%d}<br>Bills net %{y:+.1f} $bn<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=bv.index, y=bv["coupons_net_bn"],
                marker_color=MAGENTA, marker_line_width=0,
                name="COUPONS NET (Notes/Bonds/TIPS/FRN)",
                hovertemplate="%{x|%Y-%m-%d}<br>Coupons net %{y:+.1f} $bn<extra></extra>",
            ))
            fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
            fig.update_layout(barmode="relative",
                              **bbg_layout(
                title="NET DEBT ISSUANCE — BILLS vs COUPONS  ($BN, ISSUED − REDEEMED)",
                height=280))
            fig.update_yaxes(title=dict(text="USD BILLIONS / DAY",
                                        font=dict(color=ORANGE, size=10)))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

            # ---- Bill-vs-coupon mix snapshot panel ----
            recent = bv.tail(20)  # last 20 trading days
            bills_total   = float(recent["bills_net_bn"].sum())
            coupons_total = float(recent["coupons_net_bn"].sum())
            total_total   = bills_total + coupons_total
            pct_bills   = (bills_total   / total_total * 100) if total_total else 0
            pct_coupons = (coupons_total / total_total * 100) if total_total else 0

            mix_kv = [
                ("LAST 20D NET BILLS",   f"{bills_total:+,.1f} $BN",     "neu"),
                ("LAST 20D NET COUPONS", f"{coupons_total:+,.1f} $BN",   "neu"),
                ("LAST 20D NET TOTAL",   f"{total_total:+,.1f} $BN",     "neu"),
                ("BILL SHARE OF NET",    f"{pct_bills:+.1f}%",           "neu"),
                ("COUPON SHARE OF NET",  f"{pct_coupons:+.1f}%",         "neu"),
            ]
            absorption_note = (
                "BILL-HEAVY: absorbed by MMFs / RRP (low duration friction)."
                if pct_bills > 60 else
                "COUPON-HEAVY: requires duration buyers — dealer + asset-mgr capacity."
                if pct_coupons > 60 else
                "BALANCED: absorption spread across MMFs and duration buyers."
            )

            cA, cB = st.columns([1, 1])
            with cA:
                st.markdown(kv_html(mix_kv, title="ISSUANCE MIX — LAST 20D"),
                            unsafe_allow_html=True)
            with cB:
                st.markdown(
                    f"<div class='panel'><div class='panel-title'>"
                    f"ABSORPTION READ</div>"
                    f"<div style='color:{WHITE};font-size:11px;line-height:1.6;'>"
                    f"{absorption_note}<br><br>"
                    f"<span style='color:{TEXT_DIM};font-size:10px;'>"
                    f"Bills are absorbed by money-market funds with no duration "
                    f"risk — they don't compete with risk assets for capital. "
                    f"Coupon issuance forces dealer + asset-manager balance "
                    f"sheet absorption; when it crowds out, swap spreads widen "
                    f"and risk assets feel it."
                    f"</span></div></div>",
                    unsafe_allow_html=True)

        # ---- Plumbing transmission read ----
        st.markdown(f"""
        <div style="margin-top:14px;padding:10px 14px;border:1px dotted {ORANGE_DIM};
             background:{PANEL_BG};color:{WHITE};font-size:11px;line-height:1.7;">
            <span style="color:{ORANGE};font-weight:700;letter-spacing:0.10em;">
            CONKS TRANSMISSION CHAIN</span><br>
            <span style="color:{TEXT_DIM};font-size:10px;">
            TGA Δ → Bank Reserves Δ → RRP Δ → Bill demand Δ → UST/risk Δ
            </span><br><br>
            TGA <span style="color:{_flow_color(d30_change)};font-weight:700;">
            {_flow_word(d30_change)}</span> the system over the last 30 days
            (Δ {d30_change/1000:+,.0f} $bn).
            All else equal, that pushes
            <span style="color:{_flow_color(-d30_change)};">
            {'higher' if d30_change < 0 else 'lower'}</span>
            reserves and
            <span style="color:{_flow_color(-d30_change)};">
            {'more' if d30_change < 0 else 'less'}</span>
            cash searching for yield down the absorption ladder.
        </div>
        """, unsafe_allow_html=True)


# ============================================================
#  TAB 2 — FUNDING  (placeholder; data fetched, viz coming)
# ============================================================
with tab_funding:
    st.markdown(f"<h3 style='margin-top:0;'>REPO / SRF / RRP — FUNDING PLUMBING</h3>",
                unsafe_allow_html=True)

    rates = load("plumbing_rates")
    if rates.empty:
        st.info("Run `python -m src.pipeline` to populate funding-rate series "
                "(SOFR, IORB, BGCR, TGCR, EFFR, OBFR, OFRFSI, TOTRESNS).")
    else:
        # SOFR-IORB spread — the master "is the plumbing creaking" signal
        if "sofr_iorb_bps" in rates.columns:
            spread = rates["sofr_iorb_bps"].dropna().tail(365)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=spread.index, y=spread.values, mode="lines",
                line=dict(color=ORANGE, width=1.6),
                fill="tozeroy", fillcolor="rgba(250,139,31,0.10)",
                name="SOFR-IORB",
            ))
            fig.add_hline(y=0,  line_color=ORANGE_DIM, line_width=0.7)
            fig.add_hline(y=5,  line_color=YELLOW, line_width=1, line_dash="dot",
                          annotation_text="warning",
                          annotation=dict(font=dict(color=YELLOW, size=9)))
            fig.add_hline(y=10, line_color=RED, line_width=1, line_dash="dash",
                          annotation_text="stress",
                          annotation=dict(font=dict(color=RED, size=9)))
            fig.update_layout(**bbg_layout(
                title="SOFR − IORB SPREAD  (BPS)  ·  rising = repo plumbing tightening",
                height=240))
            fig.update_yaxes(title=dict(text="BPS", font=dict(color=ORANGE, size=10)))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

        # Rates panel — SOFR vs IORB vs EFFR
        rates_cols = [c for c in ("sofr", "iorb", "effr", "obfr") if c in rates.columns]
        if rates_cols:
            st.plotly_chart(
                line_panel(rates[rates_cols].tail(365),
                           "OVERNIGHT $ RATES  (SOFR · IORB · EFFR · OBFR, %)"),
                width='stretch', config={"displayModeBar": False})

        # OFR Financial Stress Index
        if "ofr_fsi" in rates.columns:
            fsi = rates["ofr_fsi"].dropna().tail(2 * 365)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=fsi.index, y=fsi.values, mode="lines",
                line=dict(color=YELLOW, width=1.4),
                name="OFR FSI",
            ))
            fig.add_hline(y=0, line_color=ORANGE_DIM, line_width=0.7)
            fig.add_hrect(y0=2, y1=10, fillcolor=RED, opacity=0.06, line_width=0)
            fig.add_hrect(y0=-10, y1=-2, fillcolor=GREEN, opacity=0.06, line_width=0)
            fig.update_layout(**bbg_layout(
                title="OFR FINANCIAL STRESS INDEX  ·  >2 = elevated stress",
                height=240))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

    st.markdown(f"""
    <div class='panel'><div class='panel-title'>NEXT IN THIS TAB</div>
    <div style='color:{TEXT_DIM};font-size:11px;line-height:1.6;padding:6px 0;'>
        <span style='color:{ORANGE}'>SRF usage time series</span> — daily
        Standing Repo Facility take-up (NY Fed daily ops). Non-zero = dealers
        tapping the Fed for emergency cash. <br>
        <span style='color:{ORANGE}'>RRP counterparty count</span> — number
        of MMFs / GSEs parking cash at the Fed. Tracks "dry-powder" capacity. <br>
        <span style='color:{ORANGE}'>Specials premium</span> — gap between
        general-collateral and specific-collateral repo rates. Widening =
        Treasury demand pressure. <br>
        <span style='color:{ORANGE}'>Repo-by-venue breakdown</span> — DVP /
        Triparty / Sponsored / GCF / FICC volumes from OFR + DTCC.
    </div></div>
    """, unsafe_allow_html=True)


# ============================================================
#  TAB 3 — DEALERS  (placeholder)
# ============================================================
with tab_dealers:
    st.markdown(f"<h3 style='margin-top:0;'>DEALER BALANCE-SHEET PRESSURE</h3>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <div class='panel'><div class='panel-title'>SCOPE  (PHASE B)</div>
    <div style='color:{WHITE};font-size:11px;line-height:1.7;padding:6px 0;'>
        <span style='color:{ORANGE}'>UST swap spreads</span> — 10Y UST yield
        minus 10Y swap rate. Negative-and-widening = dealer balance sheet
        constrained, can't absorb USTs even when cheap. Conks's preferred
        single-number proxy for dealer capacity. Source: Fed H.15 + market
        swap quotes. <br>
        <span style='color:{ORANGE}'>NY Fed primary dealer net positions</span>
        — weekly H.4.1 supplement: dealer net long / short by maturity bucket
        (USTs, MBS, agencies). Tells you whether dealers are warehousing or
        offloading. <br>
        <span style='color:{ORANGE}'>Treasury cash-futures basis</span> — the
        spread between cash USTs and CTD futures. When basis trades crowd in,
        spread compresses; when they unwind forcibly, it spikes. RV-fund
        leverage thermometer. Source: CFTC COT (asset-manager vs leveraged-fund
        positioning) + CME front-month basis. <br>
        <span style='color:{ORANGE}'>Specials premium</span> — already noted in
        FUNDING tab; appears here too because dealer specials desk is the
        plumbing layer that feels it first.
    </div></div>
    """, unsafe_allow_html=True)


# ============================================================
#  TAB 4 — FX BASIS  (placeholder)
# ============================================================
with tab_fx:
    st.markdown(f"<h3 style='margin-top:0;'>CROSS-CURRENCY BASIS — OFFSHORE $ STRESS</h3>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <div class='panel'><div class='panel-title'>SCOPE  (PHASE B)</div>
    <div style='color:{WHITE};font-size:11px;line-height:1.7;padding:6px 0;'>
        <span style='color:{ORANGE}'>3M EUR/USD basis swap</span>,
        <span style='color:{ORANGE}'>JPY/USD basis</span>,
        <span style='color:{ORANGE}'>GBP/USD basis</span>. Negative-and-
        widening = offshore borrowers paying a premium for dollars — classic
        dollar-funding stress signal. Was deeply negative around 2008, 2011-12,
        Mar-2020. <br>
        <span style='color:{ORANGE}'>FX swap spread to OIS</span> — local
        OIS rate vs. dollar-implied yield via FX swaps. Same signal, alternate
        construction. <br>
        <span style='color:{ORANGE}'>Fed FX swap line drawdowns</span> — when
        the Fed activates standing swap lines with ECB/BoJ/SNB/BoE/BoC, that's
        an explicit "offshore $ stress" alarm. Free data: H.4.1, weekly. <br>
        <span style='color:{TEXT_DIM};font-size:10px;'>Free clean basis-swap
        history is harder to source than spot FX; we'll start with FRED's
        published ON-RRP foreign-RP series + BIS quarterly cross-currency basis
        and stub the rest.</span>
    </div></div>
    """, unsafe_allow_html=True)


# ============================================================
#  TAB 5 — RV LEVERAGE  (placeholder)
# ============================================================
with tab_rv:
    st.markdown(f"<h3 style='margin-top:0;'>RV-FUND LEVERAGE / CASH-FUTURES BASIS</h3>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <div class='panel'><div class='panel-title'>SCOPE  (PHASE B)</div>
    <div style='color:{WHITE};font-size:11px;line-height:1.7;padding:6px 0;'>
        <span style='color:{ORANGE}'>CFTC COT positioning</span> — asset
        managers (long bias) vs. leveraged funds (short bias) net positions in
        UST futures. The leveraged-fund net short is the basis-trade
        thermometer. When it explodes, cash-futures basis is being arbed at
        scale; when it unwinds, that's a forced de-lever. Free data, weekly. <br>
        <span style='color:{ORANGE}'>Cash-futures basis history</span> —
        front-month CME UST futures vs. CTD cash. Spread time series + 30d
        realised. <br>
        <span style='color:{ORANGE}'>Repo specials</span> — strong specials
        bid on the CTD = basis trade demand pressure. <br>
        <span style='color:{TEXT_DIM};font-size:10px;'>The 2020 "dash for
        cash" was an RV-fund forced de-lever; it's the textbook tail event
        this tab should help you see coming.</span>
    </div></div>
    """, unsafe_allow_html=True)


# ============================================================
#  TAB 6 — RESERVES & DEPOSITS  (placeholder)
# ============================================================
with tab_res:
    st.markdown(f"<h3 style='margin-top:0;'>RESERVES STRESS & DEPOSIT FLOWS</h3>",
                unsafe_allow_html=True)

    rates = load("plumbing_rates")
    if not rates.empty and "reserves" in rates.columns:
        res = rates["reserves"].dropna().tail(5 * 12)  # 5y monthly
        if not res.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=res.index, y=res.values, mode="lines",
                line=dict(color=GREEN, width=1.6),
                fill="tozeroy", fillcolor="rgba(0,255,102,0.08)",
                name="Reserves",
            ))
            fig.update_layout(**bbg_layout(
                title="TOTAL RESERVES (TOTRESNS, $bn)  ·  the system's HQLA pool",
                height=260))
            st.plotly_chart(fig, width='stretch',
                            config={"displayModeBar": False})

    st.markdown(f"""
    <div class='panel'><div class='panel-title'>NEXT IN THIS TAB</div>
    <div style='color:{TEXT_DIM};font-size:11px;line-height:1.6;padding:6px 0;'>
        <span style='color:{ORANGE}'>H.8 deposit flows</span> — weekly Fed
        bank deposit data, large vs small banks. The "deposit flight" series. <br>
        <span style='color:{ORANGE}'>FHLB advances outstanding</span> —
        proxy for bank funding stress. SVB-era spike was visible weeks
        early. <br>
        <span style='color:{ORANGE}'>BTFP usage</span> — Bank Term Funding
        Program (now closed) but the H.4.1 line is still informative for
        historical comparison.
    </div></div>
    """, unsafe_allow_html=True)


# ============================================================
#  TAB 7 — ANATOMY  (regulatory rule structure, fully built)
# ============================================================
with tab_anat:
    # Lazy import so the page doesn't fail if the file moves
    from src.data.regulatory import (
        CAPITAL_RATIO_MINIMUMS,
        FED_BANK_CATEGORIES,
        US_GSIB_SURCHARGES_2024,
        SCB_2024,
        EFFECTIVE_SLR_Q4_2024,
        TLAC_FRAMEWORK,
        all_gsib_regulatory_stacks,
    )

    st.markdown(f"<h3 style='margin-top:0;'>U.S. BANK CAPITAL REQUIREMENTS — REFERENCE</h3>",
                unsafe_allow_html=True)
    st.markdown(f"""
    <div style="color:{TEXT_DIM};font-size:11px;line-height:1.5;
         margin-top:-4px;margin-bottom:10px;">
        Constraint, not flow. These rules are why dealer balance sheets have
        finite repo capacity, why the FICC sponsored repo and Fed SRF were
        built, and why the shadow cash market exists. Refresh annually after
        Fed CCAR (June) and G-SIB list update (Q4).
    </div>
    """, unsafe_allow_html=True)

    # ---- Capital ratio minimums + buffers ----
    cA, cB = st.columns([1, 1])
    with cA:
        rows = [(k, f"{v:.1f}%", "neu") for k, v in CAPITAL_RATIO_MINIMUMS.items()]
        st.markdown(kv_html(rows, title="CAPITAL RATIO MINIMUMS"),
                    unsafe_allow_html=True)
    with cB:
        rows = [(k, v, "neu") for k, v in FED_BANK_CATEGORIES.items()]
        st.markdown(kv_html(rows, title="FED BANK CATEGORIES"),
                    unsafe_allow_html=True)

    # ---- G-SIB surcharges (2024-25 cycle) ----
    st.markdown(f"<h3>G-SIB SURCHARGE — 2024-25 CYCLE  "
                f"<span style='color:{TEXT_DIM};font-size:10px;'>(method 2 dominates)</span></h3>",
                unsafe_allow_html=True)
    df = US_GSIB_SURCHARGES_2024.copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["bank"], y=df["method_1_pct"],
        marker_color=CYAN, marker_line_width=0,
        name="METHOD 1 (BCBS)",
    ))
    fig.add_trace(go.Bar(
        x=df["bank"], y=df["method_2_pct"],
        marker_color=ORANGE, marker_line_width=0,
        name="METHOD 2 (Fed)",
    ))
    fig.add_trace(go.Scatter(
        x=df["bank"], y=df["effective_pct"], mode="markers+text",
        marker=dict(color=YELLOW, size=12, symbol="diamond"),
        text=[f"{v:.1f}%" for v in df["effective_pct"]],
        textposition="top center",
        textfont=dict(color=YELLOW, size=10, family="JetBrains Mono"),
        name="EFFECTIVE",
    ))
    fig.update_layout(barmode="group",
                      **bbg_layout(
        title="G-SIB SURCHARGE % BY BANK  ·  effective = max(M1, M2)",
        height=320))
    fig.update_yaxes(title=dict(text="SURCHARGE %",
                                 font=dict(color=ORANGE, size=10)))
    st.plotly_chart(fig, width='stretch',
                    config={"displayModeBar": False})

    # ---- Effective ratios (Q4 2024 snapshot) ----
    st.markdown(f"<h3>EFFECTIVE CAPITAL RATIOS — Q4 2024 SNAPSHOT</h3>",
                unsafe_allow_html=True)
    df2 = EFFECTIVE_SLR_Q4_2024.copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df2["bank"], y=df2["slr_pct"],   marker_color=ORANGE,
                        marker_line_width=0, name="SLR"))
    fig.add_trace(go.Bar(x=df2["bank"], y=df2["cet1_pct"],  marker_color=GREEN,
                        marker_line_width=0, name="CET1"))
    fig.add_trace(go.Bar(x=df2["bank"], y=df2["tier1_pct"], marker_color=CYAN,
                        marker_line_width=0, name="TIER 1"))
    fig.add_trace(go.Bar(x=df2["bank"], y=df2["total_pct"], marker_color=MAGENTA,
                        marker_line_width=0, name="TOTAL"))
    # Reference lines
    fig.add_hline(y=5,    line_color=ORANGE, line_width=0.8, line_dash="dash",
                  annotation_text="SLR eff. min for G-SIBs (3% + 2% eSLR)",
                  annotation_position="top right",
                  annotation=dict(font=dict(color=ORANGE, size=9)))
    fig.update_layout(barmode="group",
                      **bbg_layout(
        title="EFFECTIVE RATIOS BY US G-SIB  (Q4 2024)",
        height=340))
    fig.update_yaxes(title=dict(text="%",
                                 font=dict(color=ORANGE, size=10)))
    st.plotly_chart(fig, width='stretch',
                    config={"displayModeBar": False})

    # ---- Effective CET1 minimum stack per bank ----
    st.markdown(f"<h3>EFFECTIVE CET1 MINIMUMS PER BANK  "
                f"<span style='color:{TEXT_DIM};font-size:10px;'>"
                f"(4.5% min + SCB + G-SIB surcharge)</span></h3>",
                unsafe_allow_html=True)
    stack = all_gsib_regulatory_stacks()
    if not stack.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=stack["bank"], y=[4.5]*len(stack),
                            marker_color=ORANGE_DIM, marker_line_width=0,
                            name="CET1 BASE  4.5%"))
        fig.add_trace(go.Bar(x=stack["bank"], y=stack["SCB"],
                            marker_color=YELLOW, marker_line_width=0,
                            name="SCB"))
        fig.add_trace(go.Bar(x=stack["bank"], y=stack["G-SIB surcharge"],
                            marker_color=RED, marker_line_width=0,
                            name="G-SIB SURCHARGE"))
        fig.update_layout(barmode="stack",
                          **bbg_layout(
            title="STACKED CET1 MINIMUM REQUIREMENT  (% RWA)",
            height=320))
        fig.update_yaxes(title=dict(text="% RWA",
                                     font=dict(color=ORANGE, size=10)))
        st.plotly_chart(fig, width='stretch',
                        config={"displayModeBar": False})

    # ---- TLAC framework reference ----
    rows = [(k, f"{v:.2f}%", "neu") for k, v in TLAC_FRAMEWORK.items()]
    st.markdown(kv_html(rows, title="TLAC / LTD FRAMEWORK — MINIMA"),
                unsafe_allow_html=True)
