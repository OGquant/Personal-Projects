"""
FRED macro data: M2, CPI, PPI, Fed funds, TIPS, unemployment, real rates.
Uses fredapi if FRED_API_KEY present, else yfinance fallback for key series.
"""
import pandas as pd
from loguru import logger
from src.data import cache
from src.config import Config

# FRED series IDs
SERIES = {
    "Fed Funds Rate": "FEDFUNDS",
    "CPI (YoY)": "CPIAUCSL",
    "Core CPI": "CPILFESL",
    "PPI": "PPIACO",
    "PCE": "PCEPI",
    "Core PCE": "PCEPILFE",
    "M2 Money Supply": "M2SL",
    "Unemployment": "UNRATE",
    "10Y Treasury": "DGS10",
    "2Y Treasury": "DGS2",
    "5Y Treasury": "DGS5",
    "30Y Treasury": "DGS30",
    "10Y TIPS": "DFII10",
    "5Y TIPS": "DFII5",
    "5Y Breakeven": "T5YIE",
    "10Y Breakeven": "T10YIE",
    "Real GDP Growth": "A191RL1Q225SBEA",
    "US Dollar Index (Broad)": "DTWEXBGS",
    "Gold Fixing (LBMA)": "GOLDAMGBD228NLBM",
    "Silver Fixing (LBMA)": "SLVPRUSD",
}


def _get_fred_client():
    """Get FRED client if API key available."""
    if not Config.FRED_API_KEY:
        return None
    try:
        from fredapi import Fred
        return Fred(api_key=Config.FRED_API_KEY)
    except ImportError:
        logger.warning("fredapi not installed, using fallback")
        return None


def fetch_series(series_name: str, period: str = "10y") -> pd.DataFrame:
    """Fetch a single FRED series."""
    series_id = SERIES.get(series_name, series_name)

    def _fetch():
        fred = _get_fred_client()
        if fred:
            try:
                s = fred.get_series(series_id)
                df = pd.DataFrame({"date": s.index, "value": s.values})
                df["series"] = series_name
                return df
            except Exception as e:
                logger.error(f"FRED fetch failed for {series_id}: {e}")
        # Fallback: try yfinance for treasury yields
        import yfinance as yf
        yf_map = {"10Y Treasury": "^TNX", "2Y Treasury": "^IRX", "5Y Treasury": "^FVX"}
        if series_name in yf_map:
            try:
                data = yf.download(yf_map[series_name], period=period, progress=False)
                if not data.empty:
                    df = data[["Close"]].reset_index()
                    df.columns = ["date", "value"]
                    df["series"] = series_name
                    return df
            except Exception:
                pass
        return pd.DataFrame()

    return cache.cached(f"fred_{series_id}", _fetch, ttl=Config.TTL_DAILY)


def fetch_macro_dashboard() -> dict[str, pd.DataFrame]:
    """Fetch key macro indicators for the dashboard."""
    key_series = [
        "Fed Funds Rate", "CPI (YoY)", "M2 Money Supply",
        "10Y Treasury", "2Y Treasury", "10Y TIPS",
        "10Y Breakeven", "Unemployment", "US Dollar Index (Broad)",
        "Gold Fixing (LBMA)", "Silver Fixing (LBMA)",
    ]
    result = {}
    for name in key_series:
        df = fetch_series(name)
        if df is not None and not df.empty:
            result[name] = df
    return result


def compute_real_rate() -> pd.DataFrame:
    """Compute real interest rate = 10Y nominal - 10Y breakeven."""
    nom = fetch_series("10Y Treasury")
    tips = fetch_series("10Y TIPS")
    if nom.empty or tips.empty:
        return pd.DataFrame()
    nom = nom.set_index("date")["value"].dropna()
    tips = tips.set_index("date")["value"].dropna()
    combined = pd.DataFrame({"nominal_10y": nom, "tips_10y": tips}).dropna()
    combined["real_rate"] = combined["nominal_10y"] - (combined["nominal_10y"] - combined["tips_10y"])
    combined["real_rate_approx"] = combined["tips_10y"]
    return combined.reset_index()
