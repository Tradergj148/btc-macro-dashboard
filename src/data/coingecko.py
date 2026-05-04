"""CoinGecko fetcher — daily price history for BTC, ETH and stablecoins."""
from __future__ import annotations

import time
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

BASE = "https://api.coingecko.com/api/v3"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_market_chart(coin_id: str, days: int | str = "max", vs: str = "usd") -> pd.DataFrame:
    url = f"{BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs, "days": days, "interval": "daily"}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    out = {}
    for key in ("prices", "market_caps", "total_volumes"):
        if key in j:
            df = pd.DataFrame(j[key], columns=["ts", key])
            df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.normalize()
            out[key] = df.set_index("date")[key]
    df = pd.concat(out, axis=1).rename(columns={
        "prices": "price", "market_caps": "mcap", "total_volumes": "volume"
    })
    df["coin"] = coin_id
    return df


def fetch_universe(coin_ids: list[str], days: int | str = "max") -> dict[str, pd.DataFrame]:
    out = {}
    for c in coin_ids:
        try:
            out[c] = fetch_market_chart(c, days=days)
            time.sleep(1.2)  # respect free-tier rate limit
        except Exception as e:  # noqa: BLE001
            print(f"[coingecko] {c} failed: {e}")
    return out
