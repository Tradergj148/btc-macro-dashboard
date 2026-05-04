"""Derivatives microstructure: funding, open interest, options skew.

All endpoints are free / public. If any fail (often rate-limited from GH Actions),
the pipeline degrades gracefully — the dashboard will mark them n/a.
"""
from __future__ import annotations

import time
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


# ---------- FUNDING ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def funding_binance(symbol: str = "BTCUSDT", limit: int = 1000) -> pd.DataFrame:
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    r = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=15)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms")
    df["fundingRate"] = pd.to_numeric(df["fundingRate"])
    df = df.set_index("fundingTime")[["fundingRate"]].rename(columns={"fundingRate": "binance"})
    return df


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def funding_bybit(symbol: str = "BTCUSDT", limit: int = 200) -> pd.DataFrame:
    url = "https://api.bybit.com/v5/market/funding/history"
    r = requests.get(
        url,
        params={"category": "linear", "symbol": symbol, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json().get("result", {}).get("list", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(pd.to_numeric(df["fundingRateTimestamp"]), unit="ms")
    df["fundingRate"] = pd.to_numeric(df["fundingRate"])
    return df.set_index("t")[["fundingRate"]].rename(columns={"fundingRate": "bybit"})


def fetch_funding_blend() -> pd.DataFrame:
    """Average funding across exchanges, daily."""
    frames = []
    for fn in (funding_binance, funding_bybit):
        try:
            frames.append(fn())
            time.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            print(f"[funding] {fn.__name__} failed: {e}")
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, axis=1).sort_index()
    daily = df.resample("D").mean()
    daily["funding_blend"] = daily.mean(axis=1)
    return daily


# ---------- OPEN INTEREST ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def oi_binance(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 500) -> pd.DataFrame:
    """Aggregate USDT-margined BTC perp open interest from Binance."""
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    r = requests.get(
        url,
        params={"symbol": symbol, "period": period, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["oi_usd"] = pd.to_numeric(df["sumOpenInterestValue"])
    return df.set_index("t")[["oi_usd"]].rename(columns={"oi_usd": "oi_binance_usd"})


# ---------- DERIBIT IMPLIED VOL ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def deribit_dvol(currency: str = "BTC", days: int = 365) -> pd.DataFrame:
    """Deribit's volatility index (DVOL) — daily."""
    end = int(time.time() * 1000)
    start = end - days * 24 * 3600 * 1000
    url = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
    r = requests.get(
        url,
        params={
            "currency": currency,
            "resolution": 86400,
            "start_timestamp": start,
            "end_timestamp": end,
        },
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json().get("result", {}).get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"])
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    return df.set_index("t")[["close"]].rename(columns={"close": "dvol"})


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def deribit_skew_proxy(currency: str = "BTC") -> pd.DataFrame:
    """Approximate 25-delta skew snapshot from Deribit option book summary.

    Returns a one-row DataFrame: latest IV(call25) - IV(put25) per expiry.
    For a richer historical skew curve, plug in a paid Deribit Volatility Index feed.
    """
    url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
    r = requests.get(url, params={"currency": currency, "kind": "option"}, timeout=20)
    r.raise_for_status()
    rows = r.json().get("result", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "mark_iv" not in df.columns:
        return pd.DataFrame()
    # crude bucket: nearest expiry only
    df["expiry"] = df["instrument_name"].str.split("-").str[1]
    df = df.dropna(subset=["mark_iv"])
    nearest = df.sort_values("expiry").groupby("expiry").head(50)
    skew_now = (
        nearest.groupby(["expiry", df["instrument_name"].str.endswith("-C").map({True: "C", False: "P"})])
        ["mark_iv"]
        .mean()
        .unstack()
    )
    skew_now["skew_25d_proxy"] = skew_now.get("C", 0) - skew_now.get("P", 0)
    skew_now["t"] = pd.Timestamp.utcnow().normalize()
    return skew_now.reset_index().set_index("t")
