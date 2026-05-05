"""Bloomberg-Terminal palette + global CSS injection.

Every page imports ``inject_css()`` once via ``setup_page()``.
Constants (ORANGE, BG, ...) are imported directly by chart helpers.
"""
from __future__ import annotations

import streamlit as st

# ============================================================
#  CLASSIC BLOOMBERG TERMINAL PALETTE
#  - Signature orange #FA8B1F (warm, slightly red-leaning)
#  - Pure black background
#  - White-dominant data values
#  - Cyan for tickers / symbols
#  - Yellow for highlights / warnings
#  - Bright green/red for up/down
# ============================================================
ORANGE      = "#FA8B1F"
ORANGE_DIM  = "#A85708"
ORANGE_DEEP = "#C76A11"
BG          = "#000000"
PANEL_BG    = "#070707"
GRID        = "#1A1A1A"
WHITE       = "#FFFFFF"
TEXT        = "#FFFFFF"
TEXT_DIM    = "#9A9A9A"
GREEN       = "#00FF66"
RED         = "#FF1F1F"
CYAN        = "#22D3EE"
YELLOW      = "#FFEB3B"
MAGENTA     = "#FF44FF"


def inject_css() -> None:
    """Inject the full Bloomberg-Terminal CSS into the current page.

    Idempotent -- safe to call once per page render.
    """
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"], .stApp, .main, .block-container {{
    background-color: {BG} !important;
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace !important;
    font-size: 12px !important;
}}
.block-container {{
    padding-top: 0.4rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}
h1, h2, h3, h4 {{
    font-family: 'JetBrains Mono', monospace !important;
    color: {ORANGE} !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid {ORANGE_DIM};
    padding-bottom: 4px !important;
    margin-top: 8px !important;
    margin-bottom: 8px !important;
}}
h1 {{ font-size: 18px !important; }}
h2 {{ font-size: 15px !important; }}
h3 {{ font-size: 13px !important; }}
hr {{ border-color: {ORANGE_DIM} !important; }}

/* ===== TOP HEADER: solid orange with black text (Bloomberg trademark) ===== */
.topbar {{
    background: {ORANGE};
    color: {BG};
    padding: 6px 14px;
    font-weight: 700;
    letter-spacing: 0.18em;
    font-size: 13px;
    margin-bottom: 0;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid {BG};
}}
.topbar .right {{
    background: {BG};
    color: {ORANGE};
    padding: 2px 10px;
    border: 1px solid {BG};
    font-weight: 700;
}}

/* ===== Function-key strip ===== */
.fnstrip {{
    background: {BG};
    border-bottom: 1px solid {ORANGE_DIM};
    padding: 4px 8px;
    display: flex;
    gap: 6px;
    margin-bottom: 6px;
}}
.fnkey {{
    background: {ORANGE};
    color: {BG};
    padding: 1px 7px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.1em;
}}
.fnlbl {{
    color: {WHITE};
    font-size: 10px;
    margin-right: 8px;
    letter-spacing: 0.05em;
}}

/* ===== Status bar ===== */
.statusbar {{
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 5px 10px;
    font-size: 10px;
    color: {WHITE};
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    letter-spacing: 0.05em;
}}
.statusbar b {{ color: {ORANGE}; }}
.statusbar .dim {{ color: {TEXT_DIM}; }}

/* ===== Panels ===== */
.panel {{
    border: 1px solid {ORANGE_DIM};
    background: {PANEL_BG};
    padding: 8px 10px;
    margin-bottom: 6px;
}}
.panel-title {{
    color: {BG};
    background: {ORANGE};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.18em;
    padding: 3px 8px;
    margin: -8px -10px 8px -10px;
    text-transform: uppercase;
}}

/* ===== Key-value rows ===== */
.kv {{ display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dotted {GRID}; font-size: 11px; }}
.kv .k {{ color: {ORANGE}; letter-spacing: 0.05em; }}
.kv .v {{ color: {WHITE}; font-weight: 500; }}
.pos {{ color: {GREEN} !important; }}
.neg {{ color: {RED}   !important; }}
.neu {{ color: {WHITE} !important; }}
.tic {{ color: {CYAN}  !important; }}
.hl  {{ color: {YELLOW} !important; }}

/* ===== Bias banner ===== */
.bias-banner {{
    padding: 14px 8px;
    text-align: center;
    border: 1px solid {ORANGE};
    background: {PANEL_BG};
    margin-bottom: 6px;
    position: relative;
}}
.bias-banner::before {{
    content: 'REGIME';
    position: absolute;
    top: -8px; left: 8px;
    background: {BG};
    color: {ORANGE};
    font-size: 9px;
    padding: 0 6px;
    letter-spacing: 0.2em;
}}
.bias-banner .value {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.1em;
    margin-top: 2px;
}}
.bias-banner .sub {{
    font-size: 11px;
    color: {WHITE};
    margin-top: 6px;
    letter-spacing: 0.05em;
}}
.bias-banner .sub b {{ color: {WHITE}; }}

