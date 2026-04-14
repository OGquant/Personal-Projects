"""Key ratios: Gold/Silver, Gold/Oil, Gold/M2, Gold/DXY, Gold/Real Rate."""
import pandas as pd
import numpy as np


def compute_ratio(series_a: pd.Series, series_b: pd.Series, name: str = "ratio") -> pd.DataFrame:
    """Compute ratio of two aligned price series."""
    combined = pd.DataFrame({"a": series_a, "b": series_b}).dropna()
    combined[name] = combined["a"] / combined["b"]
    combined[f"{name}_zscore"] = (combined[name] - combined[name].rolling(252).mean()) / combined[name].rolling(252).std()
    return combined[[name, f"{name}_zscore"]]


def gold_silver_ratio(gold: pd.Series, silver: pd.Series) -> pd.DataFrame:
    return compute_ratio(gold, silver, "gold_silver_ratio")


def gold_oil_ratio(gold: pd.Series, oil: pd.Series) -> pd.DataFrame:
    return compute_ratio(gold, oil, "gold_oil_ratio")


def gold_dxy_ratio(gold: pd.Series, dxy: pd.Series) -> pd.DataFrame:
    return compute_ratio(gold, dxy, "gold_dxy_ratio")


RATIO_BENCHMARKS = {
    "gold_silver_ratio": {"mean_20y": 68, "mean_10y": 80, "extreme_low": 45, "extreme_high": 120},
    "gold_oil_ratio": {"mean_20y": 18, "mean_10y": 22, "extreme_low": 10, "extreme_high": 40},
}
