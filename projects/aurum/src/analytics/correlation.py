"""Rolling cross-asset correlation matrix."""
import pandas as pd
import numpy as np


def rolling_correlation(prices_dict: dict[str, pd.Series], window: int = 60) -> pd.DataFrame:
    """Compute rolling correlation matrix from dict of price series."""
    df = pd.DataFrame(prices_dict).dropna()
    returns = np.log(df / df.shift(1)).dropna()
    return returns.rolling(window).corr().dropna()


def current_correlation(prices_dict: dict[str, pd.Series], window: int = 60) -> pd.DataFrame:
    """Current correlation matrix snapshot."""
    df = pd.DataFrame(prices_dict).dropna()
    returns = np.log(df / df.shift(1)).dropna()
    return returns.tail(window).corr()


def correlation_vs_time(prices_dict: dict[str, pd.Series], asset1: str, asset2: str,
                        windows: list[int] = None) -> pd.DataFrame:
    """Correlation between two assets at different lookback windows."""
    if windows is None:
        windows = [30, 60, 90, 180, 252]
    df = pd.DataFrame(prices_dict).dropna()
    returns = np.log(df / df.shift(1)).dropna()
    records = []
    for w in windows:
        if len(returns) < w:
            continue
        corr = returns[[asset1, asset2]].tail(w).corr().iloc[0, 1]
        records.append({"window": w, "correlation": round(corr, 4)})
    return pd.DataFrame(records)