/* ===== Streamlit info / alert ===== */
div[data-testid="stAlert"] {{
    background: {PANEL_BG} !important;
    border: 1px solid {ORANGE} !important;
    color: {ORANGE} !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 0 !important;
}}
div[data-testid="stAlert"] * {{ color: {ORANGE} !important; }}

/* ===== Hide Streamlit chrome -- but keep the sidebar collapse toggle visible ===== */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
/* zero-out the header bar but don't hide its children
   (the sidebar collapse-control chevron lives in here) */
[data-testid="stHeader"] {{
    background: transparent !important;
    height: 0 !important;
}}
[data-testid="collapsedControl"] {{
    visibility: visible !important;
    color: {ORANGE} !important;
    z-index: 999 !important;
}}
[data-testid="collapsedControl"] svg {{
    fill: {ORANGE} !important;
    color: {ORANGE} !important;
}}

/* ===== Sidebar styling (multipage nav) ===== */
[data-testid="stSidebar"] {{
    background: {PANEL_BG} !important;
    border-right: 1px solid {ORANGE_DIM} !important;
}}
[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 {{
    color: {ORANGE} !important;
    border-bottom: 1px solid {ORANGE_DIM};
    text-transform: uppercase;
    letter-spacing: 0.10em;
}}
[data-testid="stSidebarNav"] a {{
    color: {WHITE} !important;
    font-size: 11px !important;
    letter-spacing: 0.10em !important;
    border-left: 2px solid transparent;
    padding-left: 6px !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
    color: {ORANGE} !important;
    border-left-color: {ORANGE} !important;
    font-weight: 700;
}}

/* ===== Tables ===== */
.dataframe, .stDataFrame {{
    background: {PANEL_BG} !important;
    color: {WHITE} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
}}

/* ===== Scrollbars ===== */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {ORANGE_DIM}; }}


