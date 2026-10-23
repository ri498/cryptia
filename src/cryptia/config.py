from pathlib import Path
from typing import Dict, Any

# Root project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = DATA_DIR / "models"
STATIC_DIR = BASE_DIR / "src" / "static"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Supported Cryptocurrencies
SUPPORTED_CRYPTOS: Dict[str, Dict[str, Any]] = {
    "BTC": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "pair": "BTCUSDT",
        "coingecko_id": "bitcoin",
        "color": "#F7931A",
        "gradient": "from-amber-500 to-orange-600",
        "icon": "₿",
    },
    "ETH": {
        "name": "Ethereum",
        "symbol": "ETH",
        "pair": "ETHUSDT",
        "coingecko_id": "ethereum",
        "color": "#627EEA",
        "gradient": "from-blue-500 to-indigo-600",
        "icon": "Ξ",
    },
    "SOL": {
        "name": "Solana",
        "symbol": "SOL",
        "pair": "SOLUSDT",
        "coingecko_id": "solana",
        "color": "#14F195",
        "gradient": "from-emerald-400 to-purple-600",
        "icon": "◎",
    },
}

DEFAULT_CRYPTO = "BTC"
DEFAULT_HORIZON_DAYS = 7
MAX_HORIZON_DAYS = 30
MIN_HORIZON_DAYS = 1
