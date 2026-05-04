"""Composite Regime Score — blends all 5 layers, maps to bias label."""
from __future__ import annotations

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
            "macro": macro,
            "risk_curve": risk_curve,
            "micro": micro,
            "leadlag": leadlag,
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
    """Map regime score to a [-1, 1] BTC position weight (long/short fraction)."""
    if score_value > 0.5:    return 1.00
    if score_value > 0.2:    return 0.60
    if score_value > -0.2:   return 0.10
    if score_value > -0.5:   return -0.30
    return -0.60
