"""
Zerodha Kite Connect data provider for AURUM.

Provides live MCX quotes, option chains, and WebSocket tick streaming.
Falls back gracefully to yfinance/static data when credentials are not configured.

Setup:
  1. Get API key from https://developers.kite.trade/
  2. Generate access token via Kite login (valid for one trading day)
  3. Set in .env:
       KITE_API_KEY=your_api_key
       KITE_ACCESS_TOKEN=your_access_token

MCX Instrument tokens (stable, rarely change):
  Gold  (GOLD26APRFUT): fetch fresh each session via instruments()
  Silver (SILVER26MAYFUT): same
"""
import threading
from typing import Callable
from datetime import datetime, date, timedelta
import pandas as pd
from loguru import logger
from src.config import Config

# ── Availability check ──────────────────────────────────────────────────────

def is_configured() -> bool:
    """True when both Kite credentials are present in env."""
    return bool(Config.KITE_API_KEY and Config.KITE_ACCESS_TOKEN)


def _get_kite():
    """Return an authenticated KiteConnect instance, or None."""
    if not is_configured():
        return None
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=Config.KITE_API_KEY)
        kite.set_access_token(Config.KITE_ACCESS_TOKEN)
        return kite
    except ImportError:
        logger.warning("kiteconnect not installed — run: pip install kiteconnect")
        return None
    except Exception as e:
        logger.error(f"Kite init failed: {e}")
        return None


# ── Instrument lookup ────────────────────────────────────────────────────────

# MCX symbol prefixes for metals
MCX_SYMBOLS = {
    "Gold": "GOLD",
    "Gold Mini": "GOLDM",
    "Gold Petal": "GOLDPETAL",
    "Silver": "SILVER",
    "Silver Mini": "SILVERM",
    "Silver Micro": "SILVERMIC",
}

_instruments_cache: dict[str, list] = {}  # exchange → instrument list
_token_map: dict[str, int] = {}           # "SYMBOL_EXPIRY" → instrument_token


def _load_instruments(kite, exchange: str = "MCX") -> list:
    """Load and cache instrument list for an exchange."""
    if exchange in _instruments_cache:
        return _instruments_cache[exchange]
    try:
        instruments = kite.instruments(exchange=exchange)
        _instruments_cache[exchange] = instruments
        logger.info(f"Loaded {len(instruments)} {exchange} instruments")
        return instruments
    except Exception as e:
        logger.error(f"Instruments load failed for {exchange}: {e}")
        return []


def get_front_month_token(kite, symbol: str) -> int | None:
    """
    Find the nearest-expiry futures contract token for a symbol.
    e.g. symbol="GOLD" → returns token for GOLD25APRFUT or closest expiry.
    """
    instruments = _load_instruments(kite, "MCX")
    today = date.today()

    candidates = [
        i for i in instruments
        if i["tradingsymbol"].startswith(symbol)
        and i["instrument_type"] == "FUT"
        and i["expiry"] >= today
    ]
    if not candidates:
        return None

    # Sort by expiry ascending — nearest front month first
    candidates.sort(key=lambda x: x["expiry"])
    front = candidates[0]
    token = front["instrument_token"]
    logger.debug(f"Front month for {symbol}: {front['tradingsymbol']} token={token}")
    return token


def get_option_tokens(kite, symbol: str, expiry_date: date | None = None) -> list[dict]:
    """
    Get all option contracts for a symbol on a given expiry.
    If expiry_date is None, returns nearest expiry options.
    Returns list of dicts: {tradingsymbol, strike, instrument_type, expiry, token}
    """
    instruments = _load_instruments(kite, "MCX")
    today = date.today()

    options = [
        i for i in instruments
        if i["tradingsymbol"].startswith(symbol)
        and i["instrument_type"] in ("CE", "PE")
        and i["expiry"] >= today
    ]
    if not options:
        return []

    # Pick nearest expiry if not specified
    if expiry_date is None:
        expiry_date = min(i["expiry"] for i in options)

    filtered = [i for i in options if i["expiry"] == expiry_date]
    return [
        {
            "tradingsymbol": i["tradingsymbol"],
            "strike": float(i["strike"]),
            "type": i["instrument_type"],   # CE or PE
            "expiry": i["expiry"],
            "token": i["instrument_token"],
        }
        for i in sorted(filtered, key=lambda x: (x["strike"], x["instrument_type"]))
    ]


