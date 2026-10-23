import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from cryptia.config import MODELS_DIR, SUPPORTED_CRYPTOS

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "ret_1d",
    "ret_2d",
    "ret_3d",
    "ret_7d",
    "ret_14d",
    "vol_7d",
    "vol_14d",
    "ma_7_ratio",
    "ma_14_ratio",
    "ma_30_ratio",
    "vol_change_7d",
    "dow_sin",
    "dow_cos",
]

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate time-series technical indicators and cyclical features.
    """
    data = df.copy()
    data.sort_values("date", inplace=True)
    data.reset_index(drop=True, inplace=True)

    # Daily relative returns
    data["ret_1d"] = data["close"].pct_change(1)
    data["ret_2d"] = data["close"].pct_change(2)
    data["ret_3d"] = data["close"].pct_change(3)
    data["ret_7d"] = data["close"].pct_change(7)
    data["ret_14d"] = data["close"].pct_change(14)

    # Rolling Volatility of returns
    data["vol_7d"] = data["ret_1d"].rolling(window=7).std()
    data["vol_14d"] = data["ret_1d"].rolling(window=14).std()

    # Moving Average Ratios (Price vs MA)
    ma_7 = data["close"].rolling(window=7).mean()
    ma_14 = data["close"].rolling(window=14).mean()
    ma_30 = data["close"].rolling(window=30).mean()

    data["ma_7_ratio"] = (data["close"] / ma_7) - 1.0
    data["ma_14_ratio"] = (data["close"] / ma_14) - 1.0
    data["ma_30_ratio"] = (data["close"] / ma_30) - 1.0

    # Volume momentum
    vol_ma_7 = data["volume"].rolling(window=7).mean()
    data["vol_change_7d"] = (data["volume"] / vol_ma_7) - 1.0

    # Cyclical day of week encoding
    day_of_week = data["date"].dt.dayofweek
    data["dow_sin"] = np.sin(2 * np.pi * day_of_week / 7.0)
    data["dow_cos"] = np.cos(2 * np.pi * day_of_week / 7.0)

    # Target: Next-day return
    data["target_return"] = data["ret_1d"].shift(-1)

    return data


def train_crypto_model(symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Train a LightGBM regressor on historical crypto data.
    """
    symbol = symbol.upper()
    featured_df = create_features(df)
    clean_df = featured_df.dropna(subset=FEATURE_COLS + ["target_return"]).copy()

    if len(clean_df) < 50:
        raise ValueError(f"Insufficient data points ({len(clean_df)}) to train model for {symbol}.")

    X = clean_df[FEATURE_COLS]
    y = clean_df["target_return"]

    # Chronological train/test split (last 20% test)
    split_idx = int(len(clean_df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_close = clean_df["close"].iloc[split_idx:]

    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=150,
        learning_rate=0.03,
        num_leaves=15,
        max_depth=5,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )

    model.fit(X_train, y_train)

    # Test evaluation
    y_pred_ret = model.predict(X_test)
    pred_close = test_close * (1 + y_pred_ret)
    actual_close = test_close * (1 + y_test)

    mae = float(mean_absolute_error(actual_close, pred_close))
    rmse = float(np.sqrt(mean_squared_error(actual_close, pred_close)))
    mape = float(np.mean(np.abs((actual_close - pred_close) / actual_close)) * 100)
    r2 = float(r2_score(actual_close, pred_close))

    # Directional accuracy (% of correct up/down direction predictions)
    actual_dir = np.sign(y_test)
    pred_dir = np.sign(y_pred_ret)
    directional_accuracy = float(np.mean(actual_dir == pred_dir) * 100)

    # Feature importances
    feature_importance = dict(zip(FEATURE_COLS, [float(v) for v in model.feature_importances_]))
    sorted_features = dict(sorted(feature_importance.items(), key=lambda item: item[1], reverse=True))

    # Save model and metadata
    model_path = MODELS_DIR / f"{symbol}_lgbm.joblib"
    meta_path = MODELS_DIR / f"{symbol}_meta.json"

    joblib.dump(model, model_path)

    recent_volatility = float(clean_df["vol_7d"].iloc[-1])
    if np.isnan(recent_volatility) or recent_volatility <= 0:
        recent_volatility = float(clean_df["ret_1d"].std())

    meta = {
        "symbol": symbol,
        "name": SUPPORTED_CRYPTOS[symbol]["name"],
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "samples_total": len(clean_df),
        "samples_train": len(X_train),
        "samples_test": len(X_test),
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2),
            "r2_score": round(r2, 4),
            "directional_accuracy_pct": round(directional_accuracy, 1),
        },
        "recent_volatility": round(recent_volatility, 5),
        "last_price": round(float(clean_df["close"].iloc[-1]), 2),
        "last_date": clean_df["date"].iloc[-1].strftime("%Y-%m-%d"),
        "top_features": sorted_features,
    }

    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info("Model for %s successfully trained and saved: RMSE=%.2f, MAPE=%.2f%%", symbol, rmse, mape)
    return meta


