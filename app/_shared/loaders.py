"""Cached parquet/json loaders. Single source of truth for the data plane.

All pages read via these helpers. Caches are scoped per-process by Streamlit
and keyed on the dataset name, so repeated calls within a session are free.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ROOT = project root (parent of app/_shared/ -> app/ -> project)
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@st.cache_data(ttl=600)
def load(name: str) -> pd.DataFrame:
    """Load a parquet dataset by name (no extension).

    Returns an empty DataFrame if the file is absent -- pages should
    branch on ``df.empty`` and render a stub when so.
    """
    p = DATA / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_summary() -> dict:
    """Load the latest pipeline summary JSON (regime score, components, btstats).

    Defensive against OneDrive-style file padding: if the file shrank between
    writes, OneDrive on Windows can leave trailing NUL bytes after the new
    content. We strip whitespace + NUL bytes before parsing, and on any parse
    error we fall back to the JSON content up to the first balanced closing
    brace.
    """
    p = DATA / "summary.json"
    if not p.exists():
        return {}
    raw = p.read_bytes().rstrip(b"\x00 \r\n\t").decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        last_brace = raw.rfind("}")
        if last_brace > 0:
            try:
                return json.loads(raw[: last_brace + 1])
            except json.JSONDecodeError:
                pass
        return {}
