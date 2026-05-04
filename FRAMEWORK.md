# Bitcoin as a Macro Liquidity Release Valve — Systematic Framework

**Source:** Capital Flows Research, *"Bitcoin as a Macro Liquidity Release Valve"* (21 pages).
**Purpose of this doc:** Translate the paper's narrative into an explicit, code-able framework — every concept becomes (a) an indicator, (b) a data source, (c) a signal rule, (d) an action.

The framework has five layers. Each layer feeds a composite **Regime Score** (-100 ↔ +100) that drives positioning bias.

```
Layer 1  MACRO LIQUIDITY REGIME       weight 35%   →  the wind direction
Layer 2  RISK-CURVE / RISK FLOWS      weight 20%   →  is liquidity flowing into risk?
Layer 3  BTC MICROSTRUCTURE / FLOWS   weight 25%   →  positioning fragility
Layer 4  LEAD/LAG CROSS-MARKET        weight 15%   →  early warning system
Layer 5  POSITIONING EXTREMES         weight  5%   →  contrarian triggers
```

---

## Layer 1 — Macro Liquidity Regime  (the tide)

> "Bitcoin goes up when the price of money (real rates) is low and the quantity of money is high."

| Indicator | Source (free) | Signal logic | Bias |
|---|---|---|---|
| **10Y US Real Yield** (`DFII10`) | FRED | falling / negative | bullish |
| **2s10s Yield Curve** | FRED (`T10Y2Y`) | bull-steepening | bullish |
| **Fed Balance Sheet** (`WALCL`) | FRED | 4w & 13w change > 0 | bullish |
| **Reverse Repo (RRP)** | FRED (`RRPONTSYD`) | falling RRP = liquidity into system | bullish |
| **Treasury General Account (TGA)** | FRED (`WTREGEN`) | falling TGA = liquidity injection | bullish |
| **Net Liquidity** = WALCL − RRP − TGA | derived | rising 4w | bullish |
| **Global M2** (US + EZ + JP + CN, FX-adjusted) | FRED + ECB + BOJ + PBOC mirrors | YoY > 0, 13w MA rising | bullish |
| **5Y Breakeven Inflation** (`T5YIE`) | FRED | rising while real rates flat | bullish |
| **DXY** | Yahoo (`DX-Y.NYB`) | falling | bullish |
| **USDJPY** | Yahoo (`JPY=X`) | sharp moves = liquidity-shift signal | regime shift |

**Composite output:** `macro_score ∈ [-1, 1]` = z-score weighted blend.
- `> +0.3` → expansionary regime → long-bias, "buy the dip" mode
- `−0.3 … +0.3` → neutral / mixed → reduce size, trade ranges
- `< −0.3` → contractionary → defensive / short rallies

---

## Layer 2 — Risk-Curve Positioning  (is capital moving outward?)

> "Bitcoin is the last stop on the risk curve."

| Indicator | Source | Signal logic |
|---|---|---|
| **HY OAS spread** (`BAMLH0A0HYM2`) | FRED | tightening = risk-on |
| **VIX** | Yahoo (`^VIX`) | < 16 risk-on, > 25 risk-off |
| **MOVE Index** | Yahoo (`^MOVE`) proxy or FRED | rising = bond-vol stress = risk-off |
| **ARKK / SPY ratio** | Yahoo | rising = speculative appetite |
| **Russell 2000 / SPX (`IWM/SPY`)** | Yahoo | rising = small-cap risk-on |
| **Semis (SOXX) vs SPY** | Yahoo | rising = high-beta leadership |
| **EMFX Index (CEW)** | Yahoo | rising = global risk-on |
| **Copper / Gold** | Yahoo (`HG=F`, `GC=F`) | rising = pro-cyclical |
| **Defensives (XLP/XLU) vs SPY** | Yahoo | falling = risk-on |
| **AAII Bull-Bear** | aaii.com / FRED mirror | extreme bearish = contrarian buy |

**Output:** `risk_curve_score ∈ [-1, 1]`.

---

## Layer 3 — BTC Microstructure & Flows  (gusts and lulls)

### 3a. ETF Flows
| Indicator | Source | Signal |
|---|---|---|
| Spot-BTC ETF net flows (IBIT, FBTC, BITB, ARKB, GBTC, etc.) | farside.co.uk JSON, SoSoValue, individual issuer feeds | 5d sum > 0 → tailwind |
| ETF AUM growth | derived | rising = institutional bid |
| Days-of-supply absorbed by ETFs | derived (flows / new BTC issuance) | > 1.0 = supply squeeze |

### 3b. Futures Open Interest & Funding
| Indicator | Source | Signal |
|---|---|---|
| Aggregate OI ($) | Coinglass public, Coinalyze API | rapid OI rise + price rise = leverage build-up |
| OI / Market-Cap ratio | derived | > 3% historically = fragile |
| Perp funding rate (8h) | Binance/Bybit/OKX public APIs | > +0.05% sustained = crowded long |
| Funding-rate z-score | derived | |z| > 2 = positioning extreme |
| CME basis | CME public | rising basis = institutional carry trade on |

