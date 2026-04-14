# 🧪 Personal Projects

A collection of quantitative finance and data-driven projects by **Anuj Pilania**.

---

## Projects

### 🥇 [AURUM — Metals Intelligence Terminal](projects/aurum/)

An institutional-grade precious metals dashboard for MCX Gold & Silver trading. Built with Streamlit, it aggregates every signal a metals desk monitors — live prices, macro indicators, positioning data, geopolitics, options flow, and quant analytics — into a single terminal.

**8 Dashboard Pages**: Market Overview · Futures & OI · Options Flow · Macro Dashboard · Intelligence Feed · Trading Tools · Analytics Lab · Risk Dashboard

**Models**: Black-76 · GARCH(1,1) · Monte Carlo (GBM + Jump) · Almgren-Chriss Execution · VaR/CVaR

**Stack**: Python 3.13 · Streamlit · Plotly · pandas · numpy · scipy · yfinance · fredapi · arch

🔗 **Live Demo**: [aurum.streamlit.app](https://aurum.streamlit.app) *(coming soon)*

---

## Quick Start — Running Any Project

Each project lives in its own folder under `projects/`. Here's how to get any of them running:

### Prerequisites

- **Python 3.13+** — [Download](https://www.python.org/downloads/)
- **Git** — [Download](https://git-scm.com/downloads)

### 1. Clone the repo

```bash
git clone https://github.com/OGquant/Personal-Projects.git
cd Personal-Projects
```

### 2. Create a virtual environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install project dependencies

Each project has its own `requirements.txt`:

```bash
pip install -r projects/<project-name>/requirements.txt

# Example: for AURUM
pip install -r projects/aurum/requirements.txt
```

### 4. Configure environment variables (if needed)

Some projects use optional API keys. Copy the example and fill in your keys:

```bash
cp projects/<project-name>/config/.env.example projects/<project-name>/config/.env
# Edit the .env file with your API keys
```

> **Note**: Most projects work without API keys — they fall back to free public data sources.

### 5. Run the project

**Streamlit apps** (dashboards):
```bash
cd projects/<project-name>
streamlit run src/app.py
```

The app will open at `http://localhost:8501`.

---

## Project Structure

```
Personal-Projects/
├── README.md                    # This file
├── .gitignore
├── projects/
│   └── aurum/                   # Metals Intelligence Terminal
│       ├── README.md            # Detailed project docs
│       ├── requirements.txt     # Python dependencies
│       ├── config/
│       │   └── .env.example     # API key template
│       ├── .streamlit/
│       │   └── config.toml      # Streamlit theme config
│       └── src/
│           ├── app.py           # Main entry point
│           ├── config.py        # Config loader
│           ├── data/            # Data fetchers
│           ├── analytics/       # Quant models
│           ├── trading/         # Trading tools
│           └── pages/           # Dashboard pages
└── ...                          # Future projects
```

---

## API Keys Reference

| Key | Source | Cost | Used By |
|-----|--------|------|---------|
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) | Free | AURUM — Macro data |
| `NEWS_API_KEY` | [NewsAPI](https://newsapi.org/) | Free tier | AURUM — News feed |
| `KITE_API_KEY` | [Kite Connect](https://kite.trade/) | ₹2000/mo | AURUM — Live MCX |

---

## Deployment

### Streamlit Community Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repo → `projects/aurum/src/app.py`
5. Add secrets via the Streamlit dashboard (Settings → Secrets)

See the [Deployment Guide](#deploying-aurum-to-streamlit-cloud) in the AURUM README for details.

---

## License

Private repository. All rights reserved.

---

*Built by Anuj Pilania*
