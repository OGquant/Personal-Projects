"""
Configuration loader for AURUM Metals Terminal.
Loads API keys from .env, settings from YAML, provides defaults.

Priority: Streamlit secrets (Cloud) → .env file (local) → environment variables
"""
from pathlib import Path
from dotenv import load_dotenv
import os
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _ROOT.parent / "config"

# Load .env from workspace config or project root (local dev)
for env_path in [_CONFIG_DIR / ".env", _ROOT / ".env", _ROOT.parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break


def _get_secret(key: str, default: str = "") -> str:
    """Read a secret from Streamlit Cloud secrets first, then env vars."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


class Config:
    """Central configuration access."""

    # API Keys — reads from st.secrets on Streamlit Cloud, .env locally
    FRED_API_KEY: str = _get_secret("FRED_API_KEY")
    NEWS_API_KEY: str = _get_secret("NEWS_API_KEY")
    POLYMARKET_API_KEY: str = _get_secret("POLYMARKET_API_KEY")
    KITE_API_KEY: str = _get_secret("KITE_API_KEY")
    KITE_ACCESS_TOKEN: str = _get_secret("KITE_ACCESS_TOKEN")

    # Paths
    PROJECT_ROOT: Path = _ROOT
    CACHE_DIR: Path = _ROOT / ".cache"
    LOG_DIR: Path = _ROOT / "logs"
    DATA_DIR: Path = _ROOT / "data"

    # Defaults
    TIMEZONE: str = "Asia/Kolkata"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Cache TTLs (seconds)
    TTL_REALTIME: int = 60           # 1 min
    TTL_INTRADAY: int = 900          # 15 min
    TTL_DAILY: int = 86400           # 1 day
    TTL_WEEKLY: int = 604800         # 1 week
    TTL_QUARTERLY: int = 7776000     # 90 days

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)


Config.ensure_dirs()
