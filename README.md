# Cryptia

Cryptocurrency machine learning platform with a **FastAPI** backend and **Tailwind CSS** dashboard. Provides automated historical OHLCV data retrieval, **LightGBM** time-series model training, and recursive multi-step price forecasting from **1 day up to 30 days** (1 month) with 95% confidence bounds.

Supported cryptocurrencies:
- **Bitcoin (BTC)**
- **Ethereum (ETH)**
- **Solana (SOL)**

## Getting Started

### Local Python Environment (`uv`)
```bash
# Run FastAPI REST API and Frontend Dashboard:
uv run python src/main.py

# Access in browser:
# http://localhost:8000        (Interactive Dashboard)
# http://localhost:8000/docs   (Swagger REST API Docs)
```

### Local Container Build & Run (Podman)
```bash
# Build image
podman build -t cryptia:latest .

# Run container attached to global proxy:
podman run -d --name cryptia --network global-proxy -p 8000:8000 cryptia:latest

# Access in browser via global Nginx proxy:
# http://localhost:8080/
```

---

## FastAPI REST API Endpoints

- `GET /api/cryptos`: List supported cryptos (BTC, ETH, SOL) with model status and prices.
- `GET /api/crypto/{symbol}/history?days=180`: Fetch daily OHLCV historical price data.
- `POST /api/crypto/{symbol}/train`: Train/retrain LightGBM model with time-series feature engineering.
- `POST /api/crypto/{symbol}/predict`: Forecast future prices from 1 to 30 days ahead (recursive multi-step inference).
- `GET /docs`: Interactive Swagger UI documentation.


---

## Local CI/CD Runner (`act` + Podman)

This repository includes automated local runners powered by [`act`](https://github.com/nektos/act) and rootless Podman.

### Automatic Execution on Git Commit
A post-commit git hook is installed at `.git/hooks/post-commit`. Every time you commit:
- **`development` branch:** Automatically runs `act` to build and verify the Podman container on your local machine.
- **`main` branch:** Automatically runs `act` to build the container, package it, and deploy it to your remote Google Cloud Compute Engine VM over SSH.

### Manual Runner Execution
You can manually trigger the runner for any branch:
```bash
./scripts/run-runner.sh development   # Build and verify local container
./scripts/run-runner.sh main          # Deploy to remote GCE VM
```

### Remote GCE Deployment Configuration
To deploy to your GCE VM on `main` commits, copy `.secrets.example` to `.secrets` and fill in your VM details:
```bash
cp .secrets.example .secrets
```
Edit `.secrets`:
- `GCE_HOST`: External IP address of your GCE VM.
- `GCE_USER`: VM username (e.g., `ubuntu`).
- `GCE_SSH_KEY`: Private SSH key contents for authentication.
- `GCE_PORT`: SSH port (default: 22).
*(Note: `.secrets` is git-ignored and never committed).*
