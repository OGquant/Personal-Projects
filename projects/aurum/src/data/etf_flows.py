"""ETF flows tracker for GLD, SLV, IAU."""
import pandas as pd
import yfinance as yf
from loguru import logger
from src.data import cache
from src.config import Config

METAL_ETFS = {"GLD": "GLD", "SLV": "SLV", "IAU": "IAU", "PHYS": "PHYS", "SIVR": "SIVR"}

def fetch_etf_data(period: str = "1y") -> pd.DataFrame:
    def _fetch():
        records = []
        for name, ticker in METAL_ETFS.items():
            try:
                df = yf.download(ticker, period=period, progress=False)
                if df.empty:
                    continue
                df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                # Volume change as proxy for flow
                vol_avg_20 = df["volume"].tail(20).mean()
                vol_latest = float(latest.get("volume", 0))
                records.append({
                    "etf": name, "price": round(float(latest["close"]), 2),
                    "change_pct": round((float(latest["close"]) - float(prev["close"])) / float(prev["close"]) * 100, 2),
                    "volume": int(vol_latest),
                    "vol_vs_avg": round(vol_latest / vol_avg_20, 2) if vol_avg_20 > 0 else 1.0,
                    "20d_avg_vol": int(vol_avg_20),
                })
            except Exception as e:
                logger.warning(f"ETF {name} failed: {e}")
        return pd.DataFrame(records) if records else pd.DataFrame()
    return cache.cached("etf_flows", _fetch, ttl=Config.TTL_INTRADAY)
