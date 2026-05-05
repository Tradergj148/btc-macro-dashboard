"""Shared modules for the BTC Macro→Micro Compass dashboard.

This package holds the pieces every page consumes:
- style: palette + global CSS injection
- loaders: cached parquet/json readers (single source of truth on disk)
- charts: plotly + KV-table helpers
- chrome: top bar, status bar, compact regime strip
- sessions: trading-sessions panel (NY ET) + vol intensity
- page: one-line page-bootstrap helper

All page files (Compass.py + pages/*.py) call ``setup_page()`` from
``_shared.page`` first; that handles ``st.set_page_config``, CSS injection,
and rendering of the persistent chrome (topbar, status, regime strip).
Each page then renders only its own page-specific body.
"""
