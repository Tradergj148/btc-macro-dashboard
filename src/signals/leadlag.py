"""Layer 4 — Lead/lag cross-market proxies (MSTR, COIN, miners, ETH/BTC, stables).

v0.3 fixes
----------
- BTC trades 24/7, MSTR/COIN/miners trade weekdays.  Resample everything
  to a daily UTC index and forward-fill so the spreads are computed on
  aligned dates (instead of mixed gaps creating spurious end-point moves).
- Average BOTH 20-day and 60-day spreads — short window catches turns,
  long window stabilises against single-print whipsaw.
- Clip per-component z-scores at ±3 before averaging so one outlier
  print can't dominate the composite.
- Soften the squash with /3 instead of /2 so day-to-day moves stay smaller.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from src.utils import zscore, squash


def _daily(s: pd.Series | None) -> pd.Series | None:
    if s is None or s.empty:
        return None
    s = s.copy()
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index)
    # ensure a single tz / no-tz convention
    if s.index.tz is not None:
        s.index = s.index.tz_convert(None)
    return s.resample("D").last().ffill()


def _spread_z(proxy: pd.Series, btc: pd.Series, window: int) -> pd.Series:
    pr = proxy.pct_change(window)
    br = btc.pct_change(window)
    spread = (pr - br).dropna()
    z = zscore(spread).clip(-3.0, 3.0)
    return z


def leadlag_score(
    btc_price: pd.Series,
    mstr: pd.Series | None,
    coin: pd.Series | None,
    miners: pd.Series | None,
    eth_btc: pd.Series | None,
    stable_supply: pd.Series | None,
) -> pd.Series:
    btc = _daily(btc_price)
    if btc is None or btc.empty:
        return pd.Series(dtype=float)

    parts: list[pd.Series] = []

    # ---- equity proxies: dual-horizon spread ----
    for proxy in (mstr, coin, miners):
        proxy_d = _daily(proxy)
        if proxy_d is None:
            continue
        z20 = _spread_z(proxy_d, btc, 20)
        z60 = _spread_z(proxy_d, btc, 60)
        combined = pd.concat([z20, z60], axis=1).mean(axis=1)
        parts.append(combined)

    # ---- ETH/BTC ratio: late-cycle indicator ----
    eth_btc_d = _daily(eth_btc)
    if eth_btc_d is not None:
        z20 = zscore(eth_btc_d.pct_change(20)).clip(-3.0, 3.0)
        z60 = zscore(eth_btc_d.pct_change(60)).clip(-3.0, 3.0)
        parts.append(pd.concat([z20, z60], axis=1).mean(axis=1))

    # ---- stable-coin dry powder ----
    stable_d = _daily(stable_supply)
    if stable_d is not None:
        z = zscore(stable_d.pct_change(20)).clip(-3.0, 3.0)
        parts.append(z)

    if not parts:
        return pd.Series(dtype=float)

    avg_z = pd.concat(parts, axis=1).mean(axis=1).clip(-3.0, 3.0)
    # softer squash (/3 instead of /2) so the layer is calmer day-to-day
    out = pd.Series(np.tanh(avg_z.to_numpy() / 3.0), index=avg_z.index,
                    name="leadlag_score")
    return out
