"""Global Central Bank balance sheets — direct fetchers for sources not on FRED.

Free public APIs:
- Bank of Canada (BoC) : Valet API — JSON, no key
- Bank of Japan (BOJ)  : statistics CSVs, scraped
- RBA (Australia)      : statistics CSVs
- RBNZ (NZ)            : statistics CSVs (quarterly)

For ECB, BOE — primary source is FRED; this module is the back-up/extension
when the FRED proxies are stale or missing.

The aggregator `compute_global_net_liquidity()` produces a single USD-equivalent
series from any subset of the above + the Fed (passed in by the caller).
"""
from __future__ import annotations

import io
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


# =============================================================================
# Bank of Canada — Valet JSON API (most reliable foreign CB source we have)
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_boc_assets(years: int = 10) -> pd.Series:
    """BoC total assets from the Valet API. Series V36636 = total assets ($CAD m).

    Returns a daily-aligned (forward-filled) Series in CAD millions.
    """
    url = (
        "https://www.bankofcanada.ca/valet/observations/V36636/json"
        f"?recent_years={years}"
    )
    r = requests.get(url, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"})
    r.raise_for_status()
    obs = r.json().get("observations", [])
    if not obs:
        return pd.Series(dtype=float)
    rows = []
    for o in obs:
        date = pd.to_datetime(o.get("d"))
        val = o.get("V36636", {})
        if isinstance(val, dict) and "v" in val:
            try:
                rows.append((date, float(val["v"])))
            except (TypeError, ValueError):
                pass
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series(dict(rows)).sort_index()
    return s.resample("D").last().ffill().rename("boc_assets_cad_m")


# =============================================================================
# Reserve Bank of Australia — statistics CSV (table A1 = liabilities & assets)
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_rba_assets() -> pd.Series:
    """RBA total assets from the published A1 CSV.

    Returns weekly Series in AUD millions, daily-resampled & forward-filled.
    """
    url = "https://www.rba.gov.au/statistics/tables/csv/a01-hist.csv"
    r = requests.get(url, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"})
    r.raise_for_status()
    # RBA CSVs have ~10 header rows; the data starts where col 0 is a date.
    raw = pd.read_csv(io.StringIO(r.text), header=None, dtype=str,
                      skip_blank_lines=False)
    # Find the row where col 0 looks like a date
    date_col = raw[0].astype(str)
    # Match yyyy or dd-Mon-yyyy etc; simplest: try to_datetime row by row
    parsed = pd.to_datetime(date_col, errors="coerce")
    data_rows = raw[parsed.notna()].copy()
    if data_rows.empty:
        return pd.Series(dtype=float)
    data_rows.index = pd.to_datetime(data_rows[0])
    # The "Total assets" column varies but is usually the last numeric column.
    # Take the right-most column with any numeric values.
    for c in reversed(range(1, raw.shape[1])):
        candidate = pd.to_numeric(data_rows[c], errors="coerce")
        if candidate.notna().sum() > 50:
            return candidate.dropna().resample("D").last().ffill().rename("rba_assets_aud_m")
    return pd.Series(dtype=float)


# =============================================================================
# Aggregate: Global Net Liquidity in USD
# =============================================================================
def compute_global_net_liquidity(
    fed_walcl: pd.Series | None,            # USD millions
    fed_rrp:   pd.Series | None = None,     # USD billions
    fed_tga:   pd.Series | None = None,     # USD billions
    ecb_assets: pd.Series | None = None,    # EUR millions
    boj_assets: pd.Series | None = None,    # JPY 100m or similar
    boe_assets: pd.Series | None = None,    # GBP millions
    boc_assets: pd.Series | None = None,    # CAD millions
    rba_assets: pd.Series | None = None,    # AUD millions
    eurusd: pd.Series | None = None,
    usdjpy: pd.Series | None = None,
    gbpusd: pd.Series | None = None,
    usdcad: pd.Series | None = None,
    audusd: pd.Series | None = None,
) -> pd.DataFrame:
    """Returns DataFrame with per-CB USD contribution and the aggregate sum.

    Each CB asset series is converted to USD using its native FX rate.
    Note: Fed series are already in USD (millions).
    Output unit: USD billions.
    """
    out = pd.DataFrame()

    def _daily(s):
        if s is None or s.empty:
            return None
        s = s.copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index)
        if s.index.tz is not None:
            s.index = s.index.tz_convert(None)
        return s.resample("D").last().ffill()

    fed_walcl = _daily(fed_walcl)
    fed_rrp   = _daily(fed_rrp)
    fed_tga   = _daily(fed_tga)
    ecb_assets = _daily(ecb_assets)
    boj_assets = _daily(boj_assets)
    boe_assets = _daily(boe_assets)
    boc_assets = _daily(boc_assets)
    rba_assets = _daily(rba_assets)
    eurusd = _daily(eurusd); usdjpy = _daily(usdjpy)
    gbpusd = _daily(gbpusd); usdcad = _daily(usdcad)
    audusd = _daily(audusd)

    # FED net liquidity (USD billions): WALCL/1000 - RRP - TGA
    # WALCL is in millions of USD; RRP and TGA are in billions of USD per FRED.
    if fed_walcl is not None:
        # diagnostics
        try:
            print(f"[gcb-debug] WALCL last : {fed_walcl.dropna().iloc[-1]:>15,.2f}  (expect ~6,700,000 = millions of $)")
            if fed_rrp is not None:
                print(f"[gcb-debug] RRP   last : {fed_rrp.dropna().iloc[-1]:>15,.2f}  (expect ~100-2,500 = billions of $)")
            if fed_tga is not None:
                print(f"[gcb-debug] TGA   last : {fed_tga.dropna().iloc[-1]:>15,.2f}  (expect ~200-1,200 = billions of $)")
        except Exception:
            pass

        # WALCL is in MILLIONS of USD per FRED
        s = fed_walcl / 1000.0
        # RRPONTSYD is in BILLIONS of USD (already correct unit, just subtract)
        if fed_rrp is not None:
            s = s.subtract(fed_rrp, fill_value=0)
        # WTREGEN (TGA) is in MILLIONS of USD per FRED — convert to billions
        if fed_tga is not None:
            s = s.subtract(fed_tga / 1000.0, fill_value=0)
        out["fed_usd_bn"] = s

    # ECB EUR millions × EURUSD = USD millions → / 1000 → USD bn
    if ecb_assets is not None and eurusd is not None:
        out["ecb_usd_bn"] = (ecb_assets * eurusd / 1000.0)

    # BOJ — depends on FRED unit; assume JPY 100m (oku-yen) per FRED's JPNASSETS.
    # 100 million JPY × USD/JPY (1/USDJPY) → USD;  /10 → USD billions
    if boj_assets is not None and usdjpy is not None:
        # 1 oku JPY = 100m JPY = 1e8 JPY; in USD = 1e8/usdjpy = ~$650k for usdjpy=153
        # so 1 oku JPY ≈ 0.65e6 USD = 0.00065 USD bn
        out["boj_usd_bn"] = (boj_assets * (1.0 / usdjpy)) * 1e8 / 1e9

    # BOE (GBP millions)
    if boe_assets is not None and gbpusd is not None:
        out["boe_usd_bn"] = (boe_assets * gbpusd / 1000.0)

    # BoC (CAD millions) — usdcad is CAD-per-USD
    if boc_assets is not None and usdcad is not None:
        out["boc_usd_bn"] = (boc_assets / usdcad / 1000.0)

    # RBA (AUD millions)
    if rba_assets is not None and audusd is not None:
        out["rba_usd_bn"] = (rba_assets * audusd / 1000.0)

    if not out.empty:
        out["global_net_liquidity_usd_bn"] = out.sum(axis=1)
        # Diagnostics: print per-CB last values so unit issues are caught early
        last_row = out.dropna(how="all").iloc[-1] if not out.dropna(how="all").empty else None
        if last_row is not None:
            print("[global_cb] per-CB latest USD bn:")
            for col, val in last_row.items():
                if col == "global_net_liquidity_usd_bn":
                    continue
                if val == val:  # not NaN
                    print(f"   {col:<20s} {val:>+12,.0f}")
    return out
