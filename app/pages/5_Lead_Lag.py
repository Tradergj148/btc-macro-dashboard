"""Lead/Lag page — MSTR, COIN, miners, ETH/BTC, stable supply.

Layer 4 of the compass: cross-asset proxies that lead or lag BTC.
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
from _shared.charts  import line_panel
from _shared.style   import ORANGE

setup_page("Lead / Lag")
st.markdown("<h1>LEAD / LAG — LAYER 4</h1>", unsafe_allow_html=True)

ll  = load("leadlag_raw")
lls = load("leadlag_score")

if ll.empty and lls.empty:
    st.info("Lead/lag data not yet pulled. Run `python -m src.pipeline`.")
    st.stop()

if not ll.empty:
    cols = [c for c in ("mstr", "coin", "mara", "riot", "clsk", "btc_cme")
            if c in ll.columns]
    if cols:
        norm = ll[cols].dropna()
        if not norm.empty:
            norm = norm / norm.iloc[0]
            st.plotly_chart(line_panel(norm.tail(750),
                "PROXY UNIVERSE — INDEXED TO 100"),
                width='stretch', config={"displayModeBar": False})

if not lls.empty:
    st.plotly_chart(line_panel(lls.tail(1000), "LEAD/LAG SCORE",
                               palette=[ORANGE]),
                    width='stretch',
                    config={"displayModeBar": False})
