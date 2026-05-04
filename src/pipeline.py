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
from src.data import coingecko as cg_mod
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
        traceback.print_exc()
        return None


def main() -> int:
    cfg = load_config()
    print("[pipeline] starting", datetime.now(timezone.utc).isoformat())

    # ---------- LAYER 1 : MACRO ----------
    fred_map = cfg["macro"]["fred_series"]
    macro_fred = _safe(fred_mod.fetch_many, fred_map) or pd.DataFrame()

    yh_macro = _safe(yh_mod.fetch_close, cfg["macro"]["yahoo"]) or pd.DataFrame()

    macro_df = pd.concat([macro_fred, yh_macro], axis=1).sort_index().ffill()
    save_parquet(macro_df, "macro_raw")
    macro_s = macro_score(macro_df)
    save_parquet(macro_s.to_frame(), "macro_score")
    print(f"[pipeline] macro_score points: {len(macro_s)}")

    # ---------- LAYER 2 : RISK CURVE ----------
    rc_fred = _safe(fred_mod.fetch_many, cfg["risk_curve"]["fred_series"]) or pd.DataFrame()
    rc_yh = _safe(yh_mod.fetch_close, cfg["risk_curve"]["yahoo"]) or pd.DataFrame()
    risk_df = pd.concat([rc_fred, rc_yh], axis=1).sort_index().ffill()
    save_parquet(risk_df, "risk_curve_raw")
    rc_s = risk_curve_score(risk_df)
    save_parquet(rc_s.to_frame(), "risk_curve_score")

    # ---------- LAYER 3 : BTC MICROSTRUCTURE ----------
    btc_data = _safe(cg_mod.fetch_market_chart, cfg["micro"]["coingecko"]["btc_id"], "max")
    btc_price = btc_data["price"] if btc_data is not None and not btc_data.empty else pd.Series(dtype=float)
    if not btc_price.empty:
        save_parquet(btc_price.to_frame("btc_price"), "btc_price")

    funding = _safe(dx_mod.fetch_funding_blend)
    if funding is not None and not funding.empty:
        save_parquet(funding, "funding")
    funding_blend = funding["funding_blend"] if funding is not None and not funding.empty else None

    oi = _safe(dx_mod.oi_binance)
    if oi is not None and not oi.empty:
        save_parquet(oi, "open_interest")
    oi_series = oi["oi_binance_usd"] if oi is not None and not oi.empty else None

    dvol = _safe(dx_mod.deribit_dvol)
    if dvol is not None and not dvol.empty:
        save_parquet(dvol, "dvol")

    etf = _safe(etf_mod.fetch_etf_flows)
    if etf is not None and not etf.empty:
        save_parquet(etf, "etf_flows")
    etf_total = etf["Total"] if etf is not None and "Total" in (etf.columns if etf is not None else []) else None

    micro_s = micro_score(
        etf_total=etf_total,
        funding_blend=funding_blend,
        oi_usd=oi_series,
        dvol=dvol["dvol"] if dvol is not None and not dvol.empty else None,
        btc_price=btc_price,
    )
    save_parquet(micro_s.to_frame(), "micro_score")

    # ---------- LAYER 4 : LEAD/LAG ----------
    ll_yh = _safe(yh_mod.fetch_close, cfg["leadlag"]["yahoo"]) or pd.DataFrame()
    if not ll_yh.empty:
        save_parquet(ll_yh, "leadlag_raw")
    miners_basket = None
    if not ll_yh.empty:
        miner_cols = [c for c in ("mara", "riot", "clsk") if c in ll_yh.columns]
        if miner_cols:
            miners_basket = ll_yh[miner_cols].pct_change().mean(axis=1).add(1).cumprod()

    eth_data = _safe(cg_mod.fetch_market_chart, cfg["leadlag"]["coingecko_pairs"]["eth_btc"][0], "max")
    eth_btc_ratio = None
    if eth_data is not None and not eth_data.empty and not btc_price.empty:
        eth_btc_ratio = (eth_data["price"] / btc_price).rename("eth_btc")

    stable_supply = None
    stables = []
    for sid in cfg["leadlag"]["stables"].values():
        d = _safe(cg_mod.fetch_market_chart, sid, "max")
        if d is not None and not d.empty:
            stables.append(d["mcap"].rename(sid))
    if stables:
        stable_supply = pd.concat(stables, axis=1).sum(axis=1)

    ll_s = leadlag_score(
        btc_price=btc_price,
        mstr=ll_yh["mstr"] if "mstr" in ll_yh else None,
        coin=ll_yh["coin"] if "coin" in ll_yh else None,
        miners=miners_basket,
        eth_btc=eth_btc_ratio,
        stable_supply=stable_supply,
    )
    save_parquet(ll_s.to_frame(), "leadlag_score")

    # ---------- LAYER 5 : EXTREMES ----------
    skew_proxy = _safe(dx_mod.deribit_skew_proxy)
    skew_series = None
    if skew_proxy is not None and not skew_proxy.empty and "skew_25d_proxy" in skew_proxy.columns:
        skew_series = skew_proxy["skew_25d_proxy"]
    alerts = extreme_triggers(
        funding_blend=funding_blend,
        skew_25d=skew_series,
        oi_usd=oi_series,
        mvrv_z=None,  # plug in MVRV-Z source later
        cfg=cfg["extremes"],
    )
    save_parquet(alerts.assign(asof=pd.Timestamp.utcnow()).set_index("asof"), "alerts")
    ex_val = extremes_score(alerts)

    # ---------- COMPOSITE ----------
    regime = composite_score(
        macro=macro_s,
        risk_curve=rc_s,
        micro=micro_s,
        leadlag=ll_s,
        extremes_value=ex_val,
        weights=cfg["weights"],
    )
    save_parquet(regime.to_frame(), "regime_score")

    last_score = float(regime.dropna().iloc[-1]) if not regime.dropna().empty else 0.0
    summary = {
        "asof": datetime.now(timezone.utc).isoformat(),
        "regime_score": last_score,
        "bias": label_bias(last_score),
        "position_weight": position_sizing(last_score),
        "components": {
            "macro": float(macro_s.dropna().iloc[-1]) if not macro_s.dropna().empty else None,
            "risk_curve": float(rc_s.dropna().iloc[-1]) if not rc_s.dropna().empty else None,
            "micro": float(micro_s.dropna().iloc[-1]) if not micro_s.dropna().empty else None,
            "leadlag": float(ll_s.dropna().iloc[-1]) if not ll_s.dropna().empty else None,
            "extremes": ex_val,
        },
    }

    # ---------- BACKTEST ----------
    if not btc_price.empty:
        bt = run_backtest(btc_price, regime)
        if bt:
            save_parquet(bt["df"], "backtest")
            summary["backtest_stats"] = bt["stats"]

    with open("data/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print("[pipeline] done. summary:", json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
