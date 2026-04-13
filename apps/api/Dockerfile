# ---------------------------------------------------------------------------
# Dockerfile — MuleSoft to Logic Apps API (multi-stage, uv-based)
# ---------------------------------------------------------------------------
# Stage 1: Build dependencies with uv
# Stage 2: Slim runtime image
#
# Build context MUST be the repository root so that the path dependency on
# packages/contracts is reachable:
#   docker build -f apps/api/Dockerfile . --tag m2la-api
# ---------------------------------------------------------------------------

# --- Stage 1: Builder ---
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Mirror the repo layout so the relative path in pyproject.toml
# (../../packages/contracts) resolves correctly.
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/contracts/src/ packages/contracts/src/

# Copy API dependency files for layer caching
COPY apps/api/pyproject.toml apps/api/pyproject.toml

# Sync dependencies (production only, no dev deps)
RUN cd apps/api && uv sync --no-dev --no-install-project

# Copy API application source
COPY apps/api/src/ apps/api/src/

# Install project itself
RUN cd apps/api && uv sync --no-dev

# --- Stage 2: Runtime ---
FROM python:3.13-slim AS runtime

# Security: run as non-root user
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /build/apps/api/.venv /app/.venv

# Copy application source
COPY --from=builder /build/apps/api/src /app/src

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# FastAPI/uvicorn port
EXPOSE 8000

# Switch to non-root user
USER app

# Run the API — bind to 0.0.0.0 for container networking
CMD ["uvicorn", "m2la_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
