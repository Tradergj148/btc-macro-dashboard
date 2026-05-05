"""Global Central Bank balance sheets — Phase B: full G7 coverage.

Sources (all free, no auth):
- Fed   : FRED WALCL (already in macro module)
- ECB   : FRED ECBASSETSW (already in macro module)
- BoC   : Bank of Canada Valet API (JSON)
- BOJ   : FRED 'JPNASSETS' best-effort + Japan monetary base fallback
- BOE   : FRED via 'BOGMBASEW'-style series, fallback to BoE iadb
- RBA   : rba.gov.au A1 historical CSV  (parser hardened)
- RBNZ  : rbnz.govt.nz statistical Excel (quarterly)
- PBOC  : best-effort via FRED 'CHNMABMM01CXMSAM' (M3 proxy, monthly)

The aggregator `compute_global_net_liquidity()` produces a single
USD-equivalent series from any subset of the above (caller passes Fed series).
"""
from __future__ import annotations

import io
import re
import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

UA = {"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"}


# =============================================================================
# Bank of Canada — Valet JSON API  (Phase A, already working)
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_boc_assets(years: int = 10) -> pd.Series:
    url = (
        "https://www.bankofcanada.ca/valet/observations/V36636/json"
        f"?recent_years={years}"
    )
    r = requests.get(url, timeout=20, headers=UA)
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
# Bank of Japan — direct CSV scrape (English statistics page)
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_boj_assets() -> pd.Series:
    """BOJ total assets from BOJ time-series search.

    Series MD01'MABS1AB12_NJPY = "Bank of Japan accounts: Assets, Total"
    Units: 100 million JPY (oku).  We return Series in oku JPY.
    """
    # BOJ's time-series CSV download endpoint
    url = (
        "https://www.stat-search.boj.or.jp/ssi/cgi-bin/famecgi2"
        "?cgi=$nme_a000_en&lstSelection=MD01"
    )
    try:
        r = requests.get(url, timeout=20, headers=UA)
        r.raise_for_status()
        # The actual download is multi-step; this often returns HTML, not CSV.
        # If we get HTML rather than CSV, return empty.
        if "<html" in r.text.lower():
            return pd.Series(dtype=float)
        df = pd.read_csv(io.StringIO(r.text))
        # very fragile — needs spec verification; on failure caller falls back
        if df.empty or len(df.columns) < 2:
            return pd.Series(dtype=float)
        df.columns = ["date", "value"] + list(df.columns[2:])
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.dropna().set_index("date")["value"]
        return s.resample("D").last().ffill().rename("boj_assets_oku_jpy")
    except Exception:
        return pd.Series(dtype=float)


# =============================================================================
# Bank of England — direct from iadb (interactive database)
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_boe_assets() -> pd.Series:
    """BOE balance sheet via the iadb CSV download.

    Series LPMVTUE = "Bank of England Asset Purchase Facility, holdings"
    in GBP millions.  This is the QE portfolio not the full BS, but it's
    the closest free proxy and is what most analysts use.
    """
    url = (
        "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
        "?Travel=NIxAZxSUx"
        "&FromSeries=1&ToSeries=50"
        "&DAT=RNG&FD=1&FM=Jan&FY=2010"
        "&TD=31&TM=Dec&TY=2030"
        "&FNY=Y&CSVF=TT"
        "&html.x=66&html.y=26"
        "&SeriesCodes=LPMVTUE&UsingCodes=Y&Filter=N&title=LPMVTUE&VPD=Y"
    )
    try:
        r = requests.get(url, timeout=20, headers=UA)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        # First column is date, second is series value
        if df.shape[1] < 2:
            return pd.Series(dtype=float)
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.dropna().set_index("date")["value"]
        return s.resample("D").last().ffill().rename("boe_assets_gbp_m")
    except Exception:
        return pd.Series(dtype=float)


