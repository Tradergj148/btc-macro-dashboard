"""Sessions page — trading windows, vol intensity, future home for catalysts.

Detached version of the panel that already shows in Compass; here it gets
the full page and room for future macro-catalyst calendar work.
"""
from __future__ import annotations

# Path bootstrap ──────────────────────────────────────────────────────
import sys
from pathlib import Path
_APP_DIR = Path(__file__).resolve().parents[1]
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# ─────────────────────────────────────────────────────────────────────

import streamlit as st

from _shared.page     import setup_page
from _shared.sessions import render_sessions_panel
from _shared.style    import ORANGE_DIM, TEXT_DIM

setup_page("Sessions")
st.markdown("<h1>TRADING SESSIONS &amp; CATALYSTS — TIMING LAYER</h1>",
            unsafe_allow_html=True)

# Live sessions panel (NY ET clock, vol intensity, low-liquidity warning)
render_sessions_panel()

# Placeholder for future catalysts panel
st.markdown(f"""
<div class="panel">
    <div class="panel-title">CATALYST CALENDAR  (PLANNED)</div>
    <div style="color:{TEXT_DIM};font-size:11px;line-height:1.6;padding:6px 0;">
        Upcoming high-impact macro events on a 2-week horizon will land here:
        FOMC · CPI · NFP · ECB · BoJ · China data drops · monthly options expiry
        (OPEX) dates · major earnings windows. Not predictive — just context, so
        you know &quot;we&apos;re 3 days from CPI&quot; without leaving the dashboard.
        <br><br>
        <span style="color:{ORANGE_DIM};">Wired in a future iteration once a
        free / low-friction calendar feed is selected (econoday-style).</span>
    </div>
</div>
""", unsafe_allow_html=True)