def get_model_metadata(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve saved model metadata for a given crypto symbol."""
    meta_path = MODELS_DIR / f"{symbol.upper()}_meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to read metadata for %s: %s", symbol, exc)
    return None


def generate_forecast(symbol: str, df: pd.DataFrame, horizon_days: int = 7) -> Dict[str, Any]:
    """
    Generate recursive multi-step price forecast for horizon_days (1 to 30 days).
    """
    symbol = symbol.upper()
    model_path = MODELS_DIR / f"{symbol}_lgbm.joblib"
    meta = get_model_metadata(symbol)

    if not model_path.exists() or meta is None:
        # Train model if not yet trained
        logger.info("Model for %s not found on disk. Training now...", symbol)
        meta = train_crypto_model(symbol, df)

    model = joblib.load(model_path)
    base_df = df.copy().sort_values("date").reset_index(drop=True)

    current_price = float(base_df["close"].iloc[-1])
    current_date = base_df["date"].iloc[-1]
    vol = meta.get("recent_volatility", 0.03)

    # Prepare working history dataframe
    sim_df = base_df.copy()
    predictions = []
    running_price = current_price

    for step in range(1, horizon_days + 1):
        feat_df = create_features(sim_df)
        last_row = feat_df.iloc[-1:]

        # Feature vector
        X_curr = last_row[FEATURE_COLS].copy()
        X_curr.fillna(0.0, inplace=True)

        predicted_return = float(model.predict(X_curr)[0])
        # Bound extreme single-day returns
        predicted_return = np.clip(predicted_return, -0.15, 0.15)

        next_price = running_price * (1.0 + predicted_return)
        next_date = current_date + timedelta(days=step)

        # Confidence bounds using square root of time
        uncertainty = 1.96 * vol * np.sqrt(step)
        lower_bound = max(next_price * (1.0 - uncertainty), 0.01)
        upper_bound = next_price * (1.0 + uncertainty)

        step_change_pct = ((next_price - current_price) / current_price) * 100.0

        predictions.append({
            "step": step,
            "date": next_date.strftime("%Y-%m-%d"),
            "predicted_price": round(next_price, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "predicted_return_pct": round(predicted_return * 100.0, 3),
            "cumulative_change_pct": round(step_change_pct, 2),
        })

        # Append step to simulated history for subsequent recursive steps
        new_row = pd.DataFrame([{
            "timestamp": int(next_date.timestamp() * 1000),
            "date": next_date,
            "open": running_price,
            "high": max(running_price, next_price),
            "low": min(running_price, next_price),
            "close": next_price,
            "volume": float(sim_df["volume"].iloc[-7:].mean()),
        }])
        sim_df = pd.concat([sim_df, new_row], ignore_index=True)
        running_price = next_price

    final_price = predictions[-1]["predicted_price"]
    total_change_pct = round(((final_price - current_price) / current_price) * 100.0, 2)
    total_change_usd = round(final_price - current_price, 2)

    trend = "bullish" if total_change_pct > 1.0 else ("bearish" if total_change_pct < -1.0 else "neutral")

    # Recent history for seamless visualization
    history_subset = base_df.iloc[-60:].copy()
    history_records = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "price": round(float(row["close"]), 2),
        }
        for _, row in history_subset.iterrows()
    ]

    return {
        "symbol": symbol,
        "name": SUPPORTED_CRYPTOS[symbol]["name"],
        "horizon_days": horizon_days,
        "current_price": round(current_price, 2),
        "current_date": current_date.strftime("%Y-%m-%d"),
        "final_predicted_price": final_price,
        "total_change_pct": total_change_pct,
        "total_change_usd": total_change_usd,
        "trend": trend,
        "predictions": predictions,
        "historical": history_records,
        "model_metrics": meta.get("metrics", {}),
    }
