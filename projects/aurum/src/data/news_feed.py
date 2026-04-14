"""
News aggregator for metals-relevant headlines.
Sources: RSS feeds from major outlets + NewsAPI if key available.
Scores headlines by metals relevance.
"""
import re
from datetime import datetime, timedelta
import requests
import pandas as pd
from loguru import logger
from src.data import cache
from src.config import Config

try:
    import feedparser
except ImportError:
    feedparser = None

# RSS feeds — major financial news
RSS_FEEDS = [
    ("Reuters Commodities", "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Kitco Gold", "https://www.kitco.com/rss/gold.xml"),
    ("Mining.com", "https://www.mining.com/feed/"),
    ("FT Commodities", "https://www.ft.com/commodities?format=rss"),
    ("CNBC Commodities", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=48845888"),
    ("MarketWatch Metals", "https://feeds.marketwatch.com/marketwatch/StockstoWatch/"),
]

# Scoring keywords (weight: keyword)
SCORE_MAP = {
    5: ["gold price", "silver price", "bullion", "precious metals", "gold rally", "gold crash"],
    4: ["federal reserve", "interest rate", "rate cut", "rate hike", "inflation data", "cpi report"],
    3: ["central bank gold", "gold reserve", "dedollarization", "tariff", "sanctions", "trade war"],
    3: ["comex", "lbma", "mcx gold", "etf flows", "gld", "slv"],
    2: ["dollar index", "treasury yield", "real rate", "money supply", "quantitative"],
    2: ["russia", "ukraine", "china", "iran", "taiwan", "middle east", "conflict"],
    1: ["commodity", "mining", "oil price", "opec", "recession", "gdp"],
}


def _score_headline(text: str) -> int:
    """Score a headline by metals relevance."""
    text_lower = text.lower()
    score = 0
    for weight, keywords in SCORE_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                score += weight
    return score


def fetch_rss_news() -> pd.DataFrame:
    """Fetch news from RSS feeds."""
    if feedparser is None:
        logger.warning("feedparser not installed — RSS disabled")
        return pd.DataFrame()

    articles = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = entry.get("published", entry.get("updated", ""))
                link = entry.get("link", "")
                score = _score_headline(title + " " + summary)
                if score > 0:
                    articles.append({
                        "source": source_name,
                        "title": title,
                        "summary": re.sub(r"<[^>]+>", "", summary)[:300],
                        "url": link,
                        "published": published,
                        "score": score,
                    })
        except Exception as e:
            logger.warning(f"RSS fetch failed for {source_name}: {e}")

    df = pd.DataFrame(articles)
    if not df.empty:
        df = df.sort_values("score", ascending=False).drop_duplicates("title")
    return df


def fetch_newsapi(query: str = "gold OR silver OR precious metals", days: int = 3) -> pd.DataFrame:
    """Fetch from NewsAPI (requires API key)."""
    if not Config.NEWS_API_KEY:
        return pd.DataFrame()

    def _fetch():
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": 50,
                    "apiKey": Config.NEWS_API_KEY,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                return pd.DataFrame()
            data = resp.json()
            articles = []
            for a in data.get("articles", []):
                title = a.get("title", "")
                score = _score_headline(title + " " + a.get("description", ""))
                articles.append({
                    "source": a.get("source", {}).get("name", ""),
                    "title": title,
                    "summary": (a.get("description", "") or "")[:300],
                    "url": a.get("url", ""),
                    "published": a.get("publishedAt", ""),
                    "score": score,
                })
            return pd.DataFrame(articles)
        except Exception as e:
            logger.error(f"NewsAPI failed: {e}")
            return pd.DataFrame()

    return cache.cached(f"newsapi_{query[:20]}", _fetch, ttl=Config.TTL_INTRADAY)


def fetch_all_news() -> pd.DataFrame:
    """Aggregate all news sources, deduplicate, sort by score."""
    dfs = [fetch_rss_news()]
    newsapi = fetch_newsapi()
    if not newsapi.empty:
        dfs.append(newsapi)
    combined = pd.concat(dfs, ignore_index=True)
    if combined.empty:
        return combined
    combined = combined.drop_duplicates(subset="title").sort_values("score", ascending=False)
    return combined.head(100)
