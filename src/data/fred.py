"""FRED data fetcher.

Uses the free FRED API. Requires FRED_API_KEY env var (free at https://fred.stlouisfed.org/).
Falls back to the stlouisfed CSV endpoint if the key is missing — slower but no auth needed.
"""
from __future__ import annotations

import os
import io
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

def _is_valid_fred_key(k: str) -> bool:
    """A valid FRED API key is 32 chars, lowercase alphanumeric."""
    return bool(k) and len(k) == 32 and k.isalnum() and k == k.lower()


_FRED_KEY_RAW = os.getenv("FRED_API_KEY", "")
FRED_KEY = _FRED_KEY_RAW if _is_valid_fred_key(_FRED_KEY_RAW) else ""
if _FRED_KEY_RAW and not FRED_KEY:
    print(f"[fred] FRED_API_KEY env var is malformed "
          f"(got {len(_FRED_KEY_RAW)} chars, expected 32 lowercase alphanumerics) "
          f"-- falling back to CSV endpoint (no auth). "
          f"Get a free valid key at https://fred.stlouisfed.org/docs/api/api_key.html")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_series(series_id: str, start: str = "2015-01-01") -> pd.Series:
    """Return a pandas Series indexed by date for a FRED series."""
    if FRED_KEY:
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={FRED_KEY}&file_type=json"
            f"&observation_start={start}"
        )
        r = requests.get(url, timeout=15)
        if r.status_code >= 400:
            snippet = (r.text or "")[:200].replace("\n", " ")
            print(f"[fred] {series_id}  HTTP {r.status_code}: {snippet}")
        r.raise_for_status()
        df = pd.DataFrame(r.json()["observations"])
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.set_index("date")["value"].dropna()
    else:
        # CSV fallback — no API key needed
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        r = requests.get(url, timeout=15)
        if r.status_code >= 400:
            snippet = (r.text or "")[:200].replace("\n", " ")
            print(f"[fred-csv] {series_id}  HTTP {r.status_code}: {snippet}")
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.set_index("date")["value"].dropna()
        s = s[s.index >= pd.Timestamp(start)]
    s.name = series_id
    return s


def fetch_many(series_map: dict[str, str], start: str = "2015-01-01") -> pd.DataFrame:
    """series_map = {nice_name: fred_id}. Returns wide DataFrame."""
    out = {}
    for name, sid in series_map.items():
        try:
            out[name] = fetch_series(sid, start=start)
        except Exception as e:  # noqa: BLE001
            print(f"[fred] {sid} failed: {e}")
    return pd.concat(out, axis=1).sort_index().ffill()
