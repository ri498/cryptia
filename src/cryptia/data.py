import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import httpx
import numpy as np
import pandas as pd

from cryptia.config import SUPPORTED_CRYPTOS, CACHE_DIR

logger = logging.getLogger(__name__)

async def fetch_crypto_history(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch daily historical OHLCV data for a given cryptocurrency symbol.
    Attempts public Binance API first, with fallback to local cache or realistic seed data.
    """
    symbol = symbol.upper()
    if symbol not in SUPPORTED_CRYPTOS:
        raise ValueError(f"Unsupported crypto symbol: {symbol}. Choose from {list(SUPPORTED_CRYPTOS.keys())}")

    crypto_info = SUPPORTED_CRYPTOS[symbol]
    pair = crypto_info["pair"]
    cache_file = CACHE_DIR / f"{symbol}_history.json"

    # Try fetching from Binance Public API
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1d&limit={min(days, 1000)}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                raw_data = resp.json()
                if raw_data and isinstance(raw_data, list):
                    df = _parse_binance_klines(raw_data)
                    # Cache to disk
                    _save_to_cache(cache_file, df)
                    logger.info("Successfully fetched %d records for %s from Binance API", len(df), symbol)
                    return df
            else:
                logger.warning("Binance API returned status %d for %s", resp.status_code, symbol)
    except Exception as exc:
        logger.warning("Failed to fetch data from Binance API for %s: %s", symbol, exc)

    # Fallback to local cache
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            logger.info("Loaded %d records for %s from cache", len(df), symbol)
            return df
        except Exception as exc:
            logger.error("Error reading cache for %s: %s", symbol, exc)

    # Fallback to realistic synthetic history if completely offline/first run
    logger.info("Generating realistic fallback historical data for %s", symbol)
    df = _generate_fallback_history(symbol, days=days)
    _save_to_cache(cache_file, df)
    return df


def _parse_binance_klines(klines: List[List[Any]]) -> pd.DataFrame:
    """
    Parse Binance klines format:
    [
      0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume,
      6: Close time, 7: Quote asset volume, 8: Number of trades, ...
    ]
    """
    rows = []
    for k in klines:
        ts = int(k[0])
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append({
            "timestamp": ts,
            "date": dt,
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _save_to_cache(file_path, df: pd.DataFrame) -> None:
    """Save dataframe to JSON cache file."""
    cache_df = df.copy()
    cache_df["date"] = cache_df["date"].dt.strftime("%Y-%m-%d")
    with open(file_path, "w") as f:
        json.dump(cache_df.to_dict(orient="records"), f, indent=2)


def _generate_fallback_history(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Generate realistic random-walk time-series for offline development or testing.
    """
    base_prices = {"BTC": 82000.0, "ETH": 3100.0, "SOL": 190.0}
    daily_vol = {"BTC": 0.025, "ETH": 0.035, "SOL": 0.045}

    start_price = base_prices.get(symbol, 100.0)
    vol = daily_vol.get(symbol, 0.03)

    np.random.seed(42 if symbol == "BTC" else (43 if symbol == "ETH" else 44))
    now = datetime.now(timezone.utc)
    dates = [now - timedelta(days=days - i) for i in range(days)]

    prices = [start_price]
    for _ in range(1, days):
        ret = np.random.normal(0.0005, vol)
        prices.append(max(prices[-1] * (1 + ret), 1.0))

    rows = []
    for dt, close in zip(dates, prices):
        day_noise = close * vol * 0.5
        rows.append({
            "timestamp": int(dt.timestamp() * 1000),
            "date": dt.strftime("%Y-%m-%d"),
            "open": round(close - np.random.uniform(-day_noise, day_noise), 2),
            "high": round(close + abs(np.random.uniform(0, day_noise * 1.5)), 2),
            "low": round(close - abs(np.random.uniform(0, day_noise * 1.5)), 2),
            "close": round(close, 2),
            "volume": round(np.random.uniform(1000, 50000) * (start_price / close), 2),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df
