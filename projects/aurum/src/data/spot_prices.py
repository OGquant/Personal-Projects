"""
Spot prices fetcher: Gold, Silver, DXY, FX pairs, Oil, BTC, VIX, Bond ETFs.
Primary source: yfinance.
"""
import pandas as pd
import yfinance as yf
from loguru import logger
from src.data import cache
from src.config import Config

# Ticker map — everything an institutional metals desk watches
TICKERS = {
    # Precious metals
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "Platinum": "PL=F",
    "Palladium": "PA=F",
    # Dollar & FX
    "DXY": "DX-Y.NYB",
    "USD/INR": "INR=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CNY": "CNY=X",
    "USD/CHF": "CHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/ZAR": "ZAR=X",
    # Energy
    "WTI Crude": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
    # Crypto
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    # Fear
    "VIX": "^VIX",
    # Equities
    "S&P 500": "^GSPC",
    "NIFTY 50": "^NSEI",
    # ETFs (metals)
    "GLD": "GLD",
    "SLV": "SLV",
    "IAU": "IAU",
}


def fetch_live_prices() -> pd.DataFrame:
    """Fetch current prices for all tracked instruments."""
    def _fetch():
        records = []
        tickers_list = list(TICKERS.values())
        try:
            data = yf.download(tickers_list, period="2d", group_by="ticker", progress=False, threads=True)
            for name, ticker in TICKERS.items():
                try:
                    if len(TICKERS) > 1:
                        ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None
                    else:
                        ticker_data = data
                    if ticker_data is not None and not ticker_data.empty:
                        last = ticker_data.iloc[-1]
                        prev = ticker_data.iloc[-2] if len(ticker_data) > 1 else last
                        price = float(last["Close"])
                        prev_close = float(prev["Close"])
                        change = price - prev_close
                        change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
                        records.append({
                            "instrument": name,
                            "ticker": ticker,
                            "price": round(price, 4),
                            "change": round(change, 4),
                            "change_pct": round(change_pct, 2),
                            "high": round(float(last.get("High", price)), 4),
                            "low": round(float(last.get("Low", price)), 4),
                            "volume": int(last.get("Volume", 0)),
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse {name}: {e}")
        except Exception as e:
            logger.error(f"yfinance batch download failed: {e}")
            # Fallback: fetch individually
            for name, ticker in TICKERS.items():
                try:
                    t = yf.Ticker(ticker)
                    info = t.fast_info
                    price = info.get("lastPrice", 0) or info.get("regularMarketPrice", 0)
                    prev = info.get("previousClose", price) or info.get("regularMarketPreviousClose", price)
                    change = price - prev if prev else 0
                    change_pct = (change / prev * 100) if prev else 0
                    records.append({
                        "instrument": name,
                        "ticker": ticker,
                        "price": round(float(price), 4),
                        "change": round(float(change), 4),
                        "change_pct": round(float(change_pct), 2),
                    })
                except Exception:
                    pass
        return pd.DataFrame(records) if records else pd.DataFrame()

    return cache.cached("spot_prices_live", _fetch, ttl=Config.TTL_REALTIME)


def fetch_history(ticker_key: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch historical OHLCV for a single instrument."""
    ticker = TICKERS.get(ticker_key, ticker_key)

    def _fetch():
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df.empty:
                return pd.DataFrame()
            df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
            df.index.name = "date"
            return df.reset_index()
        except Exception as e:
            logger.error(f"History fetch failed for {ticker}: {e}")
            return pd.DataFrame()

    ttl = Config.TTL_DAILY if interval == "1d" else Config.TTL_INTRADAY
    return cache.cached(f"history_{ticker}_{period}_{interval}", _fetch, ttl=ttl)


def fetch_multi_history(keys: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Fetch historical data for multiple instruments."""
    result = {}
    for key in keys:
        df = fetch_history(key, period=period)
        if df is not None and not df.empty:
            result[key] = df
    return result