### 3c. Options Skew & Vol
| Indicator | Source | Signal |
|---|---|---|
| 25-delta skew (1m, 3m, 6m) | Deribit public DVOL/index endpoints | flips deeply negative = fear (contrarian buy); deeply positive = euphoria |
| ATM IV term structure | Deribit | inverted near-term IV > long-term = event risk |
| Put/Call OI ratio | Deribit | < 0.7 = bullish skew, > 1.0 = hedging |
| DVOL vs realized vol | Deribit / derived | IV >> RV = panic; IV << RV = complacency |

### 3d. On-chain (lightweight)
| Indicator | Source | Signal |
|---|---|---|
| Exchange net-flow | Glassnode-free / CryptoQuant-free / mempool.space | inflow = sell pressure |
| MVRV-Z score | Bitcoin-Data, Look-Into-Bitcoin scrape | > 7 = top zone, < 0 = bottom zone |
| Active addresses 30d | mempool / blockchain.info | rising = adoption tailwind |
| LTH / STH supply | Glassnode-free | LTH distributing = supply pressure |

**Output:** `micro_score ∈ [-1, 1]` = blended.

---

## Layer 4 — Lead/Lag Cross-Market  (proxies)

| Indicator | Source | Signal |
|---|---|---|
| **MSTR price + mNAV premium** | Yahoo + holdings disclosure | premium expanding = equity bid for BTC; premium collapse = warning |
| **COIN price + 5d return vs BTC** | Yahoo | divergence flagged |
| **MARA, RIOT, CLSK miners basket** | Yahoo | breaking out = high-beta leadership |
| **CME BTC futures gap** | Yahoo (`BTC=F`) | weekend gaps tend to fill |
| **ETH/BTC ratio** | CoinGecko / Yahoo | rising = late-cycle risk-on |
| **Total altcoin market cap ex-BTC** | CoinGecko | ALT outperformance = euphoria warning |
| **Stablecoin market cap (USDT+USDC)** | CoinGecko | rising = dry powder building |

**Output:** `leadlag_score ∈ [-1, 1]`.

---

## Layer 5 — Positioning Extremes  (contrarian fuel)

Triggered only when |z-score| breaches threshold:

| Trigger | Action |
|---|---|
| Funding z < −2 AND skew deeply negative AND price made fresh lows | **buy** — short-squeeze setup |
| Funding z > +2 AND skew deeply positive AND OI at ATH | **trim / hedge** — long-flush risk |
| ETF flows 5d > 99th percentile AND price flat | **caution** — distribution signal |
| MVRV-Z > 7 | **scale out** |
| MVRV-Z < 0 | **scale in** |
| MSTR mNAV premium collapses > 20% in 5d while BTC flat | **defensive** — equity-side stress |

---

## Composite Regime Score

```
regime_score = 0.35*macro + 0.20*risk_curve + 0.25*micro + 0.15*leadlag + 0.05*extremes
                ∈ [-1, 1]
```

**Mapping to action:**

| Score | Regime label | Position bias | Trade style |
|---|---|---|---|
| `> +0.5` | Strong bullish | full long | momentum / trend |
| `+0.2 … +0.5` | Bullish | long, smaller | buy dips |
| `−0.2 … +0.2` | Mixed / neutral | small / flat | range trade |
| `−0.5 … −0.2` | Bearish | reduced / hedged | sell rallies |
| `< −0.5` | Strong bearish | flat / short | trend-follow down |

---

## If-Then Trade Rules (from §5 of paper)

```
IF macro = positive AND risk_curve = positive AND micro NOT extreme   →  ADD long
IF macro = positive AND micro extreme long                            →  HOLD long, tighten stops
IF macro = positive AND positioning oversold (extreme short)          →  AGGRESSIVE long
IF macro = negative AND risk_curve = negative                         →  REDUCE / SHORT rallies
IF macro = negative AND positioning extreme short                     →  WAIT for relief rally
IF macro flips (FOMC/CB pivot)                                        →  REBALANCE same day
```

---

## Dashboard Views (mapped 1-to-1 to layers)

1. **Regime Tape** — single page: traffic-light per layer + composite score gauge + 90d history of regime score.
2. **Macro Liquidity** — net liquidity, real rates, M2, central bank balance sheets.
3. **Risk Curve** — credit spreads, VIX/MOVE, ARKK/SPY, IWM/SPY, EM, copper-gold.
4. **BTC Flows & Microstructure** — ETF flows, OI, funding, skew, IV, on-chain.
5. **Lead/Lag** — MSTR mNAV, COIN, miners, ETH/BTC, stablecoin supply.
6. **Backtest** — composite signal vs BTC buy-and-hold, drawdowns, hit rate, Sharpe, regime-conditional returns.
7. **Alerts** — current trigger conditions hitting Layer-5 thresholds.

---

## Refresh Cadence

| Data | Frequency | Mechanism |
|---|---|---|
| FRED macro series | daily 22:00 UTC | GH Actions cron |
| Yahoo equities/FX | daily 22:00 UTC | GH Actions cron |
| CoinGecko BTC/ETH | hourly | GH Actions cron + Streamlit on-demand |
| ETF flows | daily after US close | GH Actions cron |
| Funding / OI | every 4h | GH Actions cron |
| Options skew | every 4h | GH Actions cron |
| Dashboard | on page load (read parquet) | Streamlit |
