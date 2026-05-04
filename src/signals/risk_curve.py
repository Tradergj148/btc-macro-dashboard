"""Layer 2 — risk-curve / cross-asset risk flows."""
from __future__ import annotations

import pandas as pd
from src.utils import zscore, squash, diff_n


def risk_curve_score(risk_df: pd.DataFrame) -> pd.Series:
    """Combine risk-curve indicators into a single score in [-1, 1].

    Expected columns: hy_oas, vix, arkk, spy, iwm, soxx, xlp, xlu, copper, gold
    """
    parts = []

    if "hy_oas" in risk_df:
        # narrowing spreads = risk on → invert
        parts.append(zscore(-diff_n(risk_df["hy_oas"], 20)))

    if "vix" in risk_df:
        # falling VIX = risk on → invert
        parts.append(zscore(-risk_df["vix"].rolling(20).mean()))

    # ratios
    def _ratio(num, den):
        if num in risk_df and den in risk_df:
            r = risk_df[num] / risk_df[den]
            return zscore(r.pct_change(60))
        return None

    for n, d in [("arkk", "spy"), ("iwm", "spy"), ("soxx", "spy"), ("copper", "gold")]:
        z = _ratio(n, d)
        if z is not None:
            parts.append(z)

    if "xlp" in risk_df and "spy" in risk_df:
        # defensives outperforming = risk off → invert
        parts.append(zscore(-(risk_df["xlp"] / risk_df["spy"]).pct_change(60)))

    if not parts:
        return pd.Series(dtype=float)

    avg_z = pd.concat(parts, axis=1).mean(axis=1)
    return squash(avg_z).rename("risk_curve_score")
