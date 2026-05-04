"""Backtest the composite regime score vs BTC buy-and-hold.

Daily rebalanced position = position_sizing(regime_score). Fees + slippage approximated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from src.scoring import position_sizing


def run_backtest(
    btc_price: pd.Series,
    regime_score: pd.Series,
    fee_bps: float = 5.0,
) -> dict:
    df = pd.concat({"price": btc_price, "score": regime_score}, axis=1).dropna()
    if df.empty:
        return {}
    df["pos"] = df["score"].apply(position_sizing).shift(1).fillna(0)
    df["ret"] = df["price"].pct_change().fillna(0)
    df["strat_ret"] = df["pos"] * df["ret"]
    df["turnover"] = df["pos"].diff().abs().fillna(0)
    df["strat_ret"] -= df["turnover"] * (fee_bps / 1e4)

    df["equity"] = (1 + df["strat_ret"]).cumprod()
    df["bh_equity"] = (1 + df["ret"]).cumprod()

    daily = df["strat_ret"]
    sharpe = (daily.mean() / daily.std()) * np.sqrt(365) if daily.std() > 0 else np.nan
    cum = df["equity"].iloc[-1] - 1
    bh_cum = df["bh_equity"].iloc[-1] - 1
    max_dd = (df["equity"] / df["equity"].cummax() - 1).min()
    bh_max_dd = (df["bh_equity"] / df["bh_equity"].cummax() - 1).min()

    return {
        "df": df,
        "stats": {
            "strategy_total_return": float(cum),
            "buyhold_total_return": float(bh_cum),
            "strategy_sharpe": float(sharpe) if not np.isnan(sharpe) else None,
            "strategy_max_drawdown": float(max_dd),
            "buyhold_max_drawdown": float(bh_max_dd),
            "n_days": int(len(df)),
        },
    }
