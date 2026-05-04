"""Layer 4 — Lead/lag cross-market proxies (MSTR, COIN, miners, ETH/BTC, stables)."""
from __future__ import annotations

import pandas as pd
from src.utils import zscore, squash


def leadlag_score(
    btc_price: pd.Series,
    mstr: pd.Series | None,
    coin: pd.Series | None,
    miners: pd.Series | None,
    eth_btc: pd.Series | None,
    stable_supply: pd.Series | None,
) -> pd.Series:
    parts = []

    btc_ret = btc_price.pct_change(20)

    for proxy in (mstr, coin, miners):
        if proxy is None or proxy.empty:
            continue
        proxy_ret = proxy.pct_change(20)
        spread = (proxy_ret - btc_ret).dropna()
        # equity proxy outperforming BTC = leading bullishness
        parts.append(zscore(spread))

    if eth_btc is not None and not eth_btc.empty:
        # rising ETH/BTC = late-cycle risk-on (mildly bullish but mean-reverting)
        parts.append(zscore(eth_btc.pct_change(20)))

    if stable_supply is not None and not stable_supply.empty:
        # rising stable supply = dry powder = bullish setup
        parts.append(zscore(stable_supply.pct_change(20)))

    if not parts:
        return pd.Series(dtype=float)

    avg_z = pd.concat(parts, axis=1).mean(axis=1)
    return squash(avg_z).rename("leadlag_score")
