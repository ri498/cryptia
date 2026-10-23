import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cryptia.config import (
    SUPPORTED_CRYPTOS,
    STATIC_DIR,
    DEFAULT_CRYPTO,
    MIN_HORIZON_DAYS,
    MAX_HORIZON_DAYS,
)
from cryptia.data import fetch_crypto_history
from cryptia.model import train_crypto_model, get_model_metadata, generate_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cryptia.api")

app = FastAPI(
    title="Cryptia API",
    description="Machine Learning Cryptocurrency Training and Price Forecasting API powered by LightGBM",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class PredictRequest(BaseModel):
    horizon_days: int = Field(
        default=7,
        ge=MIN_HORIZON_DAYS,
        le=MAX_HORIZON_DAYS,
        description="Number of days to forecast (1 to 30 days / 1 month)",
    )


@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "service": "cryptia-api"}


@app.get("/api/cryptos")
async def get_cryptos():
    """Return list of supported cryptocurrencies and model statuses."""
    result = []
    for symbol, meta in SUPPORTED_CRYPTOS.items():
        model_meta = get_model_metadata(symbol)
        item = {
            "symbol": symbol,
            "name": meta["name"],
            "pair": meta["pair"],
            "color": meta["color"],
            "gradient": meta["gradient"],
            "icon": meta["icon"],
            "is_trained": model_meta is not None,
            "last_trained": model_meta.get("trained_at") if model_meta else None,
            "metrics": model_meta.get("metrics") if model_meta else None,
            "last_price": model_meta.get("last_price") if model_meta else None,
        }
        result.append(item)
    return {"cryptos": result}


@app.get("/api/crypto/{symbol}/history")
async def get_crypto_history(symbol: str, days: int = Query(default=180, ge=7, le=1000)):
    """Fetch historical daily price and volume data for a cryptocurrency."""
    symbol = symbol.upper()
    if symbol not in SUPPORTED_CRYPTOS:
        raise HTTPException(status_code=404, detail=f"Crypto '{symbol}' not found. Supported: {list(SUPPORTED_CRYPTOS.keys())}")

    try:
        df = await fetch_crypto_history(symbol, days=days)
        history = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": round(float(row["volume"]), 2),
            }
            for _, row in df.iterrows()
        ]
        return {
            "symbol": symbol,
            "name": SUPPORTED_CRYPTOS[symbol]["name"],
            "count": len(history),
            "history": history,
        }
    except Exception as exc:
        logger.error("Error retrieving history for %s: %s", symbol, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/crypto/{symbol}/train")
async def train_model(symbol: str, days: int = Query(default=365, ge=90, le=1000)):
    """Fetch latest historical data and train a LightGBM model for the given symbol."""
    symbol = symbol.upper()
    if symbol not in SUPPORTED_CRYPTOS:
        raise HTTPException(status_code=404, detail=f"Crypto '{symbol}' not found. Supported: {list(SUPPORTED_CRYPTOS.keys())}")

    try:
        df = await fetch_crypto_history(symbol, days=days)
        meta = train_crypto_model(symbol, df)
        return {
            "success": True,
            "message": f"LightGBM model for {symbol} trained successfully.",
            "data": meta,
        }
    except Exception as exc:
        logger.error("Failed to train model for %s: %s", symbol, exc)
        raise HTTPException(status_code=500, detail=f"Training failed: {str(exc)}")


@app.get("/api/crypto/{symbol}/model")
async def get_model_info(symbol: str):
    """Retrieve model training metrics and parameters for a cryptocurrency."""
    symbol = symbol.upper()
    if symbol not in SUPPORTED_CRYPTOS:
        raise HTTPException(status_code=404, detail=f"Crypto '{symbol}' not found.")

    meta = get_model_metadata(symbol)
    if not meta:
        return {
            "symbol": symbol,
            "is_trained": False,
            "message": f"No model has been trained for {symbol} yet.",
        }
    return {"symbol": symbol, "is_trained": True, "data": meta}


@app.post("/api/crypto/{symbol}/predict")
async def predict_crypto(symbol: str, req: PredictRequest):
    """Generate recursive price predictions for 1 to 30 days ahead."""
    symbol = symbol.upper()
    if symbol not in SUPPORTED_CRYPTOS:
        raise HTTPException(status_code=404, detail=f"Crypto '{symbol}' not found. Supported: {list(SUPPORTED_CRYPTOS.keys())}")

    try:
        df = await fetch_crypto_history(symbol, days=365)
        forecast_result = generate_forecast(symbol, df, horizon_days=req.horizon_days)
        return {
            "success": True,
            "forecast": forecast_result,
        }
    except Exception as exc:
        logger.error("Prediction error for %s: %s", symbol, exc)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}")


# Frontend Web Routes
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Cryptia Dashboard is loading...</h1>")


@app.get("/{catchall:path}", response_class=HTMLResponse)
async def serve_spa_routes(catchall: str):
    # Route frontend SPA paths like /train and /predict back to index.html
    if catchall.startswith("api") or catchall.startswith("static"):
        raise HTTPException(status_code=404, detail="Not Found")
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Cryptia Dashboard</h1>")
