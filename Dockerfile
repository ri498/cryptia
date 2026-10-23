FROM python:3.12-slim

# Install system dependencies (OpenMP runtime required for LightGBM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Cache dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy application source code
COPY . .
RUN uv sync --frozen

# Ensure default execution uses the project virtual environment
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "src/main.py"]
