# ---------------------------------------------------------------------------
# Dockerfile — MuleSoft → Logic Apps Migration API (FastAPI)
#
# Multi-stage build using uv for dependency management.
# Produces a minimal production image without dev dependencies.
# ---------------------------------------------------------------------------

# Stage 1: Build — install dependencies with uv
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev group)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ src/

# Install the project itself
RUN uv sync --frozen --no-dev

# Stage 2: Runtime — minimal image
FROM python:3.13-slim AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app/src /app/src

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
# FastAPI binds to 0.0.0.0 in container context
ENV M2LA_HOST="0.0.0.0"
ENV M2LA_PORT="8000"

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn (no reload in production)
CMD ["uvicorn", "m2la_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
