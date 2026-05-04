"""Smoke tests — verify modules import cleanly and signals work on synthetic data."""
import numpy as np
import pandas as pd

from src.utils import zscore, squash
from src.signals.macro import macro_score, net_liquidity
from src.signals.risk_curve import risk_curve_score
from src.signals.micro import micro_score
from src.signals.leadlag import leadlag_score
from src.signals.extremes import extreme_triggers, extremes_score
from src.scoring import composite_score, label_bias, position_sizing
from src.backtest import run_backtest


def _toy_df(cols, n=600):
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {c: 100 + rng.standard_normal(n).cumsum() for c in cols}, index=idx
    )


def test_zscore_squash():
    s = pd.Series(np.linspace(-10, 10, 300))
    z = zscore(s, window=60)
    assert z.notna().any()
    sq = squash(z.dropna())
    assert sq.between(-1, 1).all()


def test_macro_score_runs():
    df = _toy_df(["real_yield_10y", "fed_balance_sheet", "rrp", "tga", "breakeven_5y", "dxy", "m2_us"])
    s = macro_score(df)
    assert s.notna().any()
    assert s.between(-1, 1).all()


def test_risk_curve_score_runs():
    df = _toy_df(["hy_oas", "vix", "arkk", "spy", "iwm", "soxx", "xlp", "copper", "gold"])
    s = risk_curve_score(df)
    assert s.notna().any()


def test_micro_score_runs():
    n = 400
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(0)
    s = micro_score(
        etf_total=pd.Series(rng.standard_normal(n) * 50, index=idx),
        funding_blend=pd.Series(rng.standard_normal(n) * 0.0001, index=idx),
        oi_usd=pd.Series(20e9 + rng.standard_normal(n).cumsum() * 1e8, index=idx),
        dvol=pd.Series(60 + rng.standard_normal(n).cumsum(), index=idx),
        btc_price=pd.Series(50000 + rng.standard_normal(n).cumsum() * 100, index=idx),
    )
    assert s.notna().any()


def test_composite_and_backtest():
    n = 400
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(7)
    btc = pd.Series(50000 * (1 + rng.standard_normal(n) * 0.02).cumprod(), index=idx)
    macro = pd.Series(np.tanh(rng.standard_normal(n).cumsum() / 10), index=idx)
    rc = pd.Series(np.tanh(rng.standard_normal(n).cumsum() / 10), index=idx)
    micro = pd.Series(np.tanh(rng.standard_normal(n).cumsum() / 10), index=idx)
    ll = pd.Series(np.tanh(rng.standard_normal(n).cumsum() / 10), index=idx)

    score = composite_score(
        macro, rc, micro, ll, extremes_value=0.0,
        weights={"macro": 0.35, "risk_curve": 0.2, "micro": 0.25, "leadlag": 0.15, "extremes": 0.05},
    )
    assert score.notna().any()
    assert label_bias(score.iloc[-1])
    assert -1 <= position_sizing(score.iloc[-1]) <= 1

    bt = run_backtest(btc, score)
    assert "stats" in bt
    assert bt["stats"]["n_days"] > 0


def test_extremes_smoke():
    funding = pd.Series(np.linspace(-0.01, 0.01, 300))
    oi = pd.Series(np.linspace(10e9, 30e9, 300))
    alerts = extreme_triggers(funding, None, oi, None,
                              {"funding_z_buy": -2, "funding_z_sell": 2,
                               "skew_extreme_pct": 5, "oi_zscore_alert": 2,
                               "mvrv_z_top": 7, "mvrv_z_bottom": 0})
    assert isinstance(alerts, pd.DataFrame)
    val = extremes_score(alerts)
    assert -1 <= val <= 1
