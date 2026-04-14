"""
Central bank gold reserves — top holders, quarterly changes.
Primary: IMF IFS data via World Bank API fallback.
"""
import pandas as pd
import requests
from loguru import logger
from src.data import cache
from src.config import Config

# Static top holders (updated Q4 2025, tonnes) — updated from WGC data
TOP_HOLDERS = [
    ("United States", 8133.5, 67.8), ("Germany", 3352.3, 70.0),
    ("Italy", 2451.8, 66.7), ("France", 2436.9, 66.0),
    ("Russia", 2326.5, 29.5), ("China", 2306.0, 8.9),
    ("Switzerland", 1040.0, 7.3), ("Japan", 846.0, 5.3),
    ("India", 876.2, 10.6), ("Netherlands", 612.5, 59.5),
    ("Turkey", 644.0, 34.2), ("ECB", 506.5, 30.8),
    ("Taiwan", 423.6, 4.5), ("Poland", 448.8, 18.2),
    ("Uzbekistan", 382.0, 75.0), ("Saudi Arabia", 323.1, 5.2),
    ("UK", 310.3, 12.2), ("Kazakhstan", 312.0, 62.0),
    ("Portugal", 382.6, 72.4), ("Czech Republic", 72.0, 5.8),
]

# 2025 top buyers (tonnes, approximate)
TOP_BUYERS_2025 = [
    ("Poland", 89), ("China", 27), ("Turkey", 27), ("India", 25),
    ("Czech Republic", 20), ("Qatar", 15), ("Hungary", 12),
]


def fetch_reserves() -> pd.DataFrame:
    """Return current gold reserves by country."""
    def _fetch():
        df = pd.DataFrame(TOP_HOLDERS, columns=["country", "tonnes", "pct_of_reserves"])
        df = df.sort_values("tonnes", ascending=False)
        df["value_usd_bn"] = round(df["tonnes"] * 32150.75 * 3300 / 1e9, 1)  # approx at $3300/oz
        return df
    return cache.cached("cb_reserves", _fetch, ttl=Config.TTL_QUARTERLY)


def fetch_buying_pace() -> pd.DataFrame:
    """Return recent central bank buying activity."""
    def _fetch():
        df = pd.DataFrame(TOP_BUYERS_2025, columns=["country", "tonnes_2025"])
        df = df.sort_values("tonnes_2025", ascending=False)
        return df
    return cache.cached("cb_buying", _fetch, ttl=Config.TTL_QUARTERLY)


def fetch_annual_demand() -> pd.DataFrame:
    """Historical annual central bank net purchases."""
    data = [
        (2015, 566), (2016, 383), (2017, 375), (2018, 656), (2019, 650),
        (2020, 273), (2021, 463), (2022, 1082), (2023, 1037), (2024, 1045), (2025, 863),
    ]
    return pd.DataFrame(data, columns=["year", "net_purchases_tonnes"])
