# Cryptia - Project Guidelines

## Overview
**Cryptia** is a Python-based project focusing on machine learning and predictive modeling using LightGBM, NumPy, and SciPy. The project is automated with Podman containerization and local CI/CD pipelines powered by `act`.

---

## Tooling & Environment

### Package and Environment Management
- **Manager:** [`uv`](https://astral.sh/uv) is the standard package and environment manager for this project.
- **Python Version:** Python >= 3.12.
- **Virtual Environment:** Located at `.venv/` (automatically managed by `uv`).

### Container & Local Runner Tooling
- **Container Engine:** Podman (rootless, socket active at `/run/user/1000/podman/podman.sock`).
- **Global Nginx Reverse Proxy:** Systemd Quadlet container (`global-nginx.service`) running on network `global-proxy`, autostarting on boot (`Linger=yes`). Configs at `~/.config/nginx/conf.d/`.
- **CI/CD Local Runner:** [`act`](https://github.com/nektos/act) binary on host orchestrating workflow steps inside Podman runner containers (`catthehacker/ubuntu:act-22.04`).
- **Automated Trigger:** Git post-commit hook (`.git/hooks/post-commit`) calling runner wrapper (`scripts/run-runner.sh`).

### Common Commands
- **Run scripts locally:**
  ```bash
  uv run python src/main.py
  ```
- **Run CLI entry points:**
  ```bash
  uv run cryptia
  ```
- **Add dependencies:**
  ```bash
  uv add <package-name>
  uv add --dev <package-name>
  ```
- **Build & run container directly with Podman:**
  ```bash
  podman build -t cryptia:latest .
  podman run --rm cryptia:latest
  # Or run attached to the global proxy network:
  podman run -d --name cryptia --network global-proxy cryptia:latest
  ```
- **Trigger local runner manually:**
  ```bash
  ./scripts/run-runner.sh development   # Build and verify local container
  ./scripts/run-runner.sh main          # Build and deploy to remote GCE VM
  ```

---

## Project Structure

```text
cryptia/
├── .agents/                    # Agent customizations & automation
│   ├── hooks.json              # Lifecycle hooks
│   └── rules/                  # Workspace rules
│       └── project-guidelines.md
├── .github/
│   └── workflows/              # GitHub Actions CI/CD workflows
│       └── ci-cd.yml           # Local build (dev) & remote deploy (main)
├── scripts/                    # Automation scripts
│   └── run-runner.sh           # Local act runner executor
├── src/                        # Application source code
│   ├── cryptia/                # Primary library package
│   │   ├── __init__.py         # Package entry points
│   │   ├── api.py              # FastAPI REST endpoints
│   │   ├── config.py           # Configuration & crypto assets
│   │   ├── data.py             # Historical OHLCV data & caching
│   │   └── model.py            # LightGBM training & forecasting
│   ├── static/                 # Frontend dashboard
│   │   ├── app.js              # Interactive UI, charts & API client
│   │   └── index.html          # Tailwind CSS dashboard with Chart.js
│   └── main.py                 # Uvicorn entry point
├── data/                       # Local data persistence (git-ignored)
│   ├── cache/                  # Historical OHLCV JSON caches
│   └── models/                 # Serialized LightGBM models & metadata
├── Dockerfile                  # Container definition (Python 3.12, OpenMP, uv)
├── .dockerignore               # Container build exclusions
├── .secrets.example            # Template for remote GCE VM credentials
├── pyproject.toml              # Build & dependency declarations (PEP 621)
├── uv.lock                     # Deterministic dependency lockfile
├── .gitignore                  # Git ignore definitions (.venv, secrets, etc.)
└── README.md                   # Project documentation
```

---

## Branching & CI/CD Pipeline Strategy

The CI/CD pipeline defined in `.github/workflows/ci-cd.yml` automates workflows based on the active branch:

1. **`development` Branch (Local Container Verification):**
   - Automatically triggered on every commit.
   - Builds the Podman container `cryptia:latest` and tags it with the branch name.
   - Runs a test container execution locally to verify dependencies and execution.

2. **`main` Branch (Remote GCE VM Deployment):**
   - Automatically triggered on every commit to `main`.
   - Builds and packages the container image (`cryptia:latest`).
   - Exports the container image to an archive and transfers it to the Google Cloud Compute Engine VM over SSH.
   - On the remote VM, loads the image, terminates any older container instance, and starts the updated container (`--restart always`).
   - Credentials configured via `.secrets` (see `.secrets.example`):
     - `GCE_HOST`: Public IP or hostname of the GCE VM.
     - `GCE_USER`: Remote SSH username.
     - `GCE_SSH_KEY`: Private SSH key for VM authentication.
     - `GCE_PORT`: SSH port (default: 22).

---

## Dependencies & System Requirements

- **Primary Dependencies:**
  - `fastapi >= 0.161.0`: REST API framework.
  - `uvicorn >= 0.54.0`: ASGI production server.
  - `lightgbm >= 4.7.0`: Gradient boosting framework for time-series forecasting.
  - `pandas >= 3.1.0`: Time-series OHLCV data manipulation and feature engineering.
  - `numpy >= 2.5.4`: Numerical arrays and linear algebra.
  - `scipy >= 1.18.1`: Scientific computing and optimization.
  - `scikit-learn >= 1.9.0`: Evaluation metrics (RMSE, MAE, R²).
  - `httpx >= 0.28.0`: Async HTTP client for crypto exchange APIs.
- **System Prerequisites:**
  - Linux OpenMP runtime library (`libgomp.so.1` / `libgomp1`) is required for LightGBM multi-threading.
  - Podman socket must be running (`systemctl --user enable --now podman.socket`).

---

## Coding Standards & Conventions

1. **Environment Consistency:**
   - Always run commands via `uv run` to ensure execution against the designated virtual environment.
   - Do not invoke global `pip` or modify system Python packages directly.

2. **Code Style & Typing:**
   - Use Python 3 type annotations (`typing` or built-in generics) for function signatures and critical data structures.
   - Maintain clear docstrings and comments explaining data transformations and model configurations.

3. **Machine Learning Best Practices:**
   - Set explicit random seeds (`random_state` / `seed`) across NumPy and LightGBM for deterministic behavior.
   - Use `lgb.Dataset` efficiently with appropriate validation sets to avoid data leakage.
   - Separate data preparation, feature engineering, and model inference into modular functions/modules under `src/cryptia/`.

4. **Version Control & Secret Hygiene:**
   - Never commit `.secrets`, `.venv/`, compiled bytecode (`__pycache__/`, `*.pyc`), model checkpoints, or raw datasets to git.
   - Keep `uv.lock` synchronized whenever `pyproject.toml` dependencies are modified.
