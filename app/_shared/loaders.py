"""Cached parquet/json loaders. Single source of truth for the data plane.

All pages read via these helpers. Caches are scoped per-process by Streamlit
and keyed on the dataset name, so repeated calls within a session are free.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ROOT = project root (parent of app/_shared/ → app/ → project)
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@st.cache_data(ttl=600)
def load(name: str) -> pd.DataFrame:
    """Load a parquet dataset by name (no extension).

    Returns an empty DataFrame if the file is absent — pages should
    branch on ``df.empty`` and render a stub when so.
    """
    p = DATA / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_summary() -> dict:
    """Load the latest pipeline summary JSON (regime score, components, btstats)."""
    p = DATA / "summary.json"
    return json.loads(p.read_text()) if p.exists() else {}
