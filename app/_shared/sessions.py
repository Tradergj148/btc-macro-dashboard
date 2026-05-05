"""Trading sessions panel — NY ET clock + 4-session bars + vol intensity track.

The whole panel is a single self-contained renderer that emits one HTML block.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from _shared.style import YELLOW


# ============================================================
#  Session windows in NY ET (decimal hours, 24h clock)
# ============================================================
SESSIONS = [
    {"label": "ASIA RANGE",   "start": 20.0, "end": 24.0, "color": "#7E8C9B"},
    {"label": "LONDON",       "start":  2.0, "end":  5.0, "color": "#FF6B8A"},
    {"label": "NEW YORK AM",  "start":  9.5, "end": 12.0, "color": "#88E090"},
    {"label": "NEW YORK PM",  "start": 13.5, "end": 16.0, "color": "#C8A2D6"},
]


def render_sessions_panel() -> None:
    try:
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        now_et = datetime.now(timezone.utc)
    hour_dec = now_et.hour + now_et.minute / 60.0
    current_pct = hour_dec / 24.0 * 100.0

    active = None
    for s in SESSIONS:
        if s["start"] <= hour_dec < s["end"]:
            active = s["label"]
            break

    def _hm(h):
        hr = int(h); mn = int(round((h - hr) * 60))
        return f"{hr:02d}:{mn:02d}"

    rows_html = ""
    for s in SESSIONS:
        start_pct = s["start"] / 24 * 100
        width_pct = (s["end"] - s["start"]) / 24 * 100
        mid_pct   = start_pct + width_pct / 2
        is_active = (active == s["label"])
        active_cls = "active" if is_active else ""
        time_text = f"{_hm(s['start'])} – {_hm(s['end'] if s['end']<24 else 0)}"
        badge = ('<div class="session-active-badge">ACTIVE</div>' if is_active
                 else '<div class="session-pending-badge">—</div>')
        rows_html += (
            f'<div class="session-row {active_cls}" style="color:{s["color"]};">'
            f'<div class="session-label">{s["label"]}</div>'
            f'<div class="session-track">'
            f'<div class="session-block" style="left:{start_pct:.2f}%;width:{width_pct:.2f}%;background:{s["color"]};"></div>'
            f'<div class="session-time-text" style="left:{mid_pct:.2f}%;">{time_text}</div>'
            f'</div>'
            f'{badge}'
            f'</div>'
        )

    axis = ('<div class="session-axis">'
            '<span>00:00</span><span>06:00</span>'
            '<span>12:00</span><span>18:00</span><span>00:00</span></div>')

    # ---------- OPENING-SOON countdown ----------
    OPENING_WINDOW_MIN = 15
    opening_soon = None
    for s in SESSIONS:
        delta_min = (s["start"] - hour_dec) * 60.0
        if 0 <= delta_min <= OPENING_WINDOW_MIN:
            opening_soon = (s["label"], delta_min, s["color"])
            break
    if active:
        active_text = f"  ·  {active} ACTIVE"
    elif opening_soon:
        lbl, mins, col = opening_soon
        m = int(mins); s_ = int((mins - m) * 60)
        active_text = (
            f"  ·  <span style=\"color:{col};font-weight:700;\">{lbl} OPENS IN "
            f"{m:02d}:{s_:02d}</span>"
        )
    else:
        active_text = "  ·  Off-hours"

    # ---------- VOLUME INTENSITY OVERLAP ZONES ----------
    VOL_ZONES = [
        ( 0.0,  2.0, "ASIA TAIL",        0.30, "#3F4A55"),
        ( 2.0,  8.0, "TOKYO+LONDON",     0.55, "#5A8C9B"),
        ( 8.0, 12.0, "LONDON+NY  ★PEAK", 1.00, "#FA8B1F"),
        (12.0, 13.5, "NY LUNCH",         0.70, "#C8A2D6"),
        (13.5, 16.0, "NY MAIN",          0.85, "#88E090"),
        (16.0, 20.0, "POST-NY GAP",      0.25, "#2A2A2A"),
        (20.0, 24.0, "ASIA OPEN",        0.50, "#7E8C9B"),
    ]
    current_vol = next((z for z in VOL_ZONES if z[0] <= hour_dec < z[1]), None)
    cur_label = current_vol[2] if current_vol else "—"
    cur_intensity = current_vol[3] if current_vol else 0

    vol_zones_html = ""
    for s, e, lbl, intensity, color in VOL_ZONES:
        start_pct = s / 24 * 100
        width_pct = (e - s) / 24 * 100
        mid_pct = start_pct + width_pct / 2
        opacity = 0.35 + intensity * 0.65
        is_now = current_vol is not None and current_vol[0] == s
        glow = "box-shadow: 0 0 8px currentColor;" if is_now else ""
        vol_zones_html += (
            f'<div class="vol-zone" style="left:{start_pct:.2f}%;width:{width_pct:.2f}%;'
            f'background:{color};opacity:{opacity:.2f};color:{color};{glow}"></div>'
            f'<div class="vol-zone-text" style="left:{mid_pct:.2f}%;">{lbl}</div>'
        )

    if cur_intensity >= 0.85:
        meter_text, meter_color = "PEAK VOL", "#FA8B1F"
    elif cur_intensity >= 0.65:
        meter_text, meter_color = "HIGH VOL", "#88E090"
    elif cur_intensity >= 0.40:
        meter_text, meter_color = "MED VOL",  "#C8A2D6"
    else:
        meter_text, meter_color = "LOW VOL",  "#7E8C9B"

    vol_intensity_html = (
        f'<div class="vol-intensity-row">'
        f'<div class="vol-intensity-label">VOL INTENSITY</div>'
        f'<div class="vol-intensity-track">'
        f'{vol_zones_html}'
        f'</div>'
        f'<div class="vol-intensity-meter" style="background:{meter_color};color:#000;">{meter_text}</div>'
        f'</div>'
    )

    low_warn_html = ""
    if cur_intensity < 0.40:
        low_warn_html = (
            f'<div style="background:rgba(255,235,59,0.10);'
            f'border:1px solid {YELLOW};color:{YELLOW};'
            f'padding:4px 10px;font-size:10px;letter-spacing:0.12em;'
            f'font-weight:700;margin-bottom:8px;text-align:center;">'
            f'⚠️  LOW LIQUIDITY WINDOW ({cur_label}) — WIDER SPREADS · FALSE BREAKOUTS LIKELY · DEFER FRESH ENTRIES'
            f'</div>'
        )

    now_line_html = (
        f'<div class="sessions-now-line" '
        f'style="--now-pct:{current_pct/100.0:.4f};"></div>'
    )
    panel_html = (
        f'<div class="sessions-panel">'
        f'<div class="sessions-title">'
        f'<span>TRADING SESSIONS &amp; VOL INTENSITY — NY TIME (ET)</span>'
        f'<span class="now-badge">NOW: {now_et.strftime("%H:%M")} ET'
        f'  ·  {cur_label} ({meter_text})'
        f'  {active_text}</span>'
        f'</div>'
        f'<div class="sessions-rows">'
        f'  {vol_intensity_html}'
        f'  {rows_html}'
        f'  {now_line_html}'
        f'</div>'
        f'{axis}'
        f'</div>'
        f'{low_warn_html}'
    )
    st.markdown(panel_html, unsafe_allow_html=True)
