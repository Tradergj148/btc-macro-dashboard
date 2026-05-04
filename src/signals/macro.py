"""Layer 1 — macro liquidity regime score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils import zscore, squash, diff_n


def net_liquidity(walcl: pd.Series, rrp: pd.Series, tga: pd.Series) -> pd.Series:
    """Fed Net Liquidity = Balance Sheet - RRP - TGA (in $bn)."""
    df = pd.concat({"walcl": walcl, "rrp": rrp, "tga": tga}, axis=1).ffill()
    return (df["walcl"] - df["rrp"] - df["tga"]).rename("net_liquidity")


def macro_score(macro_df: pd.DataFrame) -> pd.Series:
    """Combine macro indicators into a single score in [-1, 1].

    Expects columns: real_yield_10y, fed_balance_sheet, rrp, tga,
                     breakeven_5y, dxy, m2_us
    Missing columns are simply skipped.
    """
    parts = []

    if "real_yield_10y" in macro_df:
        # falling real yield is bullish → invert
        z = zscore(-diff_n(macro_df["real_yield_10y"], 60))
        parts.append(z)

    if {"fed_balance_sheet", "rrp", "tga"}.issubset(macro_df.columns):
        nl = net_liquidity(
            macro_df["fed_balance_sheet"], macro_df["rrp"], macro_df["tga"]
        )
        z = zscore(diff_n(nl, 28))
        parts.append(z)
    elif "fed_balance_sheet" in macro_df:
        z = zscore(diff_n(macro_df["fed_balance_sheet"], 28))
        parts.append(z)

    if "breakeven_5y" in macro_df:
        z = zscore(diff_n(macro_df["breakeven_5y"], 60))
        parts.append(z)

    if "dxy" in macro_df:
        # falling DXY is bullish → invert
        z = zscore(-macro_df["dxy"].pct_change(60))
        parts.append(z)

    if "m2_us" in macro_df:
        z = zscore(macro_df["m2_us"].pct_change(252))
        parts.append(z)

    if not parts:
        return pd.Series(dtype=float)

    avg_z = pd.concat(parts, axis=1).mean(axis=1)
    return squash(avg_z).rename("macro_score")
