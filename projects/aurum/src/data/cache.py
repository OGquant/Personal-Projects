"""
File-based cache with TTL support.
Stores DataFrames as parquet, other objects as JSON.
"""
import json
import time
import hashlib
from pathlib import Path
from typing import Any
import pandas as pd
from src.config import Config
from loguru import logger


def _cache_path(key: str) -> Path:
    safe = hashlib.md5(key.encode()).hexdigest()
    return Config.CACHE_DIR / f"{safe}"


def _meta_path(key: str) -> Path:
    return Path(str(_cache_path(key)) + ".meta.json")


def get(key: str) -> pd.DataFrame | dict | None:
    """Retrieve cached item if not expired."""
    meta_file = _meta_path(key)
    if not meta_file.exists():
        return None

    with open(meta_file) as f:
        meta = json.load(f)

    if time.time() > meta["expires_at"]:
        logger.debug(f"Cache expired: {key}")
        return None

    data_file = _cache_path(key)
    fmt = meta.get("format", "json")

    if fmt == "parquet" and Path(str(data_file) + ".parquet").exists():
        return pd.read_parquet(str(data_file) + ".parquet")
    elif Path(str(data_file) + ".json").exists():
        with open(str(data_file) + ".json") as f:
            return json.load(f)
    return None


def set(key: str, data: Any, ttl: int = Config.TTL_DAILY) -> None:
    """Store item with TTL."""
    meta_file = _meta_path(key)
    data_file = _cache_path(key)

    meta = {"key": key, "expires_at": time.time() + ttl, "created_at": time.time()}

    if isinstance(data, pd.DataFrame):
        meta["format"] = "parquet"
        data.to_parquet(str(data_file) + ".parquet")
    else:
        meta["format"] = "json"
        with open(str(data_file) + ".json", "w") as f:
            json.dump(data, f, default=str)

    with open(meta_file, "w") as f:
        json.dump(meta, f)

    logger.debug(f"Cached: {key} (TTL={ttl}s)")


def cached(key: str, fetcher, ttl: int = Config.TTL_DAILY):
    """Decorator-style: return cached or fetch and cache."""
    result = get(key)
    if result is not None:
        logger.debug(f"Cache hit: {key}")
        return result
    logger.info(f"Cache miss: {key} — fetching...")
    result = fetcher()
    if result is not None:
        set(key, result, ttl)
    return result


def clear_all() -> int:
    """Remove all cached files. Returns count removed."""
    count = 0
    for f in Config.CACHE_DIR.glob("*"):
        f.unlink()
        count += 1
    return count
