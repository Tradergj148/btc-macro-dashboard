"""Yahoo Finance fetcher (yfinance)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def fetch_close(tickers: dict[str, str], start: str = "2015-01-01") -> pd.DataFrame:
    """tickers = {nice_name: yahoo_symbol}. Returns wide adj-close DataFrame."""
    syms = list(tickers.values())
    raw = yf.download(syms, start=start, progress=False, auto_adjust=True, threads=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]].rename(columns={"Close": syms[0]})
    rename = {v: k for k, v in tickers.items()}
    close = close.rename(columns=rename)
    return close.sort_index().ffill()
