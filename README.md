# BTC Macro Liquidity Release-Valve Dashboard

A systematic Python framework that operationalises Capital Flows Research's
*"Bitcoin as a Macro Liquidity Release Valve"* paper. It ingests free macro and
crypto-microstructure data, computes a composite **Regime Score**, and serves
the result as an interactive Streamlit dashboard. A daily GitHub Actions cron
keeps the parquet snapshots fresh.

## Framework summary

The full mapping (paper concept → indicator → data source → signal logic) lives in
[`FRAMEWORK.md`](./FRAMEWORK.md). Five layers feed the regime score:

| # | Layer | Weight | Captures |
|---|---|---|---|
| 1 | Macro Liquidity | 35% | real rates, net liquidity, M2, DXY |
| 2 | Risk Curve | 20% | HY spreads, VIX, ARKK/SPY, IWM/SPY, copper-gold |
| 3 | BTC Microstructure | 25% | ETF flows, funding, OI, DVOL |
| 4 | Lead/Lag | 15% | MSTR, COIN, miners, ETH/BTC, stables |
| 5 | Positioning Extremes | 5% | contrarian triggers (z-score) |

Composite regime → bias label → suggested position weight + backtest vs BTC HODL.

## Repo layout

```
btc_macro_micro_dashboard/
├── FRAMEWORK.md              # full systematic spec
├── README.md
├── requirements.txt
├── config/
│   └── indicators.yaml       # tickers, weights, thresholds
├── src/
│   ├── data/                 # FRED, Yahoo, CoinGecko, derivatives, ETF flows
│   ├── signals/              # one module per layer
│   ├── scoring.py            # composite + bias mapping
│   ├── backtest.py           # BTC vs strategy
│   ├── pipeline.py           # orchestrator (run me daily)
│   └── utils.py
├── app/
│   └── dashboard.py          # Streamlit front-end
├── data/                     # parquet snapshots committed by GH Actions
├── notebooks/                # research scratch
└── .github/workflows/etl.yml # daily cron
```

## Quick start (local)

```bash
git clone <your-repo>.git
cd btc_macro_micro_dashboard
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# OPTIONAL — get a free FRED key at https://fred.stlouisfed.org/docs/api/api_key.html
export FRED_API_KEY=<your_key>                         # Windows: setx FRED_API_KEY <your_key>

# fetch all data + compute scores + run backtest
python -m src.pipeline

# launch dashboard
streamlit run app/dashboard.py
```

## Automating updates (GitHub Actions)

The included workflow (`.github/workflows/etl.yml`) runs the pipeline at 22:00 UTC
daily and commits fresh parquet snapshots back to the repo. Add `FRED_API_KEY`
as a GitHub repository secret if you want the FRED API path; otherwise the
fetcher falls back to the public CSV endpoint (slower but auth-less).

## Tuning the model

All knobs live in `config/indicators.yaml`:
- **`weights`** — change layer importance.
- **`extremes`** — z-score thresholds for alerts.
- **Add/remove tickers** under `macro`, `risk_curve`, `leadlag`.

After editing, re-run `python -m src.pipeline`.

## Roadmap / extension ideas

- Plug in MVRV-Z and Coin-Days-Destroyed (Glassnode free or scraped).
- Add CME COT report for hedge-fund net positioning.
- Add proper Deribit options skew history (DVI / paid feed).
- ETH overlay regime (ETH has its own ETF flow + staking yield dynamics).
- Telegram / email alerts when alerts file flips state.
- Replace flat weights with a logistic regression trained against forward BTC returns.

## Disclaimer

Educational tool. No investment advice. Free public data sources can lag, fail
or be rate-limited; verify before trading on any signal.
