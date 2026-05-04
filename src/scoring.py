"""Composite Regime Score — blends all 5 layers, maps to bias label.

Position sizing recognises BTC's structural up-drift:
- Default 60% long in NEUTRAL (vs 10% in v0.1)
- Lever up to ~1.5x in strong bullish regime
- Stay flat in mild bearish (avoid fighting trend)
- Only mildly short in clear bearish (BTC has historically punished outright shorts)
"""
from __future__ import annotations

import math
import pandas as pd


def composite_score(
    macro: pd.Series,
    risk_curve: pd.Series,
    micro: pd.Series,
    leadlag: pd.Series,
    extremes_value: float,
    weights: dict,
) -> pd.Series:
    df = pd.concat(
        {
            "macro":      macro,
            "risk_curve": risk_curve,
            "micro":      micro,
            "leadlag":    leadlag,
        },
        axis=1,
    ).ffill()
    w = weights
    score = (
        w["macro"]      * df["macro"].fillna(0)
        + w["risk_curve"] * df["risk_curve"].fillna(0)
        + w["micro"]      * df["micro"].fillna(0)
        + w["leadlag"]    * df["leadlag"].fillna(0)
    )
    score = score + w["extremes"] * float(extremes_value)
    return score.rename("regime_score")


def label_bias(score_value: float) -> str:
    if score_value > 0.5:    return "STRONG BULLISH"
    if score_value > 0.2:    return "BULLISH"
    if score_value > -0.2:   return "NEUTRAL"
    if score_value > -0.5:   return "BEARISH"
    return "STRONG BEARISH"


def position_sizing(score_value: float) -> float:
    """Continuous tanh sizing, asymmetric long-biased.

        pos = 0.6 + 0.8 * tanh(score * 1.5)
        clamped to [-0.5, +1.5]
    """
    pos = 0.6 + 0.8 * math.tanh(float(score_value) * 1.5)
    return max(-0.5, min(1.5, pos))
