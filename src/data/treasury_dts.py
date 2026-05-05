"""Daily Treasury Statement (DTS) -- fiscal plumbing data.

Source: Treasury FiscalData API  (free, no auth, daily, deep history)
Docs:   https://fiscaldata.treasury.gov/api-documentation/
"""
from __future__ import annotations

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

API_ROOT = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
UA       = {"User-Agent": "Mozilla/5.0 (BTC-Macro-Dashboard)"}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
def _fetch_paginated(endpoint: str,
                     filter_expr: str,
                     fields: str | None = None,
                     page_size: int = 10000) -> pd.DataFrame:
    """Walk the cursor-paginated FiscalData endpoint and return a DataFrame.

    On HTTP failure, prints status code + response body snippet *before*
    re-raising, so the underlying tenacity RetryError isn't opaque.
    """
    base = f"{API_ROOT}{endpoint}"
    qs = [f"filter={filter_expr}",
          f"format=json",
          f"page[size]={page_size}",
          f"sort=record_date"]
    if fields:
        qs.insert(0, f"fields={fields}")
    url = base + "?" + "&".join(qs)

    rows = []
    while url:
        r = requests.get(url, timeout=12, headers=UA)
        if r.status_code >= 400:
            snippet = (r.text or "")[:300].replace("\n", " ")
            print(f"[dts] {endpoint}  HTTP {r.status_code}: {snippet}")
            r.raise_for_status()
        body = r.json()
        rows.extend(body.get("data", []))
        links = body.get("links", {}) or {}
        nxt = links.get("next")
        url = (API_ROOT + nxt) if nxt else None
    return pd.DataFrame(rows)


# ============================================================
#  1) TGA daily balance
# ============================================================
def fetch_tga_balance(start: str = "2018-01-01") -> pd.Series:
    """Daily Treasury General Account balance, in USD millions.

    Treasury restructured the DTS in April 2022.  Both the account_type
    label AND the balance field can change across schema versions, so
    we probe defensively:

      - account_type matches either legacy "Federal Reserve Account"
        OR new "Treasury General Account ..." (any sub-label).
      - balance column is the first of these to exist + have data:
        close_today_bal, today_bal, account_balance, open_today_bal.
    """
    df = _fetch_paginated(
        endpoint    = "/v1/accounting/dts/operating_cash_balance",
        filter_expr = f"record_date:gte:{start}",
        # no fields= filter so we tolerate schema renames
    )
    if df.empty or "account_type" not in df.columns:
        return pd.Series(dtype=float, name="tga_balance_musd")

    mask = (
        df["account_type"].str.contains("Treasury General Account",
                                         case=False, na=False)
        | (df["account_type"] == "Federal Reserve Account")
    )
    df = df[mask].copy()
    if df.empty:
        return pd.Series(dtype=float, name="tga_balance_musd")

    df["record_date"] = pd.to_datetime(df["record_date"])

    # Per-row coalesce: legacy rows store the balance in close_today_bal,
    # post-April-2022 rows may use today_bal / account_balance / open_today_bal.
    # Pick the first non-null candidate PER ROW (not globally).
    bal_candidates = ["close_today_bal", "today_bal", "account_balance",
                      "open_today_bal"]
    cols_present = [c for c in bal_candidates if c in df.columns]
    if not cols_present:
        print(f"[dts] tga_balance: no balance column in {list(df.columns)}")
        return pd.Series(dtype=float, name="tga_balance_musd")
    for c in cols_present:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Vectorised first-non-null across columns:  bfill across columns,
    # then take the first column.
    df["_bal"] = df[cols_present].bfill(axis=1).iloc[:, 0]
    bal_col = "_bal"
    if df[bal_col].notna().sum() == 0:
        print(f"[dts] tga_balance: all balance values null in {cols_present}")
        return pd.Series(dtype=float, name="tga_balance_musd")

    # Prefer "(TGA) Closing Balance" label specifically; fall back to any
    # TGA-shaped row, then to legacy "Federal Reserve Account".
    def _priority(at):
        s = str(at)
        if "Closing Balance" in s:                  return 3
        if "Treasury General Account" in s:         return 2
        if s == "Federal Reserve Account":          return 1
        return 0
    df["_priority"] = df["account_type"].apply(_priority)
    df = (df.sort_values(["record_date", "_priority"], ascending=[True, False])
            .drop_duplicates("record_date", keep="first"))

    s = (df.set_index("record_date")[bal_col]
           .sort_index()
           .dropna()
           .rename("tga_balance_musd"))
    return s


