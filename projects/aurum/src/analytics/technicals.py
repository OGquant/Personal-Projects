"""Technical indicators: SMA, EMA, RSI, MACD, Bollinger, S/R levels."""
import pandas as pd
import numpy as np


def sma(prices: pd.Series, window: int = 20) -> pd.Series:
    return prices.rolling(window).mean()

def ema(prices: pd.Series, span: int = 20) -> pd.Series:
    return prices.ewm(span=span).mean()

def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})

def bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    return pd.DataFrame({"upper": mid + num_std * std, "middle": mid, "lower": mid - num_std * std})

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def support_resistance(prices: pd.Series, window: int = 20) -> dict:
    """Simple pivot-based support/resistance."""
    recent = prices.tail(window)
    high = recent.max()
    low = recent.min()
    close = recent.iloc[-1]
    pivot = (high + low + close) / 3
    return {
        "pivot": round(pivot, 2), "r1": round(2 * pivot - low, 2), "r2": round(pivot + (high - low), 2),
        "s1": round(2 * pivot - high, 2), "s2": round(pivot - (high - low), 2),
    }

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to a price DataFrame."""
    close = df["close"] if "close" in df.columns else df.iloc[:, 0]
    df = df.copy()
    df["sma_20"] = sma(close, 20)
    df["sma_50"] = sma(close, 50)
    df["sma_200"] = sma(close, 200)
    df["ema_12"] = ema(close, 12)
    df["ema_26"] = ema(close, 26)
    df["rsi_14"] = rsi(close, 14)
    macd_df = macd(close)
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["signal"]
    df["macd_hist"] = macd_df["histogram"]
    bb = bollinger_bands(close)
    df["bb_upper"] = bb["upper"]
    df["bb_middle"] = bb["middle"]
    df["bb_lower"] = bb["lower"]
    if "high" in df.columns and "low" in df.columns:
        df["atr_14"] = atr(df["high"], df["low"], close)
    return df
