"""US Spot Bitcoin ETF flows — scraped from farside.co.uk public table."""
from __future__ import annotations

import pandas as pd
import requests
from io import StringIO
from tenacity import retry, stop_after_attempt, wait_exponential

URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_etf_flows() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"}
    r = requests.get(URL, headers=headers, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(StringIO(r.text))
    if not tables:
        return pd.DataFrame()
    df = tables[0]
    # First column is the date; remaining are issuer flows in $m. Last column = Total.
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    # numeric cleanup
    for c in df.columns:
        df[c] = (
            df[c].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
            .str.replace("-", "0", regex=False)
            .replace({"": "0", "nan": "0"})
        )
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "Total" not in df.columns:
        df["Total"] = df.sum(axis=1)
    return df
