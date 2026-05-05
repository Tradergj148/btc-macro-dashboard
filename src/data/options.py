"""Deribit options chain fetcher + Greeks + GEX computation.

All Deribit endpoints used here are public / free.

Pipeline:
    chain = fetch_options_chain('BTC')
    spot  = fetch_spot('BTC')
    enrich_chain(chain, spot, risk_free=0.05)        # adds gamma, delta, dte
    term  = compute_term_structure(chain)            # ATM IV per expiry
    skew  = compute_skew_curve(chain)                # 25d skew per expiry
    oi    = compute_oi_profile(chain)                # strike x expiry x type
    gex   = compute_gex(chain, spot, method='B')     # aggregate + per-strike
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from scipy.stats import norm
from tenacity import retry, stop_after_attempt, wait_exponential


DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
INDEX_TICKERS = {"BTC": "btc_usd", "ETH": "eth_usd"}


# ------------------------------------------------------------------
#  RAW FETCH
# ------------------------------------------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_spot(currency: str = "BTC") -> float:
    """Current spot index from Deribit (good for GEX calc; ~ matches USD)."""
    r = requests.get(
        f"{DERIBIT_BASE}/get_index_price",
        params={"index_name": INDEX_TICKERS[currency]},
        timeout=10,
    )
    r.raise_for_status()
    return float(r.json()["result"]["index_price"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_options_chain(currency: str = "BTC") -> pd.DataFrame:
    """Pull full options book summary in one call. Returns one row per instrument."""
    r = requests.get(
        f"{DERIBIT_BASE}/get_book_summary_by_currency",
        params={"currency": currency, "kind": "option"},
        timeout=30,
    )
    r.raise_for_status()
    rows = r.json().get("result", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    parts = df["instrument_name"].str.split("-", expand=True)
    df["currency"] = parts[0]
    df["expiry_str"] = parts[1]
    df["strike"] = pd.to_numeric(parts[2], errors="coerce")
    df["type"] = parts[3]   # "C" or "P"

    df["expiry"] = pd.to_datetime(df["expiry_str"], format="%d%b%y", errors="coerce", utc=True)

    keep = ["instrument_name", "currency", "expiry", "expiry_str", "strike", "type",
            "mark_iv", "mark_price", "underlying_price", "open_interest",
            "bid_iv", "ask_iv", "delta", "gamma", "vega", "theta",
            "interest_rate", "volume", "estimated_delivery_price"]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].copy()
    for c in ("mark_iv", "mark_price", "open_interest", "bid_iv", "ask_iv",
              "delta", "gamma", "vega", "theta", "interest_rate", "volume",
              "underlying_price", "estimated_delivery_price"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "mark_iv" in df.columns:
        df["mark_iv"] = df["mark_iv"] / 100.0    # Deribit returns vol in % points
    df = df.dropna(subset=["expiry", "strike", "type"])
    df["asof"] = pd.Timestamp.now(tz="UTC")
    return df.sort_values(["expiry", "strike", "type"]).reset_index(drop=True)


# ------------------------------------------------------------------
#  BLACK-SCHOLES
# ------------------------------------------------------------------
def _d1(spot, strike, t, iv, r=0.0):
    if t <= 0 or iv <= 0 or strike <= 0 or spot <= 0:
        return np.nan
    return (math.log(spot / strike) + (r + 0.5 * iv * iv) * t) / (iv * math.sqrt(t))


def bs_delta(spot, strike, t, iv, r=0.0, opt_type="C"):
    d1 = _d1(spot, strike, t, iv, r)
    if np.isnan(d1):
        return np.nan
    return float(norm.cdf(d1)) if opt_type == "C" else float(norm.cdf(d1) - 1)


def bs_gamma(spot, strike, t, iv, r=0.0):
    """Gamma is the same for calls and puts."""
    d1 = _d1(spot, strike, t, iv, r)
    if np.isnan(d1):
        return np.nan
    return float(norm.pdf(d1) / (spot * iv * math.sqrt(t)))


def enrich_chain(chain: pd.DataFrame, spot: float, risk_free: float = 0.05) -> pd.DataFrame:
    """Adds days-to-expiry, recomputed delta/gamma so we don't trust Deribit's snapshot."""
    if chain.empty:
        return chain
    now = pd.Timestamp.now(tz="UTC")
    chain = chain.copy()
    chain["dte_days"] = (chain["expiry"] - now).dt.total_seconds() / 86400.0
    chain["t_years"] = chain["dte_days"].clip(lower=0) / 365.25

    iv = chain["mark_iv"].fillna(0).clip(lower=1e-4)
    chain["bs_delta"] = [
        bs_delta(spot, k, t, v, risk_free, ot)
        for k, t, v, ot in zip(chain["strike"], chain["t_years"], iv, chain["type"])
    ]
    chain["bs_gamma"] = [
        bs_gamma(spot, k, t, v, risk_free)
        for k, t, v in zip(chain["strike"], chain["t_years"], iv)
    ]
    return chain


# ------------------------------------------------------------------
#  TERM STRUCTURE  (ATM IV per expiry)
# ------------------------------------------------------------------
def compute_term_structure(chain: pd.DataFrame, spot: float) -> pd.DataFrame:
    if chain.empty or "mark_iv" not in chain.columns:
        return pd.DataFrame()
    out = []
    for exp, g in chain.groupby("expiry"):
        g = g.dropna(subset=["mark_iv"])
        if g.empty:
            continue
        # nearest strike to spot
        idx = (g["strike"] - spot).abs().idxmin()
        atm = g.loc[idx]
        out.append({
            "expiry":   exp,
            "dte_days": atm.get("dte_days", np.nan),
            "atm_strike": atm["strike"],
            "atm_iv":   atm["mark_iv"],
        })
    df = pd.DataFrame(out).sort_values("dte_days").reset_index(drop=True)
    return df


# ------------------------------------------------------------------
#  SKEW CURVE  (25-delta skew per expiry)
# ------------------------------------------------------------------
def compute_skew_curve(chain: pd.DataFrame) -> pd.DataFrame:
    if chain.empty or "bs_delta" not in chain.columns:
        return pd.DataFrame()

    out = []
    for exp, g in chain.groupby("expiry"):
        calls = g[g["type"] == "C"].dropna(subset=["bs_delta", "mark_iv"])
        puts  = g[g["type"] == "P"].dropna(subset=["bs_delta", "mark_iv"])
        if calls.empty or puts.empty:
            continue

        # 25-delta call: nearest to delta = 0.25
        c25 = calls.iloc[(calls["bs_delta"] - 0.25).abs().argsort()[:1]]
        # 25-delta put: nearest to delta = -0.25
        p25 = puts.iloc[(puts["bs_delta"] + 0.25).abs().argsort()[:1]]
        # ATM (50-delta call)
        c50 = calls.iloc[(calls["bs_delta"] - 0.50).abs().argsort()[:1]]

        rec = {
            "expiry":    exp,
            "dte_days":  g["dte_days"].iloc[0] if "dte_days" in g.columns else np.nan,
            "iv_call25": float(c25["mark_iv"].iloc[0]) if not c25.empty else np.nan,
            "iv_put25":  float(p25["mark_iv"].iloc[0]) if not p25.empty else np.nan,
            "iv_atm":    float(c50["mark_iv"].iloc[0]) if not c50.empty else np.nan,
        }
        rec["skew_25d"] = rec["iv_call25"] - rec["iv_put25"]   # positive=call-heavy
        rec["risk_reversal_25d"] = rec["skew_25d"]              # alias
        out.append(rec)

    return pd.DataFrame(out).sort_values("dte_days").reset_index(drop=True)


# ------------------------------------------------------------------
#  OI PROFILE  (strike x expiry x type)
# ------------------------------------------------------------------
def compute_oi_profile(chain: pd.DataFrame) -> pd.DataFrame:
    if chain.empty:
        return pd.DataFrame()
    keep = ["expiry", "strike", "type", "open_interest", "mark_iv", "bs_delta", "bs_gamma"]
    keep = [c for c in keep if c in chain.columns]
    return chain[keep].copy()


# ------------------------------------------------------------------
#  GEX  (delta-bucketed dealer model = Option B)
# ------------------------------------------------------------------
def _dealer_position_factor(delta: float, opt_type: str) -> float:
    """Empirical dealer positioning sign × strength.

    Delta-bucketed model:
        Calls : dealers tend to be net SHORT (retail buys upside lottos)
                stronger short on far OTM, lighter on ITM
        Puts  : dealers tend to be net LONG (provide hedging)
                stronger long on far OTM, lighter on ITM

    Returns a factor in [-1, +1]:
        positive = dealer net long that contract  → adds positive gamma
        negative = dealer net short that contract → adds negative gamma
    """
    if not np.isfinite(delta):
        return 0.0
    abs_d = abs(delta)
    if opt_type == "C":
        # short more strongly when delta is small (far OTM)
        return -(0.4 + 0.5 * (1 - abs_d))   # -0.4 (deep ITM) ... -0.9 (deep OTM)
    elif opt_type == "P":
        return +(0.4 + 0.5 * (1 - abs_d))   # +0.4 (deep ITM) ... +0.9 (deep OTM)
    return 0.0


def compute_gex(chain: pd.DataFrame, spot: float,
                contract_size: float = 1.0, method: str = "B") -> dict:
    """Returns {'total': float, 'by_strike': DataFrame, 'method': str}.

    GEX(strike) = γ × OI × contract_size × spot² × 0.01 × dealer_factor
    Units: USD change in dealer hedge per 1% spot move.
    """
    if chain.empty or "bs_gamma" not in chain.columns:
        return {"total": 0.0, "by_strike": pd.DataFrame(), "method": method}

    df = chain.dropna(subset=["bs_gamma", "open_interest", "bs_delta"]).copy()
    if df.empty:
        return {"total": 0.0, "by_strike": pd.DataFrame(), "method": method}

    if method == "A":
        # naive: short all calls, long all puts
        df["dealer_factor"] = np.where(df["type"] == "C", -1.0, 1.0)
    else:
        # Option B (delta-bucketed) — recommended
        df["dealer_factor"] = [
            _dealer_position_factor(d, t) for d, t in zip(df["bs_delta"], df["type"])
        ]

    df["gex_contract"] = (
        df["bs_gamma"] * df["open_interest"] * contract_size *
        spot * spot * 0.01 * df["dealer_factor"]
    )

    by_strike = (
        df.groupby("strike", as_index=False)["gex_contract"]
          .sum()
          .rename(columns={"gex_contract": "gex_usd_per_pct"})
          .sort_values("strike")
          .reset_index(drop=True)
    )

    by_strike_expiry = (
        df.groupby(["expiry", "strike"], as_index=False)["gex_contract"]
          .sum()
          .rename(columns={"gex_contract": "gex_usd_per_pct"})
    )

    return {
        "total": float(df["gex_contract"].sum()),
        "by_strike": by_strike,
        "by_strike_expiry": by_strike_expiry,
        "method": method,
        "spot": float(spot),
        "asof": pd.Timestamp.now(tz="UTC"),
    }


# ------------------------------------------------------------------
#  Convenience: full snapshot pipeline
# ------------------------------------------------------------------
def snapshot(currency: str = "BTC", risk_free: float = 0.05) -> dict:
    """One-call pipeline: returns dict of {chain, spot, term, skew, oi, gex}."""
    spot = fetch_spot(currency)
    chain = fetch_options_chain(currency)
    chain = enrich_chain(chain, spot, risk_free)
    return {
        "asof":  pd.Timestamp.now(tz="UTC"),
        "spot":  spot,
        "chain": chain,
        "term":  compute_term_structure(chain, spot),
        "skew":  compute_skew_curve(chain),
        "oi":    compute_oi_profile(chain),
        "gex":   compute_gex(chain, spot, method="B"),
    }
