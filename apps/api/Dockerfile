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

# Create the virtual environment at the FINAL runtime path (/app/.venv) so that
# shebang lines in scripts like uvicorn reference /app/.venv/bin/python — which
# will be valid after the venv is copied into the runtime stage.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Mirror the repo layout so the relative paths in pyproject.toml resolve correctly.
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/contracts/src/ packages/contracts/src/

# Copy all service packages that the API depends on
COPY services/parser/pyproject.toml services/parser/pyproject.toml
COPY services/parser/src/ services/parser/src/

COPY services/ir/pyproject.toml services/ir/pyproject.toml
COPY services/ir/src/ services/ir/src/

COPY services/mapping-config/pyproject.toml services/mapping-config/pyproject.toml
COPY services/mapping-config/src/ services/mapping-config/src/

COPY services/transform/pyproject.toml services/transform/pyproject.toml
COPY services/transform/src/ services/transform/src/

COPY services/validate/pyproject.toml services/validate/pyproject.toml
COPY services/validate/src/ services/validate/src/

COPY services/agents/pyproject.toml services/agents/pyproject.toml
COPY services/agents/src/ services/agents/src/

# Copy mapping config data files
COPY packages/mapping-config/ packages/mapping-config/

# Copy API dependency files for layer caching
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/uv.lock apps/api/uv.lock

# Sync dependencies (production only, no dev deps)
# --no-editable ensures packages are installed into site-packages (not .pth
# symlinks back to /build/…) so the venv is fully self-contained.
RUN cd apps/api && uv sync --no-dev --no-editable --no-install-project

# Copy API application source
COPY apps/api/src/ apps/api/src/

# Install project itself
RUN cd apps/api && uv sync --no-dev --no-editable

# --- Stage 2: Runtime ---
FROM python:3.13-slim AS runtime

# Security: run as non-root user
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy the virtual environment from the builder (already at /app/.venv)
COPY --from=builder /app/.venv /app/.venv

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# FastAPI/uvicorn port
EXPOSE 8000

# Switch to non-root user
USER app

# Run the API — bind to 0.0.0.0 for container networking
CMD ["uvicorn", "m2la_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