# ── Live Quotes ──────────────────────────────────────────────────────────────

def fetch_mcx_quotes(symbols: list[str] | None = None) -> pd.DataFrame:
    """
    Fetch live MCX quotes for metals futures.
    Returns DataFrame with: symbol, ltp, change, change_pct, volume, oi, bid, ask, high, low
    Falls back to empty DataFrame if Kite not configured.
    """
    if not is_configured():
        logger.debug("Kite not configured — skipping MCX live quotes")
        return pd.DataFrame()

    kite = _get_kite()
    if kite is None:
        return pd.DataFrame()

    if symbols is None:
        symbols = list(MCX_SYMBOLS.values())

    # Build token list for all front-month contracts
    tokens = []
    token_to_name = {}
    for name, sym in MCX_SYMBOLS.items():
        if sym not in symbols and name not in symbols:
            continue
        token = get_front_month_token(kite, sym)
        if token:
            tokens.append(token)
            token_to_name[token] = name

    if not tokens:
        return pd.DataFrame()

    try:
        quotes = kite.quote([f"MCX:{t}" for t in tokens])
        records = []
        for token in tokens:
            key = f"MCX:{token}"
            q = quotes.get(key, {})
            if not q:
                continue
            ohlc = q.get("ohlc", {})
            depth = q.get("depth", {})
            best_bid = depth.get("buy", [{}])[0].get("price", 0) if depth.get("buy") else 0
            best_ask = depth.get("sell", [{}])[0].get("price", 0) if depth.get("sell") else 0
            ltp = q.get("last_price", 0)
            prev_close = ohlc.get("close", ltp)
            change = ltp - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            records.append({
                "symbol": token_to_name.get(token, str(token)),
                "ltp": round(ltp, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 3),
                "volume": q.get("volume", 0),
                "oi": q.get("oi", 0),
                "bid": round(best_bid, 2),
                "ask": round(best_ask, 2),
                "high": round(ohlc.get("high", ltp), 2),
                "low": round(ohlc.get("low", ltp), 2),
                "open": round(ohlc.get("open", ltp), 2),
                "timestamp": q.get("timestamp"),
            })
        return pd.DataFrame(records)
    except Exception as e:
        logger.error(f"Kite quote fetch failed: {e}")
        return pd.DataFrame()


# ── Option Chain ─────────────────────────────────────────────────────────────

def fetch_option_chain(symbol: str = "GOLD", expiry_date: date | None = None) -> pd.DataFrame:
    """
    Fetch live MCX option chain for a symbol.
    Returns DataFrame with full chain: strike, CE ltp/oi/iv, PE ltp/oi/iv.
    Falls back to empty DataFrame if Kite not configured.
    """
    if not is_configured():
        logger.debug("Kite not configured — skipping option chain fetch")
        return pd.DataFrame()

    kite = _get_kite()
    if kite is None:
        return pd.DataFrame()

    options = get_option_tokens(kite, symbol, expiry_date)
    if not options:
        return pd.DataFrame()

    tokens = [o["token"] for o in options]
    try:
        quotes = kite.quote([f"MCX:{t}" for t in tokens])
    except Exception as e:
        logger.error(f"Option chain quote failed: {e}")
        return pd.DataFrame()

    # Pivot into chain format: one row per strike
    chain: dict[float, dict] = {}
    for opt in options:
        token = opt["token"]
        key = f"MCX:{token}"
        q = quotes.get(key, {})
        strike = opt["strike"]
        opt_type = opt["type"]  # CE or PE
        ltp = q.get("last_price", 0)
        oi = q.get("oi", 0)
        volume = q.get("volume", 0)

        if strike not in chain:
            chain[strike] = {"strike": strike, "expiry": opt["expiry"]}

        prefix = "ce" if opt_type == "CE" else "pe"
        chain[strike][f"{prefix}_ltp"] = round(ltp, 2)
        chain[strike][f"{prefix}_oi"] = oi
        chain[strike][f"{prefix}_volume"] = volume
        chain[strike][f"{prefix}_symbol"] = opt["tradingsymbol"]

    df = pd.DataFrame(list(chain.values())).sort_values("strike")
    logger.info(f"Option chain fetched: {symbol} {expiry_date} — {len(df)} strikes")
    return df


