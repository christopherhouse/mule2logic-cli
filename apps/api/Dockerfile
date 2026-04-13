# ---------------------------------------------------------------------------
# Dockerfile — MuleSoft to Logic Apps API (multi-stage, uv-based)
# ---------------------------------------------------------------------------
# Stage 1: Build dependencies with uv
# Stage 2: Slim runtime image
# ---------------------------------------------------------------------------

# --- Stage 1: Builder ---
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml ./

# Sync dependencies (production only, no dev deps)
RUN uv sync --no-dev --no-install-project

# Copy application source
COPY src/ ./src/

# Install project itself
RUN uv sync --no-dev

# --- Stage 2: Runtime ---
FROM python:3.13-slim AS runtime

# Security: run as non-root user
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app/src /app/src

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# FastAPI/uvicorn port
EXPOSE 8000

# Switch to non-root user
USER app

# Run the API — bind to 0.0.0.0 for container networking
CMD ["uvicorn", "m2la_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
