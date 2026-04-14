"""Seasonality analysis: monthly/weekly patterns over historical data."""
import pandas as pd
import numpy as np


def monthly_seasonality(prices: pd.DataFrame, years: int = 10) -> pd.DataFrame:
    """Average monthly returns over last N years."""
    df = prices.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    col = "close" if "close" in df.columns else df.columns[0]
    df = df[[col]].dropna().tail(252 * years)
    df["return"] = df[col].pct_change()
    df["month"] = df.index.month
    monthly = df.groupby("month")["return"].agg(["mean", "std", "median", "count"])
    monthly.columns = ["avg_return", "std", "median_return", "count"]
    monthly["avg_return_pct"] = (monthly["avg_return"] * 100).round(2)
    monthly["win_rate"] = df.groupby("month")["return"].apply(lambda x: (x > 0).mean()).round(2) * 100
    monthly.index = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return monthly


def weekly_pattern(prices: pd.DataFrame, years: int = 5) -> pd.DataFrame:
    """Average return by day of week."""
    df = prices.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    col = "close" if "close" in df.columns else df.columns[0]
    df = df[[col]].dropna().tail(252 * years)
    df["return"] = df[col].pct_change()
    df["dow"] = df.index.dayofweek
    weekly = df.groupby("dow")["return"].agg(["mean", "std", "count"])
    weekly.columns = ["avg_return", "std", "count"]
    weekly["avg_return_pct"] = (weekly["avg_return"] * 100).round(3)
    weekly.index = ["Mon", "Tue", "Wed", "Thu", "Fri"][:len(weekly)]
    return weekly


def monthly_heatmap(prices: pd.DataFrame, years: int = 10) -> pd.DataFrame:
    """Year × Month return heatmap."""
    df = prices.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    col = "close" if "close" in df.columns else df.columns[0]
    df = df[[col]].dropna().tail(252 * years)
    monthly = df[col].resample("ME").last().pct_change().dropna()
    heatmap = pd.DataFrame({"year": monthly.index.year, "month": monthly.index.month, "return": monthly.values})
    return heatmap.pivot(index="year", columns="month", values="return")
