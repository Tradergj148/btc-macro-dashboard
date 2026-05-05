"""Risk Curve page — credit spreads, VIX, equity rotations.

Layer 2 of the compass: risk-on / risk-off barometer.
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

from _shared.page    import setup_page
from _shared.loaders import load
from _shared.charts  import line_panel, small_multiples

setup_page("Risk Curve")
st.markdown("<h1>RISK CURVE — LAYER 2</h1>", unsafe_allow_html=True)

rc = load("risk_curve_raw")
rs = load("risk_curve_score")

if rc.empty:
    st.info("Risk curve data not yet pulled. Run `python -m src.pipeline`.")
    st.stop()

c_a, c_b = st.columns(2)
with c_a:
    sm = small_multiples(rc.tail(1500),
        ["hy_oas", "vix", "arkk", "spy", "iwm", "soxx"],
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
