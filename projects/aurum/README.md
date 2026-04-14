# 🥇 AURUM — Metals Intelligence Terminal

An institutional-grade precious metals dashboard for MCX Gold & Silver trading. Aggregates every signal a metals desk monitors: spot prices, macro, positioning, geopolitics, options flow, and trading tools.

## 8 Dashboard Pages

| Page | Content |
|------|---------|
| 🏠 Market Overview | Live spot prices (25+ instruments), candlestick charts, key ratios, ETF monitor |
| 📈 Futures & OI | Price history, CFTC COT managed money positioning |
| 🔗 Options Flow | Black-76 calculator, IV smile, synthetic chain with Greeks, contract specs |
| 🌍 Macro Dashboard | Real rates vs gold, FRED data (CPI/M2/Fed), DXY overlay, central bank reserves |
| 📡 Intelligence | Polymarket geopolitical bets, metals news feed with relevance scoring |
| 🛠️ Trading Tools | Payoff builder (straddle/strangle/IC), margin calc, MCX-COMEX arb, Almgren-Chriss execution |
| 📊 Analytics Lab | Monte Carlo (GBM + jump), GARCH, vol cone, correlation matrix, seasonality, technicals |
| ⚠️ Risk Dashboard | Parametric/Historical VaR, CVaR, drawdown, stress scenarios, Sharpe/Sortino |

## Data Sources

- **yfinance**: Gold, Silver, DXY, 8 FX pairs, oil, BTC, VIX, equities, ETFs
- **FRED**: M2, CPI, PPI, Fed funds, TIPS, real rates, unemployment
- **CFTC**: COT managed money positioning (weekly)
- **Polymarket**: War, sanctions, Fed, tariffs, dedollarization bets
- **RSS/NewsAPI**: Metals-relevant news with keyword scoring
- **Static/WGC**: Central bank gold reserves, annual demand data

## Quick Start

```bash
# 1. Clone/copy to your workspace
cp -r aurum ~/Desktop/ai-workspace/projects/aurum

# 2. Setup venv (or use shared workspace venv)
cd ~/Desktop/ai-workspace/projects/aurum
python3.13 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Add API keys for enhanced data
cp config/.env.example config/.env
# Edit config/.env with your FRED_API_KEY, NEWS_API_KEY, etc.

# 5. Run
streamlit run src/app.py
```

## Optional API Keys

The terminal works without any API keys (uses yfinance + public data). For enhanced data:

| Key | Source | What it unlocks |
|-----|--------|-----------------|
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) | Full macro data (CPI, M2, etc.) — free |
| `NEWS_API_KEY` | [NewsAPI](https://newsapi.org/) | Enhanced news feed — free tier available |
| `KITE_API_KEY` | [Kite Connect](https://kite.trade/) | Live MCX data + option chains |

## Project Structure

```
aurum/
├── src/
│   ├── app.py                    # Main entry point
│   ├── config.py                 # Config loader
│   ├── data/                     # Data fetchers
│   │   ├── cache.py              # File-based TTL cache
│   │   ├── spot_prices.py        # 25+ instruments via yfinance
│   │   ├── fred_macro.py         # FRED macro series
│   │   ├── cot_reports.py        # CFTC COT parser
│   │   ├── polymarket.py         # Prediction markets
│   │   ├── news_feed.py          # RSS + NewsAPI aggregator
│   │   ├── etf_flows.py          # GLD/SLV/IAU monitor
│   │   └── central_banks.py      # Gold reserves data
│   ├── analytics/                # Quant models
│   │   ├── greeks.py             # Black-76 options Greeks
│   │   ├── volatility.py         # GARCH, EWMA, vol cone
│   │   ├── monte_carlo.py        # GBM + jump diffusion
│   │   ├── correlation.py        # Cross-asset correlation
│   │   ├── seasonality.py        # Monthly/weekly patterns
│   │   ├── technicals.py         # SMA, RSI, MACD, Bollinger
│   │   ├── ratios.py             # Gold/Silver, Gold/Oil, etc.
│   │   └── risk.py               # VaR, CVaR, stress tests
│   ├── trading/                  # Trading tools
│   │   ├── contracts.py          # MCX + CME contract specs
│   │   ├── payoff.py             # Option payoff diagrams
│   │   ├── margin_calc.py        # MCX margin calculator
│   │   └── rollover.py           # Rollover, basis arb, execution
│   └── pages/                    # Streamlit pages
│       ├── 2_futures_oi.py
│       ├── 3_options_flow.py
│       ├── 4_macro_dashboard.py
│       ├── 5_intelligence.py
│       ├── 6_trading_tools.py
│       ├── 7_analytics.py
│       └── 8_risk_dashboard.py
├── .streamlit/config.toml        # Dark theme config
└── requirements.txt
```

## Deploying to Streamlit Community Cloud (Free)

### Prerequisites
- This repo pushed to GitHub (public or private)
- A [Streamlit Community Cloud](https://share.streamlit.io) account (free, sign up with GitHub)

### Step-by-Step

1. **Go to** [share.streamlit.io](https://share.streamlit.io) → Click **"New app"**

2. **Fill in the deployment form:**
   | Field | Value |
   |-------|-------|
   | Repository | `OGquant/Personal-Projects` |
   | Branch | `main` |
   | Main file path | `projects/aurum/src/app.py` |

3. **Click "Advanced settings"** → Add your API keys as secrets in TOML format:
   ```toml
   FRED_API_KEY = "your_fred_key_here"
   NEWS_API_KEY = "your_newsapi_key_here"
   KITE_API_KEY = ""
   KITE_ACCESS_TOKEN = ""
   LOG_LEVEL = "INFO"
   ```
   > These are injected as `st.secrets` — the app reads them automatically via `config.py`.

4. **Click "Deploy"** — Streamlit will install dependencies from `projects/aurum/requirements.txt` and launch the app.

### Custom App URL

After deployment, go to **Settings → General → Custom subdomain** and set it to `aurum` to get:
```
https://aurum.streamlit.app
```

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Import errors (`ModuleNotFoundError`) | Ensure "Main file path" is `projects/aurum/src/app.py` — Streamlit sets the working directory to the file's parent |
| Missing packages | The app reads `requirements.txt` from the repo root first, then the project folder. Add a symlink or copy if needed |
| Secrets not loading | Check TOML syntax in Streamlit dashboard → Settings → Secrets |
| App crashes on boot | Check the Streamlit Cloud logs (bottom-right "Manage app" → "Logs") |

---

## Tech Stack

Python 3.13 · Streamlit · Plotly · pandas · numpy · scipy · yfinance · fredapi · arch (GARCH)

## Models Used

- **Black-76**: Options pricing for futures options (not Black-Scholes)
- **GARCH(1,1)**: Volatility forecasting with persistence estimation
- **GBM + Merton Jump Diffusion**: Monte Carlo price simulation
- **Almgren-Chriss**: Optimal execution scheduling
- **Parametric/Historical VaR**: Risk measurement at 95%/99% confidence

---
*Built by Anuj Pilania · Codename AURUM*

