"""Options layer signals — term structure, skew, GEX → composite [-1,+1].

Each sub-signal lives in [-1, +1].  Bullish reads are positive.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils import zscore, squash


# ------------------------------------------------------------------
#  TERM STRUCTURE
#  contango (long-end > short-end)  → calm                    bullish
#  backwardation (short-end > long-end) → near-term stress    bearish
# ------------------------------------------------------------------
def term_structure_score(term: pd.DataFrame) -> float:
    if term is None or term.empty or "atm_iv" not in term.columns:
        return 0.0
    df = term.dropna(subset=["atm_iv", "dte_days"]).sort_values("dte_days")
    if len(df) < 2:
        return 0.0

    short = df[df["dte_days"] <= 14]
    long_ = df[(df["dte_days"] >= 60) & (df["dte_days"] <= 180)]
    if short.empty or long_.empty:
        return 0.0

    iv_short = float(short["atm_iv"].iloc[0])
    iv_long  = float(long_["atm_iv"].iloc[-1])
    if iv_long <= 0:
        return 0.0

    ratio = iv_short / iv_long           # > 1 = backwardation = bearish
    # squash centred at 1: ratio of 1.0 -> 0; 1.3 -> -1; 0.7 -> +1
    z = (1.0 - ratio) * 3.3
    return float(np.tanh(z))


# ------------------------------------------------------------------
#  SKEW CURVE
#  positive 25d skew (calls > puts) → call-heavy, FOMO        mildly bearish (frothy)
#  deeply negative skew (puts > calls) → fear-bid             mildly bullish (contrarian)
#  near zero with mild positive bias is the healthy regime
# ------------------------------------------------------------------
def skew_score(skew: pd.DataFrame) -> float:
    if skew is None or skew.empty or "skew_25d" not in skew.columns:
        return 0.0
    df = skew.dropna(subset=["skew_25d", "dte_days"]).sort_values("dte_days")
    if df.empty:
        return 0.0

    # short-dated skew is the most reactive
    short = df[df["dte_days"] <= 30]
    sk = float(short["skew_25d"].mean()) if not short.empty else float(df["skew_25d"].iloc[0])

    # Convention: BTC tends to run mild-positive call skew in calm regimes.
    # Strong negative skew = put hedging panic = contrarian buy.
    # Strong positive skew = blow-off-top buying = caution.
    # Map vol-points (typically ±0.10 of vol) to a [-1, +1] regime score.
    return float(np.tanh(-sk * 8.0))   # invert so panic → positive (contrarian)


# ------------------------------------------------------------------
#  GAMMA EXPOSURE
#  GEX > 0 (positive-gamma regime) → vol-suppressing, mean-reverting → bullish stable
#  GEX < 0 (negative-gamma regime) → vol-amplifying, trending → bearish if extending
# ------------------------------------------------------------------
def gex_score(gex_total_history: pd.Series | float | None) -> float:
    """Accepts either a single float (live) or a Series (history-derived z-score)."""
    if gex_total_history is None:
        return 0.0
    if isinstance(gex_total_history, pd.Series):
        s = gex_total_history.dropna()
        if s.empty:
            return 0.0
        if len(s) >= 30:
            z = zscore(s).iloc[-1]
            if pd.isna(z):
                z = 0.0
            return float(np.tanh(float(z) / 2.0))
        # not enough history yet — fall back to sign
        last = float(s.iloc[-1])
        return float(np.tanh(last / 1e10))
    val = float(gex_total_history)
    return float(np.tanh(val / 1e10))


# ------------------------------------------------------------------
#  COMPOSITE OPTIONS SCORE
# ------------------------------------------------------------------
def options_composite_score(
    term: pd.DataFrame,
    skew: pd.DataFrame,
    gex_total_or_history,
    weights: dict | None = None,
) -> dict:
    weights = weights or {"term": 0.40, "skew": 0.30, "gex": 0.30}

    ts = term_structure_score(term)
    sk = skew_score(skew)
    gx = gex_score(gex_total_or_history)

    composite = (
        weights["term"] * ts + weights["skew"] * sk + weights["gex"] * gx
    )
    composite = float(np.clip(composite, -1.0, 1.0))
    return {
        "term_score": ts,
        "skew_score": sk,
        "gex_score":  gx,
        "options_composite": composite,
    }