# =============================================================================
# RBA — hardened CSV parser
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_rba_assets() -> pd.Series:
    """RBA total assets from the published A1 CSV.  Returns AUD millions."""
    url = "https://www.rba.gov.au/statistics/tables/csv/a01-hist.csv"
    r = requests.get(url, timeout=20, headers=UA)
    r.raise_for_status()
    text = r.text

    # RBA CSVs have ~10 metadata lines before tabular data.
    # Find the first row whose first column parses as a date.
    lines = text.splitlines()
    data_start = None
    for i, ln in enumerate(lines):
        first = ln.split(",")[0].strip().strip('"')
        if re.match(r"\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}", first) or \
           re.match(r"\d{4}-\d{2}-\d{2}", first):
            data_start = i
            break
    if data_start is None:
        return pd.Series(dtype=float)

    # Re-read CSV from the data row
    csv_data = "\n".join(lines[data_start:])
    df = pd.read_csv(io.StringIO(csv_data), header=None, dtype=str,
                     skip_blank_lines=False)
    df[0] = pd.to_datetime(df[0], errors="coerce", dayfirst=True)
    df = df.dropna(subset=[0]).set_index(0)

    # Take the rightmost numeric column with enough non-NaN values (Total Assets)
    for c in reversed(range(1, df.shape[1])):
        col = pd.to_numeric(df[c].astype(str).str.replace(",", ""),
                            errors="coerce")
        if col.notna().sum() > 100:
            return col.dropna().resample("D").last().ffill().rename("rba_assets_aud_m")
    return pd.Series(dtype=float)


# =============================================================================
# RBNZ — quarterly only, from RBNZ statistics page
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_rbnz_assets() -> pd.Series:
    """RBNZ total assets — best effort from R3 (Reserve Bank balance sheet).

    Quarterly data, NZD millions.  Returns a forward-filled daily Series.
    """
    # RBNZ publishes statistical tables as Excel; many endpoints exist.
    # The primary URL changes — we try the most stable one and fall back to empty.
    candidates = [
        "https://www.rbnz.govt.nz/-/media/ReserveBank/Files/Statistics/tables/r3/hr3.xlsx",
        "https://www.rbnz.govt.nz/-/media/project/sites/rbnz/files/statistics/tables/r3/hr3.xlsx",
    ]
    for url in candidates:
        try:
            r = requests.get(url, timeout=30, headers=UA)
            if r.status_code != 200:
                continue
            df = pd.read_excel(io.BytesIO(r.content), sheet_name=0,
                                header=None, engine="openpyxl")
            # find first row with parseable date
            date_col = pd.to_datetime(df[0], errors="coerce")
            mask = date_col.notna()
            if mask.sum() < 8:
                continue
            data = df[mask].copy()
            data.index = pd.to_datetime(data[0])
            for c in reversed(range(1, data.shape[1])):
                col = pd.to_numeric(data[c], errors="coerce")
                if col.notna().sum() > 12:
                    return col.dropna().resample("D").last().ffill().rename(
                        "rbnz_assets_nzd_m")
        except Exception:
            continue
    return pd.Series(dtype=float)


# =============================================================================
# PBOC — best-effort via FRED's monthly Chinese monetary aggregate
# =============================================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_pboc_assets() -> pd.Series:
    """PBOC total assets — best-effort.

    Real PBOC BS data is monthly, in CNY 100m, only on the Chinese-language
    PBOC site. As a free proxy we use FRED's M3 monetary aggregate for China
    which tracks PBOC liquidity provision reasonably well.

    NOTE: This is a *proxy* not the actual balance sheet. Documented in dashboard.
    """
    # FRED CSV fallback path
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MABMM301CNM189N"
    try:
        r = requests.get(url, timeout=20, headers=UA)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.dropna().set_index("date")["value"]
        # CNY billions per FRED
        return s.resample("D").last().ffill().rename("pboc_m3_cny_bn")
    except Exception:
        return pd.Series(dtype=float)


