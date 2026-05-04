"""Layer 3 — BTC microstructure (ETF flows, OI, funding, options)."""
from __future__ import annotations

import pandas as pd
from src.utils import zscore, squash


def micro_score(
    etf_total: pd.Series | None,
    funding_blend: pd.Series | None,
    oi_usd: pd.Series | None,
    dvol: pd.Series | None,
    btc_price: pd.Series | None,
) -> pd.Series:
    parts = []

    # ETF flows: rising rolling sum is bullish
    if etf_total is not None and not etf_total.empty:
        sum5 = etf_total.rolling(5).sum()
        parts.append(zscore(sum5))

    # Funding: extreme positive funding = crowded long → bearish (invert)
    if funding_blend is not None and not funding_blend.empty:
        parts.append(zscore(-funding_blend))

    # OI: rising OI alone is ambiguous; but combined with price up = momentum.
    if oi_usd is not None and not oi_usd.empty and btc_price is not None:
        df = pd.concat({"oi": oi_usd, "px": btc_price}, axis=1).ffill().dropna()
        if not df.empty:
            oi_chg = df["oi"].pct_change(5)
            px_chg = df["px"].pct_change(5)
            momo = (oi_chg * px_chg.apply(lambda x: 1 if x > 0 else -1))
            parts.append(zscore(momo))

    # DVOL: extremely high IV = panic = contrarian buy (invert)
    if dvol is not None and not dvol.empty:
        parts.append(zscore(-dvol))

    if not parts:
        return pd.Series(dtype=float)

    avg_z = pd.concat(parts, axis=1).mean(axis=1)
    return squash(avg_z).rename("micro_score")
