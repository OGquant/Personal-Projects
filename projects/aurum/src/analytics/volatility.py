"""
Volatility models: GARCH(1,1), EWMA, realized volatility, vol term structure.
"""
import math
import numpy as np
import pandas as pd
from loguru import logger


def realized_vol(prices: pd.Series, window: int = 21, annualize: int = 252) -> pd.Series:
    """Rolling realized volatility from close prices."""
    log_returns = np.log(prices / prices.shift(1)).dropna()
    return log_returns.rolling(window).std() * np.sqrt(annualize)


def ewma_vol(prices: pd.Series, span: int = 30, annualize: int = 252) -> pd.Series:
    """Exponentially weighted moving average volatility."""
    log_returns = np.log(prices / prices.shift(1)).dropna()
    return log_returns.ewm(span=span).std() * np.sqrt(annualize)


def garch_forecast(prices: pd.Series, horizon: int = 5) -> dict:
    """Fit GARCH(1,1) and forecast volatility for next `horizon` days."""
    try:
        from arch import arch_model
    except ImportError:
        logger.warning("arch package not installed — GARCH unavailable")
        return {"forecast": [], "params": {}, "error": "arch not installed"}

    log_returns = np.log(prices / prices.shift(1)).dropna() * 100  # in percentage

    try:
        model = arch_model(log_returns, vol="Garch", p=1, q=1, mean="AR", lags=1)
        result = model.fit(disp="off", show_warning=False)
        forecast = result.forecast(horizon=horizon)
        var_forecast = forecast.variance.iloc[-1].values
        vol_forecast = np.sqrt(var_forecast) * np.sqrt(252) / 100  # annualized decimal

        return {
            "forecast": [round(v, 4) for v in vol_forecast],
            "params": {
                "omega": round(result.params.get("omega", 0), 6),
                "alpha": round(result.params.get("alpha[1]", 0), 4),
                "beta": round(result.params.get("beta[1]", 0), 4),
                "persistence": round(result.params.get("alpha[1]", 0) + result.params.get("beta[1]", 0), 4),
            },
            "current_vol": round(float(realized_vol(prices).iloc[-1]), 4) if len(prices) > 22 else None,
            "aic": round(result.aic, 2),
            "bic": round(result.bic, 2),
        }
    except Exception as e:
        logger.error(f"GARCH fit failed: {e}")
        return {"forecast": [], "params": {}, "error": str(e)}


def vol_cone(prices: pd.Series, windows: list[int] = None) -> pd.DataFrame:
    """Volatility cone — min/max/median realized vol at different lookback windows."""
    if windows is None:
        windows = [5, 10, 21, 42, 63, 126, 252]

    records = []
    for w in windows:
        rv = realized_vol(prices, window=w).dropna()
        if rv.empty:
            continue
        records.append({
            "window": w,
            "min": round(rv.min(), 4),
            "q25": round(rv.quantile(0.25), 4),
            "median": round(rv.median(), 4),
            "q75": round(rv.quantile(0.75), 4),
            "max": round(rv.max(), 4),
            "current": round(rv.iloc[-1], 4),
        })
    return pd.DataFrame(records)


def ewma_vol_halflife(prices: pd.Series, half_life: int = 120, annualize: int = 252) -> pd.Series:
    """EWMA volatility with half-life parameterization.
    half_life = number of days for weight to decay to 50%.
    lambda = exp(-ln(2)/half_life)
    """
    lam = math.exp(-math.log(2) / half_life)
    span = 2 / (1 - lam) - 1  # convert lambda to pandas ewm span
    log_returns = np.log(prices / prices.shift(1)).dropna()
    return log_returns.ewm(span=span).std() * np.sqrt(annualize)


def parkinson_vol(ohlc_df: pd.DataFrame, window: int = 21, annualize: int = 252) -> pd.Series:
    """Parkinson volatility estimator using high-low range.
    More efficient than close-to-close for trending markets.
    Requires columns: high, low
    """
    if "high" not in ohlc_df.columns or "low" not in ohlc_df.columns:
        return pd.Series(dtype=float)
    log_hl = np.log(ohlc_df["high"] / ohlc_df["low"])
    parkinson = (log_hl ** 2) / (4 * np.log(2))
    return np.sqrt(parkinson.rolling(window).mean() * annualize)


def garman_klass_vol(ohlc_df: pd.DataFrame, window: int = 21, annualize: int = 252) -> pd.Series:
    """Garman-Klass volatility estimator using OHLC.
    Most efficient of the classic estimators.
    Requires columns: open, high, low, close
    """
    required = ["open", "high", "low", "close"]
    if not all(c in ohlc_df.columns for c in required):
        return pd.Series(dtype=float)
    log_hl = np.log(ohlc_df["high"] / ohlc_df["low"])
    log_co = np.log(ohlc_df["close"] / ohlc_df["open"])
    gk = 0.5 * log_hl**2 - (2*np.log(2)-1) * log_co**2
    return np.sqrt(gk.rolling(window).mean() * annualize)


def rogers_satchell_vol(ohlc_df: pd.DataFrame, window: int = 21, annualize: int = 252) -> pd.Series:
    """Rogers-Satchell estimator — handles drift, doesn't assume zero mean.
    Best for trending assets like gold.
    Requires columns: open, high, low, close
    """
    required = ["open", "high", "low", "close"]
    if not all(c in ohlc_df.columns for c in required):
        return pd.Series(dtype=float)
    log_ho = np.log(ohlc_df["high"] / ohlc_df["open"])
    log_lo = np.log(ohlc_df["low"] / ohlc_df["open"])
    log_co = np.log(ohlc_df["close"] / ohlc_df["open"])
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    return np.sqrt(rs.rolling(window).mean() * annualize)
