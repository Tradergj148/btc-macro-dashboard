"""Orchestrate: fetch all data, compute every signal, persist parquets.

Run via:    python -m src.pipeline
GH Actions: invoked nightly by .github/workflows/etl.yml
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone

import pandas as pd

from src.utils import load_config, save_parquet
from src.data import fred as fred_mod
from src.data import yahoo as yh_mod
from src.data import derivatives as dx_mod
from src.data import etf_flows as etf_mod
from src.signals.macro import macro_score
from src.signals.risk_curve import risk_curve_score
from src.signals.micro import micro_score
from src.signals.leadlag import leadlag_score
from src.signals.extremes import extreme_triggers, extremes_score
from src.scoring import composite_score, label_bias, position_sizing
from src.backtest import run_backtest


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] {fn.__name__} failed: {e}")
        return None


def _df(x) -> pd.DataFrame:
    if x is None:
        return pd.DataFrame()
    if isinstance(x, pd.DataFrame):
        return x
    if isinstance(x, pd.Series):
        return x.to_frame()
    return pd.DataFrame(x)


def _last_val(s):
    if s is None:
        return None
    if isinstance(s, pd.Series):
        s = s.dropna()
        return float(s.iloc[-1]) if not s.empty else None
    return None


def main() -> int:
    cfg = load_config()
    print("[pipeline] starting", datetime.now(timezone.utc).isoformat())

    # ---------- LAYER 1 : MACRO ----------
    macro_fred = _df(_safe(fred_mod.fetch_many, cfg["macro"]["fred_series"]))
    yh_macro   = _df(_safe(yh_mod.fetch_close, cfg["macro"]["yahoo"]))
    macro_df = pd.concat([macro_fred, yh_macro], axis=1, sort=True).sort_index().ffill()
    if not macro_df.empty:
        save_parquet(macro_df, "macro_raw")
    macro_s = macro_score(macro_df) if not macro_df.empty else pd.Series(dtype=float)
    if not macro_s.empty:
        save_parquet(macro_s.to_frame(), "macro_score")
    print(f"[pipeline] macro_score points: {len(macro_s)}")

    # ---------- LAYER 2 : RISK CURVE ----------
    rc_fred = _df(_safe(fred_mod.fetch_many, cfg["risk_curve"]["fred_series"]))
    rc_yh   = _df(_safe(yh_mod.fetch_close, cfg["risk_curve"]["yahoo"]))
    risk_df = pd.concat([rc_fred, rc_yh], axis=1, sort=True).sort_index().ffill()
    if not risk_df.empty:
        save_parquet(risk_df, "risk_curve_raw")
    rc_s = risk_curve_score(risk_df) if not risk_df.empty else pd.Series(dtype=float)
    if not rc_s.empty:
        save_parquet(rc_s.to_frame(), "risk_curve_score")
    print(f"[pipeline] risk_curve_score points: {len(rc_s)}")

    # ---------- LAYER 3 : BTC MICROSTRUCTURE ----------
    # BTC price via Yahoo (CoinGecko free tier now requires demo key)
    btc_yh = _df(_safe(yh_mod.fetch_close, {"btc": "BTC-USD"}, "2014-01-01"))
    btc_price = btc_yh["btc"] if "btc" in btc_yh.columns else pd.Series(dtype=float)
    if not btc_price.empty:
        save_parquet(btc_price.to_frame("btc_price"), "btc_price")

    funding = _df(_safe(dx_mod.fetch_funding_blend))
    if not funding.empty:
        save_parquet(funding, "funding")
    funding_blend = funding["funding_blend"] if "funding_blend" in funding.columns else None

    oi = _df(_safe(dx_mod.oi_binance))
    if not oi.empty:
        save_parquet(oi, "open_interest")
    oi_series = oi["oi_binance_usd"] if "oi_binance_usd" in oi.columns else None

    dvol = _df(_safe(dx_mod.deribit_dvol))
    if not dvol.empty:
        save_parquet(dvol, "dvol")
    dvol_s = dvol["dvol"] if "dvol" in dvol.columns else None

    etf = _df(_safe(etf_mod.fetch_etf_flows))
    if not etf.empty:
        save_parquet(etf, "etf_flows")
    etf_total = etf["Total"] if "Total" in etf.columns else None

    micro_s = micro_score(
        etf_total=etf_total,
        funding_blend=funding_blend,
        oi_usd=oi_series,
        dvol=dvol_s,
        btc_price=btc_price,
    )
    if not micro_s.empty:
        save_parquet(micro_s.to_frame(), "micro_score")
    print(f"[pipeline] micro_score points: {len(micro_s)}")

    # ---------- LAYER 4 : LEAD/LAG ----------
    ll_yh = _df(_safe(yh_mod.fetch_close, cfg["leadlag"]["yahoo"]))
    if not ll_yh.empty:
        save_parquet(ll_yh, "leadlag_raw")
    miners_basket = None
    if not ll_yh.empty:
        miner_cols = [c for c in ("mara", "riot", "clsk") if c in ll_yh.columns]
        if miner_cols:
            miners_basket = ll_yh[miner_cols].pct_change().mean(axis=1).add(1).cumprod()

    # ETH price via Yahoo
    eth_yh = _df(_safe(yh_mod.fetch_close, {"eth": "ETH-USD"}, "2017-01-01"))
    eth_btc_ratio = None
    if "eth" in eth_yh.columns and not btc_price.empty:
        eth_btc_ratio = (eth_yh["eth"] / btc_price).dropna().rename("eth_btc")

    # Stablecoin supply: skipped (CoinGecko free tier rate-limits aggressively).
    # TODO: replace with DefiLlama free API or Glassnode-free.
    stable_supply = None

    ll_s = leadlag_score(
        btc_price=btc_price,
        mstr=ll_yh["mstr"] if "mstr" in ll_yh.columns else None,
        coin=ll_yh["coin"] if "coin" in ll_yh.columns else None,
        miners=miners_basket,
        eth_btc=eth_btc_ratio,
        stable_supply=stable_supply,
    )
    if not ll_s.empty:
        save_parquet(ll_s.to_frame(), "leadlag_score")
    print(f"[pipeline] leadlag_score points: {len(ll_s)}")

    # ---------- LAYER 5 : EXTREMES ----------
    skew_proxy = _df(_safe(dx_mod.deribit_skew_proxy))
    skew_series = skew_proxy["skew_25d_proxy"] if "skew_25d_proxy" in skew_proxy.columns else None
    alerts = extreme_triggers(
        funding_blend=funding_blend,
        skew_25d=skew_series,
        oi_usd=oi_series,
        mvrv_z=None,
        cfg=cfg["extremes"],
    )
    if not alerts.empty:
        save_parquet(alerts.assign(asof=pd.Timestamp.now(tz="UTC")).set_index("asof"),
                     "alerts")
    ex_val = extremes_score(alerts)

    # ---------- COMPOSITE ----------
    regime = composite_score(
        macro=macro_s, risk_curve=rc_s, micro=micro_s, leadlag=ll_s,
        extremes_value=ex_val, weights=cfg["weights"],
    )
    if not regime.empty:
        save_parquet(regime.to_frame(), "regime_score")

    last_score = float(regime.dropna().iloc[-1]) if not regime.dropna().empty else 0.0
    summary = {
        "asof": datetime.now(timezone.utc).isoformat(),
        "regime_score": last_score,
        "bias": label_bias(last_score),
        "position_weight": position_sizing(last_score),
        "components": {
            "macro":      _last_val(macro_s),
            "risk_curve": _last_val(rc_s),
            "micro":      _last_val(micro_s),
            "leadlag":    _last_val(ll_s),
            "extremes":   ex_val,
        },
    }

    # ---------- BACKTEST ----------
    if not btc_price.empty and not regime.empty:
        bt = run_backtest(btc_price, regime)
        if bt:
            save_parquet(bt["df"], "backtest")
            summary["backtest_stats"] = bt["stats"]

    with open("data/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print("[pipeline] done. summary:")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
