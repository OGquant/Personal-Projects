"""
Polymarket API client.
Fetches prediction markets relevant to metals: war, Fed, tariffs, dedollarization.
Uses the Gamma events API — no auth needed for read-only.
Pattern matches the working template from research/Explore_Gemini_Capabilities.
"""
import json
import urllib.request
import urllib.parse
import pandas as pd
from loguru import logger
from src.data import cache
from src.config import Config

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Keywords that influence metals prices
METALS_KEYWORDS = [
    "war", "russia", "ukraine", "china", "taiwan", "iran", "israel",
    "fed", "federal reserve", "interest rate", "inflation", "cpi",
    "tariff", "sanctions", "trade war", "dollar", "dedollarization",
    "gold", "silver", "commodity", "oil", "opec",
    "recession", "default", "debt ceiling", "nato",
    "brics", "yuan", "petrodollar", "central bank",
    "trump", "election", "nuclear", "military",
]


def _fetch_url(url: str) -> dict | list | None:
    """Fetch JSON from URL with proper User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"HTTP fetch failed {url}: {e}")
        return None


def fetch_active_markets(limit: int = 100) -> pd.DataFrame:
    """Fetch active Polymarket events filtered for metals-relevant topics."""
    def _fetch():
        try:
            all_events = []
            offset = 0
            batch_size = 100

            while len(all_events) < limit * 3:  # fetch enough to filter
                url = f"{GAMMA_API}/events?limit={batch_size}&offset={offset}&active=true&closed=false"
                data = _fetch_url(url)
                if not data or not isinstance(data, list):
                    break
                all_events.extend(data)
                offset += batch_size
                if len(data) < batch_size:
                    break

            relevant = []
            for event in all_events:
                title = event.get("title", "")
                description = event.get("description", "")
                text = (title + " " + description).lower()

                matched_keywords = [kw for kw in METALS_KEYWORDS if kw in text]
                if not matched_keywords:
                    continue

                # Pull market data from embedded markets list
                markets = event.get("markets", [])
                for market in markets:
                    if not market.get("active") or market.get("closed"):
                        continue

                    # Parse outcome prices
                    outcome_prices = market.get("outcomePrices", [])
                    if isinstance(outcome_prices, str):
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except Exception:
                            outcome_prices = []

                    # Best outcome probability (first = yes probability)
                    best_price = float(outcome_prices[0]) if outcome_prices else 0.0

                    volume = float(market.get("volume", 0) or 0)
                    liquidity = float(market.get("liquidity", 0) or 0)

                    relevant.append({
                        "question": market.get("question", title),
                        "event_title": title,
                        "slug": event.get("slug", ""),
                        "token_id": market.get("clob_token_ids", [""])[0] if market.get("clob_token_ids") else "",
                        "probability": round(best_price * 100, 1),
                        "volume": volume,
                        "liquidity": liquidity,
                        "end_date": event.get("endDate", "")[:10] if event.get("endDate") else "",
                        "keywords": ", ".join(matched_keywords[:3]),
                        "category": _categorize(matched_keywords),
                        "url": f"https://polymarket.com/event/{event.get('slug', '')}",
                    })

            df = pd.DataFrame(relevant)
            if not df.empty:
                df = df.sort_values("volume", ascending=False).drop_duplicates("question").head(limit)
            logger.info(f"Polymarket: fetched {len(df)} relevant markets from {len(all_events)} events")
            return df

        except Exception as e:
            logger.error(f"Polymarket fetch failed: {e}")
            return pd.DataFrame()

    return cache.cached("polymarket_active_v2", _fetch, ttl=Config.TTL_INTRADAY)


def fetch_price_history(token_id: str) -> list[dict]:
    """Fetch CLOB price history for a market token (for sparklines)."""
    if not token_id:
        return []
    try:
        url = f"{CLOB_API}/prices-history?market={token_id}&interval=max&fidelity=1440"
        data = _fetch_url(url)
        return data.get("history", []) if data else []
    except Exception as e:
        logger.error(f"CLOB history fetch failed: {e}")
        return []


def _categorize(keywords: list[str]) -> str:
    """Assign a category based on matched keywords."""
    geo = {"war", "russia", "ukraine", "china", "taiwan", "iran", "israel", "nato", "nuclear", "military"}
    macro = {"fed", "federal reserve", "interest rate", "inflation", "cpi", "recession", "debt ceiling"}
    trade = {"tariff", "sanctions", "trade war", "dollar", "dedollarization", "brics", "yuan", "petrodollar", "central bank"}
    commodity = {"gold", "silver", "oil", "opec", "commodity"}

    kw_set = set(keywords)
    if kw_set & commodity:
        return "🟡 Commodity"
    if kw_set & geo:
        return "🔴 Geopolitical"
    if kw_set & macro:
        return "🔵 Macro/Fed"
    if kw_set & trade:
        return "🟠 Trade/FX"
    return "⚪ Other"