# ============================================================
#  2) TGA flows  (deposits + withdrawals by category)
# ============================================================
def fetch_tga_flows(start: str = "2024-01-01") -> pd.DataFrame:
    """TGA daily deposits / withdrawals by category.

    DISABLED for now -- all known endpoint URLs return 404 after Treasury's
    April 2022 DTS restructuring.  The correct path needs verification at
    https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/
    Re-enable by setting candidates to the discovered URL.
    """
    # Quietly return empty -- no point spamming retries against 404s
    print("[dts] flows: disabled until correct endpoint URL is confirmed")
    return pd.DataFrame()
    # ---- legacy candidates kept for reference (all 404 as of May 2026) ----
    candidates = [
        "/v1/accounting/dts/deposits_withdrawals_operating_cash",
        "/v2/accounting/dts/deposits_withdrawals_operating_cash",
        "/v1/accounting/dts/dts_table_2",
    ]
    df = pd.DataFrame()
    for ep in candidates:
        try:
            df = _fetch_paginated(endpoint=ep,
                                   filter_expr=f"record_date:gte:{start}")
            if not df.empty:
                print(f"[dts] flows: using endpoint {ep}")
                break
        except Exception:  # noqa: BLE001
            continue
    if df.empty:
        return pd.DataFrame()
    if "record_date" in df.columns:
        df["record_date"] = pd.to_datetime(df["record_date"])
    if "transaction_today_amt" in df.columns:
        df["transaction_today_amt"] = pd.to_numeric(df["transaction_today_amt"],
                                                     errors="coerce")
        df = df.rename(columns={"transaction_today_amt": "today"})
    return df.dropna(subset=["today"]) if "today" in df.columns else df


def tga_net_flow(flows_df: pd.DataFrame) -> pd.Series:
    if flows_df.empty:
        return pd.Series(dtype=float, name="tga_net_flow_musd")
    pivot = (flows_df[flows_df["transaction_catg"].isin(("Total Deposits",
                                                         "Total Withdrawals"))]
             .pivot_table(index="record_date",
                          columns="transaction_catg",
                          values="today",
                          aggfunc="sum"))
    if "Total Deposits" not in pivot or "Total Withdrawals" not in pivot:
        return pd.Series(dtype=float, name="tga_net_flow_musd")
    net = (pivot["Total Deposits"] - pivot["Total Withdrawals"]).dropna()
    return net.rename("tga_net_flow_musd")


# ============================================================
#  3) Debt issuance -- bills vs coupons
# ============================================================
def fetch_debt_issuance(start: str = "2024-01-01") -> pd.DataFrame:
    """Daily public-debt transactions (issued vs redeemed).

    DISABLED for now -- same April-2022 endpoint-rename situation as
    fetch_tga_flows.  Re-enable once correct path is confirmed.
    """
    print("[dts] issuance: disabled until correct endpoint URL is confirmed")
    return pd.DataFrame()
    # ---- legacy candidates kept for reference (all 404 as of May 2026) ----
    candidates = [
        "/v1/accounting/dts/public_debt_cash_issues",
        "/v1/accounting/dts/public_debt_transactions",
        "/v1/accounting/dts/dts_table_3a",
    ]
    df = pd.DataFrame()
    for ep in candidates:
        try:
            df = _fetch_paginated(endpoint=ep,
                                   filter_expr=f"record_date:gte:{start}")
            if not df.empty:
                print(f"[dts] issuance: using endpoint {ep}")
                break
        except Exception:  # noqa: BLE001
            continue
    if df.empty:
        return pd.DataFrame()
    if "record_date" in df.columns:
        df["record_date"] = pd.to_datetime(df["record_date"])
    if "transaction_today_amt" in df.columns:
        df["transaction_today_amt"] = pd.to_numeric(df["transaction_today_amt"],
                                                     errors="coerce")
        df = df.rename(columns={"transaction_today_amt": "today"})
    return df.dropna(subset=["today"]) if "today" in df.columns else df


def issuance_bills_vs_coupons(issu_df: pd.DataFrame) -> pd.DataFrame:
    if issu_df.empty:
        return pd.DataFrame()
    bill_mask   = issu_df["security_type_desc"].str.contains("Bill", case=False,
                                                              na=False)
    coupon_kw   = ("Note", "Bond", "Inflation", "FRN", "Floating")
    coupon_mask = issu_df["security_type_desc"].apply(
        lambda x: any(k in (x or "") for k in coupon_kw))
    sign = issu_df["transaction_type_desc"].apply(
        lambda x: 1 if "Issue" in (x or "") else (-1 if "Redem" in (x or "") else 0))
    sub = issu_df.assign(_sign=sign)
    sub["bills_net"]   = sub["today"] * sub["_sign"] * bill_mask
    sub["coupons_net"] = sub["today"] * sub["_sign"] * coupon_mask
    out = (sub.groupby("record_date")[["bills_net", "coupons_net"]]
              .sum()
              .rename(columns={"bills_net":   "bills_net_musd",
                               "coupons_net": "coupons_net_musd"}))
    out["total_net_musd"] = out["bills_net_musd"] + out["coupons_net_musd"]
    return out
