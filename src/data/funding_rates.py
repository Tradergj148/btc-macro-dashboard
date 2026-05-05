"""NY Fed + OFR direct fetchers -- bypass FRED for the brittle series.

Switched from /last/{n}.json to /search.json?startDate=&endDate= -- the
former has an undocumented N cap that 4xx's silently for large windows.
"""
from __future__ import annotations

import io
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

UA = {"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"}


def _diag(name, r):
    if r.status_code >= 400:
        snippet = (r.text or "")[:300].replace("\n", " ")
        print(f"[funding_rates] {name}  HTTP {r.status_code}: {snippet}")


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
def fetch_ny_fed_secured(start: str = "2018-01-01",
                         end: str | None = None) -> pd.DataFrame:
    """SOFR / BGCR / TGCR -- NY Fed Markets API search endpoint."""
    end = end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    url = (f"https://markets.newyorkfed.org/api/rates/secured/all/"
           f"search.json?startDate={start}&endDate={end}")
    r = requests.get(url, timeout=12, headers=UA)
    _diag("secured", r)
    r.raise_for_status()
    rows = r.json().get("refRates", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["effectiveDate"])
    df["rate"] = pd.to_numeric(df["percentRate"], errors="coerce")
    pivot = df.pivot_table(index="date", columns="type",
                           values="rate", aggfunc="last")
    pivot.columns = [str(c).lower() for c in pivot.columns]
    return pivot.sort_index()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
def fetch_ny_fed_unsecured(start: str = "2018-01-01",
                           end: str | None = None) -> pd.DataFrame:
    """EFFR / OBFR -- NY Fed Markets API search endpoint."""
    end = end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    url = (f"https://markets.newyorkfed.org/api/rates/unsecured/all/"
           f"search.json?startDate={start}&endDate={end}")
    r = requests.get(url, timeout=12, headers=UA)
    _diag("unsecured", r)
    r.raise_for_status()
    rows = r.json().get("refRates", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["effectiveDate"])
    df["rate"] = pd.to_numeric(df["percentRate"], errors="coerce")
    pivot = df.pivot_table(index="date", columns="type",
                           values="rate", aggfunc="last")
    pivot.columns = [str(c).lower() for c in pivot.columns]
    return pivot.sort_index()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
def fetch_ofr_fsi() -> pd.Series:
    """Daily OFR Financial Stress Index."""
    url = "https://www.financialresearch.gov/financial-stress-index/data/fsi.csv"
    r = requests.get(url, timeout=12, headers=UA)
    _diag("ofr_fsi", r)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty:
        return pd.Series(dtype=float, name="ofr_fsi")
    date_col = next((c for c in df.columns if "date" in c.lower()),
                    df.columns[0])
    fsi_col = next((c for c in df.columns
                    if "ofr" in c.lower() and "fsi" in c.lower()), None)
    if fsi_col is None:
        fsi_col = next((c for c in df.columns
                        if "fsi" in c.lower() or "stress" in c.lower()), None)
    if fsi_col is None and len(df.columns) > 1:
        fsi_col = df.columns[1]
    if fsi_col is None:
        return pd.Series(dtype=float, name="ofr_fsi")
    s = pd.Series(
        pd.to_numeric(df[fsi_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col], errors="coerce"),
        name="ofr_fsi",
    ).dropna().sort_index()
    return s


def fetch_plumbing_rates(start: str = "2018-01-01") -> pd.DataFrame:
    """Combined NY Fed + OFR plumbing rates frame.

    Columns: sofr  bgcr  tgcr  effr  obfr  ofr_fsi  (whatever subset succeeds).
    """
    parts = []
    try:
        sec = fetch_ny_fed_secured(start)
        if not sec.empty:
            parts.append(sec)
    except Exception as e:  # noqa: BLE001
        print(f"[funding_rates] NY Fed secured failed: {e}")
    try:
        unsec = fetch_ny_fed_unsecured(start)
        if not unsec.empty:
            parts.append(unsec)
    except Exception as e:  # noqa: BLE001
        print(f"[funding_rates] NY Fed unsecured failed: {e}")
    try:
        fsi = fetch_ofr_fsi()
        if not fsi.empty:
            parts.append(fsi.to_frame())
    except Exception as e:  # noqa: BLE001
        print(f"[funding_rates] OFR FSI failed: {e}")

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, axis=1).sort_index().ffill()
