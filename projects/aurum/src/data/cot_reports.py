"""
CFTC Commitments of Traders (COT) report parser.
Downloads and parses managed money positions for Gold and Silver.
"""
import io
import zipfile
import pandas as pd
import requests
from loguru import logger
from src.data import cache
from src.config import Config

# CFTC COT URLs
COT_FUTURES_URL = "https://www.cftc.gov/dea/newcot/deafulong.txt"
COT_COMBINED_URL = "https://www.cftc.gov/dea/newcot/deacomlong.txt"
COT_HISTORY_URL = "https://www.cftc.gov/files/dea/history/deacot2024.zip"

# CFTC codes for metals
COMMODITY_CODES = {
    "GOLD": "088691",
    "SILVER": "084691",
    "COPPER": "085692",
    "PLATINUM": "076651",
    "PALLADIUM": "075651",
    "CRUDE OIL": "067651",
}


def fetch_cot_current() -> pd.DataFrame:
    """Fetch the latest COT report and parse Gold/Silver positions."""
    def _fetch():
        try:
            resp = requests.get(COT_FUTURES_URL, timeout=30)
            if resp.status_code != 200:
                logger.error(f"COT download failed: {resp.status_code}")
                return pd.DataFrame()
            df = pd.read_csv(io.StringIO(resp.text))
            # Filter for metals
            metals = df[df["CFTC_Contract_Market_Code"].isin(COMMODITY_CODES.values())].copy()
            if metals.empty:
                # Try name-based filter
                metals = df[df["Market_and_Exchange_Names"].str.contains("GOLD|SILVER", case=False, na=False)].copy()
            if metals.empty:
                return pd.DataFrame()
            result = []
            for _, row in metals.iterrows():
                name = row.get("Market_and_Exchange_Names", "Unknown")
                result.append({
                    "commodity": "Gold" if "GOLD" in name.upper() else "Silver" if "SILVER" in name.upper() else name,
                    "report_date": row.get("As_of_Date_In_Form_YYMMDD", ""),
                    "oi_total": row.get("Open_Interest_All", 0),
                    "mm_long": row.get("M_Money_Positions_Long_All", 0),
                    "mm_short": row.get("M_Money_Positions_Short_All", 0),
                    "mm_spread": row.get("M_Money_Positions_Spread_All", 0),
                    "prod_long": row.get("Prod_Merc_Positions_Long_All", 0),
                    "prod_short": row.get("Prod_Merc_Positions_Short_All", 0),
                    "swap_long": row.get("Swap_Positions_Long_All", 0),
                    "swap_short": row.get("Swap__Positions_Short_All", row.get("Swap_Positions_Short_All", 0)),
                })
            df_out = pd.DataFrame(result)
            df_out["mm_net"] = df_out["mm_long"] - df_out["mm_short"]
            return df_out
        except Exception as e:
            logger.error(f"COT parse failed: {e}")
            return pd.DataFrame()

    return cache.cached("cot_current", _fetch, ttl=Config.TTL_WEEKLY)


def fetch_cot_history(commodity: str = "GOLD", years: int = 3) -> pd.DataFrame:
    """Fetch historical COT data for a commodity (simplified)."""
    def _fetch():
        # Use the disaggregated format from CFTC archives
        records = []
        for year in range(2024 - years + 1, 2027):
            url = f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
            try:
                resp = requests.get(url, timeout=60)
                if resp.status_code != 200:
                    continue
                z = zipfile.ZipFile(io.BytesIO(resp.content))
                for fname in z.namelist():
                    with z.open(fname) as f:
                        df = pd.read_csv(f, low_memory=False)
                        mask = df["Market_and_Exchange_Names"].str.contains(commodity, case=False, na=False)
                        filtered = df[mask]
                        for _, row in filtered.iterrows():
                            records.append({
                                "date": pd.to_datetime(str(row.get("Report_Date_as_YYYY-MM-DD", "")), errors="coerce"),
                                "oi": row.get("Open_Interest_All", 0),
                                "mm_long": row.get("M_Money_Positions_Long_All", 0),
                                "mm_short": row.get("M_Money_Positions_Short_All", 0),
                                "mm_net": row.get("M_Money_Positions_Long_All", 0) - row.get("M_Money_Positions_Short_All", 0),
                            })
            except Exception as e:
                logger.warning(f"COT history {year} failed: {e}")
        return pd.DataFrame(records).sort_values("date") if records else pd.DataFrame()

    return cache.cached(f"cot_history_{commodity}_{years}y", _fetch, ttl=Config.TTL_WEEKLY)
