"""Regulatory anatomy — static + low-frequency reference data.

The ANATOMY tab on the Plumbing page renders the constraint structure that
governs every flow elsewhere on the dashboard:

  * Capital ratio stack (CET1 / Tier 1 / Total + buffers) per Fed Category
  * G-SIB surcharge per US-domiciled G-SIB (Method 1 vs Method 2 results)
  * SCB (Stress Capital Buffer) — published by Fed each June after CCAR
  * SLR / eSLR rules + currently effective ratios for the six US G-SIBs
  * TLAC + LTD framework

Cadence:  most of this updates **once a year** (Fed publishes G-SIB list +
surcharges in Q4; CCAR/SCB results in June).  We keep the latest cycle's
values here as Python literals — refresh annually.

Sources:
  * Fed Board G-SIB scores                — https://www.federalreserve.gov/publications/files/large-bank-capital-requirements-20240828.pdf
  * Fed CCAR / SCB results                — https://www.federalreserve.gov/publications/files/2024-dfast-results-20240626.pdf
  * Y-9C bank holding company filings     — https://www.ffiec.gov/npw/FinancialReport/FinancialDataDownload
  * SLR / eSLR rule text                  — 12 CFR 217 (Regulation Q)
"""
from __future__ import annotations

import pandas as pd


# ============================================================
#  Static regulatory rule structure
# ============================================================
# All values in percent (so 4.5 means 4.5%).
CAPITAL_RATIO_MINIMUMS = {
    "CET1":           4.5,
    "Tier 1":         6.0,
    "Total Capital":  8.0,
    "Tier 1 Leverage": 4.0,
    "SLR":            3.0,    # all banks
    "eSLR add-on":    2.0,    # G-SIBs only — buffer above 3% min
    "eSLR at IDIs":   3.0,    # extra requirement at FDIC-insured subsidiaries
}

CAPITAL_BUFFERS = {
    "CCB Standardized":   2.5,    # standardised approach: fixed
    "SCB Advanced":       2.5,    # advanced approach: fixed
    "CCyB":               0.0,    # currently 0% in US (not activated by Fed)
    "G-SIB surcharge":    None,   # variable per bank (see below)
    "SCB":                None,   # variable per bank (see below)
}

FED_BANK_CATEGORIES = {
    "Cat I":     ">$700bn assets OR US G-SIB",
    "Cat II":    "≥$700bn  OR  ≥$75bn cross-juris activity",
    "Cat III":   "≥$250bn  OR  ≥$75bn nonbank/STWF/OBSE",
    "Cat IV":    "$100–$250bn",
    "Cat V":     "$50–$100bn (other firms)",
}


# ============================================================
#  US G-SIBs — 2024-25 cycle (effective from 2025 reporting)
# ============================================================
# Method 1 = BCBS methodology  ·  Method 2 = Fed Board methodology
# Effective surcharge = max(Method 1, Method 2)   per FR rule.
# Source: Fed Board, "Large Bank Capital Requirements" 2024-08-28 release.
US_GSIB_SURCHARGES_2024 = pd.DataFrame([
    # bank,  method_1, method_2, effective
    ("JPMorgan Chase",   2.5, 4.5, 4.5),
    ("Bank of America",  1.5, 3.0, 3.0),
    ("Citigroup",        2.0, 3.0, 3.0),
    ("Goldman Sachs",    1.5, 3.0, 3.0),
    ("Morgan Stanley",   1.5, 3.0, 3.0),
    ("Wells Fargo",      1.0, 2.0, 2.0),
    ("State Street",     1.0, 1.0, 1.0),
    ("Bank of NY Mellon",1.0, 1.0, 1.0),
], columns=["bank", "method_1_pct", "method_2_pct", "effective_pct"])


# ============================================================
#  SCB — 2024 CCAR cycle (effective Oct 1, 2024 – Sep 30, 2025)
# ============================================================
# Source: Fed CCAR June 2024 results.
SCB_2024 = pd.DataFrame([
    ("JPMorgan Chase",    3.3),
    ("Bank of America",   3.2),
    ("Citigroup",         4.1),
    ("Goldman Sachs",     6.2),
    ("Morgan Stanley",    5.1),
    ("Wells Fargo",       3.8),
    ("State Street",      2.5),
    ("Bank of NY Mellon", 2.5),
], columns=["bank", "scb_pct"])


def regulatory_stack_for_gsib(bank: str) -> dict:
    """Return the full effective ratio stack for one G-SIB.

    ``CET1 minimum effective`` = 4.5 + SCB + G-SIB surcharge
    ``SLR minimum effective``  = 3.0  (+2.0 eSLR if G-SIB)
    """
    g = US_GSIB_SURCHARGES_2024.set_index("bank")
    s = SCB_2024.set_index("bank")
    if bank not in g.index or bank not in s.index:
        return {}
    gsib   = float(g.loc[bank, "effective_pct"])
    scb    = float(s.loc[bank, "scb_pct"])
    cet1_min_total = 4.5 + scb + gsib
    return {
        "bank":               bank,
        "CET1 minimum":        4.5,
        "SCB":                 scb,
        "G-SIB surcharge":     gsib,
        "CET1 effective min":  cet1_min_total,
        "SLR minimum":         3.0,
        "eSLR buffer":         2.0,
        "SLR effective min":   5.0,   # 3.0 + 2.0 eSLR for G-SIBs
    }


def all_gsib_regulatory_stacks() -> pd.DataFrame:
    """Return one row per G-SIB with the effective minimum ratios."""
    rows = [regulatory_stack_for_gsib(b)
            for b in US_GSIB_SURCHARGES_2024["bank"]]
    return pd.DataFrame([r for r in rows if r])


# ============================================================
#  Effective SLR / eSLR — quarterly snapshot (Y-9C, manual refresh)
# ============================================================
# Latest available cycle: Q4 2024 (filed Feb 2025).  Refresh quarterly from:
# https://www.ffiec.gov/npw/Institution/Profile/<RSSD ID>
# Source: company 10-Q filings (Pillar 3 / Capital section).
EFFECTIVE_SLR_Q4_2024 = pd.DataFrame([
    # bank,                slr,  cet1,  tier1,  total
    ("JPMorgan Chase",     6.1, 15.7, 16.5, 18.5),
    ("Bank of America",    6.1, 13.5, 14.4, 16.0),
    ("Citigroup",          5.8, 13.6, 15.4, 17.5),
    ("Goldman Sachs",      5.7, 14.6, 16.7, 19.0),
    ("Morgan Stanley",     5.5, 15.6, 17.5, 19.7),
    ("Wells Fargo",        7.0, 11.1, 12.5, 14.7),
], columns=["bank", "slr_pct", "cet1_pct", "tier1_pct", "total_pct"])


# ============================================================
#  TLAC / LTD framework — context
# ============================================================
TLAC_FRAMEWORK = {
    "Risk-based TLAC (G-SIBs SPOE)":  18.0,   # %RWA + buffers
    "Risk-based TLAC (G-SIBs MPOE)":  16.0,
    "Leverage-based TLAC SPOE":       9.5,
    "Leverage-based TLAC MPOE":       6.75,
    "LTD risk-based":                  6.0,   # (+ G-SIB max surcharge)
    "LTD leverage-based":              4.5,
}
