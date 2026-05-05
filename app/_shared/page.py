"""One-call page setup.

Every page (Compass.py + pages/*.py) starts with::

    from _shared.page import setup_page
    summary = setup_page("Macro")

That handles st.set_page_config, CSS injection, topbar / status / regime
strip, and returns the cached pipeline summary dict so the page body can
re-use it without a second read.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


def _ensure_app_on_path() -> None:
    """Make ``app/`` importable from every page (pages/ subdir or root).

    Streamlit runs the entry script with its own dir on sys.path; pages live
    in app/pages/ and can normally already import _shared, but we add the
    parent dir explicitly so this works regardless of how the user launches
    streamlit.
    """
    here = Path(__file__).resolve()
    app_dir = here.parents[1]  # _shared/page.py → _shared/ → app/
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))


_ensure_app_on_path()


def setup_page(page_title: str = "BTC Compass",
               show_regime_strip: bool = True) -> dict:
    """Configure page, inject CSS, render persistent chrome, return summary."""
    st.set_page_config(
        page_title=f"BTC // {page_title.upper()}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Lazy imports keep the module side-effect free until called
    from _shared.style import inject_css
    from _shared.chrome import render_chrome

    inject_css()
    return render_chrome(show_regime_strip=show_regime_strip)