# =============================================================================
# Aggregator: Global Net Liquidity in USD billions
# =============================================================================
def compute_global_net_liquidity(
    fed_walcl: pd.Series | None,
    fed_rrp:   pd.Series | None = None,
    fed_tga:   pd.Series | None = None,
    ecb_assets: pd.Series | None = None,
    boj_m3:    pd.Series | None = None,    # Japan M3 (JPY millions, monthly)
    boe_m3:    pd.Series | None = None,    # UK M3 (GBP millions, monthly)
    rba_m3:    pd.Series | None = None,    # Australia M3 (AUD millions, monthly)
    rbnz_m3:   pd.Series | None = None,    # NZ M3 (NZD millions, monthly)
    pboc_m3:   pd.Series | None = None,    # China M3 (CNY millions, monthly)
    boc_assets: pd.Series | None = None,   # CAD millions (Valet)
    eurusd: pd.Series | None = None,
    usdjpy: pd.Series | None = None,
    gbpusd: pd.Series | None = None,
    usdcad: pd.Series | None = None,
    audusd: pd.Series | None = None,
    nzdusd: pd.Series | None = None,
    usdcnh: pd.Series | None = None,
) -> pd.DataFrame:
    """Sum of central bank liquidity proxies in USD billions.

    Mix of approaches:
      Fed   = WALCL - RRP - TGA       (true Net Liquidity)
      ECB   = ECBASSETSW              (true balance sheet)
      BoC   = Valet V36636            (true balance sheet)
      BOJ   = M3 monetary aggregate   (proxy)
      BOE   = M3 monetary aggregate   (proxy)
      RBA   = M3 monetary aggregate   (proxy)
      RBNZ  = M3 monetary aggregate   (proxy)
      PBOC  = M3 monetary aggregate   (proxy)

    M3 is what macro analysts (Howell, Capital Wars, BIS) use for
    "Global Money Supply" — closely tracks CB liquidity provision.
    """
    out = pd.DataFrame()

    def _daily(s):
        if s is None or (isinstance(s, pd.Series) and s.empty):
            return None
        s = s.copy() if isinstance(s, pd.Series) else None
        if s is None:
            return None
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index)
        if s.index.tz is not None:
            s.index = s.index.tz_convert(None)
        return s.resample("D").last().ffill()

    fed_walcl   = _daily(fed_walcl);  fed_rrp = _daily(fed_rrp);  fed_tga = _daily(fed_tga)
    ecb_assets  = _daily(ecb_assets); boc_assets = _daily(boc_assets)
    boj_m3      = _daily(boj_m3);     boe_m3 = _daily(boe_m3)
    rba_m3      = _daily(rba_m3);     rbnz_m3 = _daily(rbnz_m3)
    pboc_m3     = _daily(pboc_m3)
    eurusd = _daily(eurusd); usdjpy = _daily(usdjpy); gbpusd = _daily(gbpusd)
    usdcad = _daily(usdcad); audusd = _daily(audusd); nzdusd = _daily(nzdusd)
    usdcnh = _daily(usdcnh)

    # FED (USD billions)
    if fed_walcl is not None:
        s = fed_walcl / 1000.0
        if fed_rrp is not None:
            s = s.subtract(fed_rrp, fill_value=0)
        if fed_tga is not None:
            s = s.subtract(fed_tga / 1000.0, fill_value=0)
        out["fed_usd_bn"] = s

    # ECB (EUR millions × EURUSD / 1000 = USD bn)
    if ecb_assets is not None and eurusd is not None:
        out["ecb_usd_bn"] = ecb_assets * eurusd / 1000.0

    # BoC (CAD millions / usdcad / 1000 = USD bn)
    if boc_assets is not None and usdcad is not None:
        out["boc_usd_bn"] = boc_assets / usdcad / 1000.0

    # BOJ via M3.  FRED OECD series in JPY millions (monthly, ffilled to daily)
    if boj_m3 is not None and usdjpy is not None:
        out["boj_usd_bn"] = boj_m3 / usdjpy / 1e9

    # BOE via M3 (GBP millions × GBPUSD / 1000 = USD bn)
    if boe_m3 is not None and gbpusd is not None:
        out["boe_usd_bn"] = boe_m3 * gbpusd / 1e9

    # RBA via M3 (AUD millions × audusd / 1000 = USD bn)
    if rba_m3 is not None and audusd is not None:
        out["rba_usd_bn"] = rba_m3 * audusd / 1e9

    # RBNZ via M3 (NZD millions × nzdusd / 1000 = USD bn)
    if rbnz_m3 is not None and nzdusd is not None:
        out["rbnz_usd_bn"] = rbnz_m3 * nzdusd / 1e9

    # PBOC via M3 (CNY millions / usdcnh / 1000 = USD bn)
    if pboc_m3 is not None and usdcnh is not None:
        out["pboc_usd_bn"] = pboc_m3 / usdcnh / 1e9

    if not out.empty:
        out["global_net_liquidity_usd_bn"] = out.sum(axis=1)
        last_row = out.dropna(how="all").iloc[-1] if not out.dropna(how="all").empty else None
        if last_row is not None:
            print("[global_cb] per-CB latest USD bn:")
            for col, val in last_row.items():
                if col == "global_net_liquidity_usd_bn":
                    continue
                if val == val:
                    print(f"   {col:<22s} {val:>+12,.0f}")
    return out