/* ===== TRADING SESSIONS PANEL ===== */
.sessions-panel {{
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 8px 12px;
    margin-bottom: 8px;
    position: relative;
}}
.sessions-title {{
    color: {ORANGE};
    font-size: 10px;
    letter-spacing: 0.18em;
    font-weight: 700;
    margin-bottom: 8px;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.sessions-title .now-badge {{
    color: {YELLOW};
    font-size: 11px;
    letter-spacing: 0.10em;
}}
.sessions-rows {{ position: relative; }}
.session-row {{
    display: flex;
    align-items: center;
    margin: 3px 0;
    height: 18px;
    position: relative;
}}
.session-label {{
    color: currentColor;
    font-size: 9px;
    width: 110px;
    text-align: right;
    margin-right: 12px;
    letter-spacing: 0.10em;
    font-weight: 700;
    flex-shrink: 0;
}}
.session-track {{
    flex: 1;
    height: 14px;
    background: {GRID};
    position: relative;
    border-radius: 1px;
}}
.session-block {{
    position: absolute;
    height: 100%;
    top: 0;
    border-radius: 1px;
    opacity: 0.55;
    transition: opacity .2s;
}}
.session-row.active .session-block {{
    opacity: 1.0;
    box-shadow: 0 0 6px currentColor;
}}
.session-time-text {{
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    font-size: 8px;
    color: {WHITE};
    white-space: nowrap;
    pointer-events: none;
    font-weight: 600;
    text-shadow: 0 0 2px black;
}}
.session-active-badge {{
    background: {GREEN};
    color: {BG};
    font-weight: 700;
    font-size: 8px;
    letter-spacing: 0.15em;
    padding: 1px 5px;
    margin-left: 6px;
    flex-shrink: 0;
    width: 60px;
    text-align: center;
}}
.session-pending-badge {{
    color: {TEXT_DIM};
    font-size: 8px;
    margin-left: 6px;
    width: 60px;
    text-align: center;
    flex-shrink: 0;
}}
/* single vertical DASHED NOW-line that spans every row */
.sessions-now-line {{
    position: absolute;
    top: 0;
    bottom: 0;
    left: calc(122px + (100% - 188px) * var(--now-pct, 0));
    width: 0;
    border-left: 2px dashed {YELLOW};
    z-index: 12;
    pointer-events: none;
}}
.sessions-now-line::before {{
    content: '';
    position: absolute;
    top: -4px;
    left: -5px;
    width: 8px;
    height: 8px;
    background: {YELLOW};
    border-radius: 50%;
    box-shadow: 0 0 4px {YELLOW};
}}
.sessions-now-line::after {{
    content: 'NOW';
    position: absolute;
    top: -14px;
    left: -14px;
    color: {YELLOW};
    font-size: 7px;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-shadow: 0 0 2px black;
}}
.session-axis {{
    margin-left: 122px;
    margin-top: 2px;
    color: {WHITE};
    font-size: 8px;
    display: flex;
    justify-content: space-between;
}}


/* ===== VOLUME INTENSITY OVERLAP TRACK ===== */
.vol-intensity-row {{
    display: flex;
    align-items: center;
    margin: 6px 0 8px 0;
    height: 22px;
    position: relative;
    border-bottom: 1px dotted {ORANGE_DIM};
    padding-bottom: 6px;
}}
.vol-intensity-label {{
    color: {ORANGE};
    font-size: 9px;
    width: 110px;
    text-align: right;
    margin-right: 12px;
    letter-spacing: 0.10em;
    font-weight: 700;
    flex-shrink: 0;
}}
.vol-intensity-track {{
    flex: 1;
    height: 18px;
    background: {GRID};
    position: relative;
    border-radius: 1px;
}}
.vol-zone {{
    position: absolute;
    height: 100%;
    top: 0;
    border-right: 1px solid {BG};
}}
.vol-zone-text {{
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    font-size: 7px;
    color: {WHITE};
    white-space: nowrap;
    pointer-events: none;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-shadow: 0 0 2px black;
}}
.vol-intensity-meter {{
    width: 60px;
    margin-left: 6px;
    flex-shrink: 0;
    text-align: center;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.10em;
    padding: 1px 5px;
}}


/* ===== COMPACT REGIME STRIP (6 cells, fully responsive) ===== */
.regime-strip {{
    display: flex;
    flex-wrap: nowrap;
    gap: 4px;
    margin: 8px 0;
    overflow: hidden;
}}
.regime-cell {{
    flex: 1 1 0;
    min-width: 0;
    background: {PANEL_BG};
    border: 1px solid {ORANGE_DIM};
    padding: 8px 6px 6px 6px;
    text-align: center;
    position: relative;
}}
.regime-cell.composite {{
    flex: 1.6 1 0;
    border: 2px solid {ORANGE};
    background: linear-gradient(180deg, rgba(250,139,31,0.08), {PANEL_BG} 60%);
}}
.regime-cell .rc-label {{
    color: {ORANGE};
    font-size: 9px;
    letter-spacing: 0.18em;
    font-weight: 700;
    text-transform: uppercase;
    line-height: 1;
}}
.regime-cell.composite .rc-label {{
    font-size: 10px;
    letter-spacing: 0.20em;
}}
.regime-cell .rc-bias {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.10em;
    margin-top: 4px;
    line-height: 1;
}}
.regime-cell.composite .rc-bias {{
    font-size: 14px;
    margin-top: 6px;
}}
.regime-cell .rc-score {{
    font-size: 18px;
    font-weight: 700;
    margin: 4px 0 4px;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
}}
.regime-cell.composite .rc-score {{
    font-size: 26px;
    margin: 6px 0;
}}
.regime-cell .rc-bar {{
    position: relative;
    height: 5px;
    background: {GRID};
    border-radius: 1px;
    margin: 4px 4px 2px;
    overflow: visible;
}}
.regime-cell .rc-bar::before {{
    content: '';
    position: absolute;
    left: 50%;
    top: -2px; bottom: -2px;
    width: 1px;
    background: {ORANGE_DIM};
}}
.regime-cell .rc-marker {{
    position: absolute;
    width: 8px;
    height: 12px;
    top: -3.5px;
    margin-left: -4px;
    border-radius: 1px;
}}
.regime-cell .rc-strength {{
    color: {TEXT_DIM};
    font-size: 8px;
    margin-top: 4px;
    letter-spacing: 0.15em;
    font-weight: 700;
}}
.regime-cell .rc-pos {{
    background: {YELLOW};
    color: {BG};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.15em;
    padding: 2px 6px;
    margin: 6px auto 0;
    display: inline-block;
}}

</style>
""", unsafe_allow_html=True)
