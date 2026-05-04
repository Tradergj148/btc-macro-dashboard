"""Layer 5 — positioning-extreme triggers (alerts)."""
from __future__ import annotations

import pandas as pd
from src.utils import zscore


def extreme_triggers(
    funding_blend: pd.Series | None,
    skew_25d: pd.Series | None,
    oi_usd: pd.Series | None,
    mvrv_z: pd.Series | None,
    cfg: dict,
) -> pd.DataFrame:
    """Returns a one-row alerts DataFrame with bool columns."""
    out = {}

    if funding_blend is not None and not funding_blend.empty:
        z = zscore(funding_blend).iloc[-1]
        out["funding_extreme_long"] = bool(z > cfg["funding_z_sell"])
        out["funding_extreme_short"] = bool(z < cfg["funding_z_buy"])

    if oi_usd is not None and not oi_usd.empty:
        z = zscore(oi_usd).iloc[-1]
        out["oi_extreme_high"] = bool(z > cfg["oi_zscore_alert"])

    if skew_25d is not None and not skew_25d.empty:
        last = skew_25d.iloc[-1] if hasattr(skew_25d, "iloc") else skew_25d
        out["skew_extreme_call"] = bool(last > cfg["skew_extreme_pct"])
        out["skew_extreme_put"] = bool(last < -cfg["skew_extreme_pct"])

    if mvrv_z is not None and not mvrv_z.empty:
        last = mvrv_z.iloc[-1]
        out["mvrv_top_zone"] = bool(last > cfg["mvrv_z_top"])
        out["mvrv_bottom_zone"] = bool(last < cfg["mvrv_z_bottom"])

    return pd.DataFrame([out])


def extremes_score(alerts: pd.DataFrame) -> float:
    """Tiny additive score: contrarian buys add +, blow-off tops subtract."""
    if alerts.empty:
        return 0.0
    s = 0.0
    if alerts.get("funding_extreme_short", pd.Series([False])).iloc[0]: s += 0.5
    if alerts.get("skew_extreme_put", pd.Series([False])).iloc[0]:      s += 0.5
    if alerts.get("mvrv_bottom_zone", pd.Series([False])).iloc[0]:      s += 1.0
    if alerts.get("funding_extreme_long", pd.Series([False])).iloc[0]:  s -= 0.5
    if alerts.get("skew_extreme_call", pd.Series([False])).iloc[0]:     s -= 0.5
    if alerts.get("oi_extreme_high", pd.Series([False])).iloc[0]:       s -= 0.3
    if alerts.get("mvrv_top_zone", pd.Series([False])).iloc[0]:         s -= 1.0
    # squash to [-1,1]
    return max(-1.0, min(1.0, s / 2.0))
