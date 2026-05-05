"""Persistent page chrome: top bar, function-key strip, status bar, regime strip.

Every page calls ``render_chrome()`` (via ``setup_page()``) so the user always
knows: (a) what app this is, (b) what the current regime is, (c) where the
data is from. The compact 6-cell regime strip is the synthesis the rest of
the dashboard explains.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from _shared.loaders import load_summary
from _shared.style import (
    ORANGE, GREEN, RED, TEXT_DIM,
)


# ============================================================
#  REGIME-STRIP cell semantics (kept in this module so the
#  Compass page and any embedded mini-strip stay consistent)
# ============================================================
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


def render_regime_strip(summary: dict | None = None) -> None:
    """Render the compact 6-cell regime strip (composite + 5 layers)."""
    summary = summary if summary is not None else load_summary()
    regime = summary.get("regime_score")
    posw   = summary.get("position_weight")
    comps  = summary.get("components", {}) or {}
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
#  Top bar / function keys / status bar
# ============================================================
def render_topbar(version: str = "v0.8", title: str = "BTC // MACRO LIQUIDITY COMPASS") -> None:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(f"""
<div class="topbar">
    <div>BTC&nbsp;&lt;CRNCY&gt;&nbsp;&nbsp;{title} &nbsp;·&nbsp; {version}</div>
    <div class="right">{now_utc}</div>
</div>
<div class="fnstrip">
    <span class="fnkey">F1</span><span class="fnlbl">COMPASS</span>
    <span class="fnkey">F2</span><span class="fnlbl">MACRO</span>
    <span class="fnkey">F3</span><span class="fnlbl">RISK</span>
    <span class="fnkey">F4</span><span class="fnlbl">MICRO</span>
    <span class="fnkey">F5</span><span class="fnlbl">OPTIONS</span>
    <span class="fnkey">F6</span><span class="fnlbl">LEAD/LAG</span>
    <span class="fnkey">F7</span><span class="fnlbl">SESSIONS</span>
</div>
""", unsafe_allow_html=True)


def render_status(summary: dict | None = None) -> None:
    """USER / FRAMEWORK / MODE / DATA AS-OF strip."""
    summary = summary if summary is not None else load_summary()
    asof = summary.get("asof", "—")
    st.markdown(f"""
<div class="statusbar">
    <div><b>USER</b> <span>TRADERGJ148@AETHEION</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>FRAMEWORK</b> <span>CAPITAL FLOWS RESEARCH</span> &nbsp;<span class="dim">|</span>&nbsp;
         <b>MODE</b> <span>MONITOR</span></div>
    <div><b>DATA AS-OF</b> <span>{asof}</span></div>
</div>
""", unsafe_allow_html=True)


def render_chrome(summary: dict | None = None,
                  show_regime_strip: bool = True) -> dict:
    """One-call shorthand: topbar + statusbar + (optional) regime strip.

    Returns the loaded summary dict so the calling page can re-use it
    without a second JSON read.
    """
    summary = summary if summary is not None else load_summary()
    render_topbar()
    render_status(summary)
    if show_regime_strip:
        render_regime_strip(summary)
    return summary