# ── Intraday OHLCV ───────────────────────────────────────────────────────────

def fetch_intraday(
    symbol: str = "GOLD",
    interval: str = "5minute",
    days_back: int = 5,
) -> pd.DataFrame:
    """
    Fetch intraday OHLCV from Kite Historical Data API.

    interval options: minute, 3minute, 5minute, 10minute, 15minute, 30minute, 60minute, day

    Returns DataFrame with: date, open, high, low, close, volume
    Falls back to yfinance 5-minute data if Kite not configured.
    """
    if not is_configured():
        logger.debug("Kite not configured — falling back to yfinance intraday")
        return _yfinance_intraday_fallback(symbol, interval, days_back)

    kite = _get_kite()
    if kite is None:
        return _yfinance_intraday_fallback(symbol, interval, days_back)

    token = get_front_month_token(kite, MCX_SYMBOLS.get(symbol, symbol))
    if not token:
        return pd.DataFrame()

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)

    try:
        data = kite.historical_data(
            instrument_token=token,
            from_date=from_date.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=to_date.strftime("%Y-%m-%d %H:%M:%S"),
            interval=interval,
        )
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date": "datetime"})
        logger.info(f"Intraday {symbol} {interval}: {len(df)} bars")
        return df
    except Exception as e:
        logger.error(f"Kite historical_data failed for {symbol}: {e}")
        return pd.DataFrame()


def _yfinance_intraday_fallback(symbol: str, interval: str, days_back: int) -> pd.DataFrame:
    """Fallback to yfinance for intraday data when Kite is not available."""
    import yfinance as yf
    from src.data.spot_prices import TICKERS
    ticker_map = {"GOLD": "GC=F", "SILVER": "SI=F"}
    ticker = ticker_map.get(symbol) or TICKERS.get(symbol, "GC=F")

    # Map Kite intervals to yfinance
    interval_map = {
        "minute": "1m", "3minute": "5m", "5minute": "5m",
        "10minute": "15m", "15minute": "15m", "30minute": "30m",
        "60minute": "60m", "day": "1d",
    }
    yf_interval = interval_map.get(interval, "5m")
    period = f"{min(days_back, 5)}d" if "m" in yf_interval else f"{days_back}d"

    try:
        df = yf.download(ticker, period=period, interval=yf_interval, progress=False)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
        df.index.name = "datetime"
        return df.reset_index()
    except Exception as e:
        logger.warning(f"yfinance intraday fallback failed: {e}")
        return pd.DataFrame()


# ── WebSocket Tick Stream ─────────────────────────────────────────────────────

class KiteTicker:
    """
    Thin wrapper around KiteTicker WebSocket for live MCX price streaming.
    Usage:
        ticker = KiteTicker()
        ticker.on_tick(my_callback)   # callback(ticks: list[dict])
        ticker.start(["GOLD", "SILVER"])
        ...
        ticker.stop()

    When Kite is not configured, start() is a no-op and on_tick callbacks
    are never called. The calling UI should fall back to polling fetch_mcx_quotes().
    """

    def __init__(self):
        self._ticker = None
        self._callbacks: list[Callable] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def on_tick(self, callback: Callable[[list[dict]], None]) -> None:
        """Register a callback to receive tick updates."""
        self._callbacks.append(callback)

    def start(self, symbols: list[str] | None = None) -> bool:
        """
        Start the WebSocket stream. Returns True if started, False if Kite not configured.
        symbols: list of MCX symbol names e.g. ["GOLD", "SILVER"]
        """
        if not is_configured():
            logger.info("KiteTicker: Kite not configured — streaming disabled")
            return False

        try:
            from kiteconnect import KiteTicker as _KT
        except ImportError:
            logger.warning("kiteconnect not installed — WebSocket streaming unavailable")
            return False

        kite = _get_kite()
        if kite is None:
            return False

        # Resolve tokens
        if symbols is None:
            symbols = ["GOLD", "SILVER"]

        tokens = []
        for sym in symbols:
            mcx_sym = MCX_SYMBOLS.get(sym, sym)
            token = get_front_month_token(kite, mcx_sym)
            if token:
                tokens.append(token)

        if not tokens:
            logger.warning("KiteTicker: no valid tokens found")
            return False

        self._ticker = _KT(api_key=Config.KITE_API_KEY, access_token=Config.KITE_ACCESS_TOKEN)

        def _on_ticks(ws, ticks):
            for cb in self._callbacks:
                try:
                    cb(ticks)
                except Exception as e:
                    logger.warning(f"Tick callback error: {e}")

        def _on_connect(ws, response):
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)
            logger.info(f"KiteTicker connected, subscribed to {tokens}")

        def _on_error(ws, code, reason):
            logger.error(f"KiteTicker error {code}: {reason}")

        def _on_close(ws, code, reason):
            logger.info(f"KiteTicker closed {code}: {reason}")
            self._running = False

        self._ticker.on_ticks = _on_ticks
        self._ticker.on_connect = _on_connect
        self._ticker.on_error = _on_error
        self._ticker.on_close = _on_close

        self._running = True
        self._thread = threading.Thread(
            target=lambda: self._ticker.connect(threaded=False),
            daemon=True,
        )
        self._thread.start()
        logger.info("KiteTicker WebSocket thread started")
        return True

    def stop(self) -> None:
        """Stop the WebSocket stream."""
        if self._ticker:
            try:
                self._ticker.close()
            except Exception:
                pass
        self._running = False
        logger.info("KiteTicker stopped")

    @property
    def is_running(self) -> bool:
        return self._running


# ── Realized Vol from Ticks ──────────────────────────────────────────────────

def compute_intraday_rv(symbol: str = "GOLD", interval: str = "5minute", days_back: int = 5) -> dict:
    """
    Compute realized volatility from intraday bars.
    Returns dict with rv_5min, rv_annualized, n_bars, source.
    Source is 'kite' if connected, 'yfinance' otherwise.
    """
    import numpy as np

    df = fetch_intraday(symbol, interval, days_back)
    if df.empty or "close" not in df.columns:
        return {"rv_5min": None, "rv_annualized": None, "n_bars": 0, "source": "unavailable"}

    close = df["close"].dropna()
    log_returns = np.log(close / close.shift(1)).dropna()

    # Per-bar vol (not annualized)
    rv_bar = log_returns.std()

    # Annualize: MCX Gold trades ~7.5 hours/day = 90 five-minute bars/day
    # 252 trading days → 252 * 90 = 22,680 bars/year
    bars_per_day = {"minute": 450, "3minute": 150, "5minute": 90,
                    "10minute": 45, "15minute": 30, "30minute": 15,
                    "60minute": 7, "day": 1}.get(interval, 90)
    annualization = (bars_per_day * 252) ** 0.5
    rv_annualized = rv_bar * annualization

    source = "kite" if is_configured() else "yfinance"
    return {
        "rv_5min": round(float(rv_bar), 6),
        "rv_annualized": round(float(rv_annualized), 4),
        "n_bars": len(log_returns),
        "source": source,
        "interval": interval,
    }
