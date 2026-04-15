# MuleSoft → Logic Apps Standard Migration Platform

An AI-assisted platform that converts MuleSoft (Anypoint) projects into Azure Logic Apps Standard projects.

## Overview

This platform supports two input modes:

- **Project mode**: Full MuleSoft project root (pom.xml + flows) → complete Logic Apps Standard project
- **Single-flow mode**: Individual Mule flow XML → standalone workflow JSON

### Architecture

| Component | Location | Technology |
|-----------|----------|------------|
| API Backend | `apps/api/` | Python 3.13, FastAPI |
| CLI | `apps/cli/` | TypeScript, chalk |
| Shared Contracts | `packages/contracts/` | JSON schemas, DTOs |
| Connector Mappings | `packages/mapping-config/` | YAML config |
| Sample Projects | `packages/sample-projects/` | MuleSoft XML fixtures |
| Mule Parser | `services/parser/` | Python |
| IR Models | `services/ir/` | Python |
| Transformation | `services/transform/` | Python |
| Validation | `services/validate/` | Python |
| Agent Orchestration | `services/agents/` | Microsoft Agent Framework |
| Infrastructure | `infra/bicep/` | Bicep + Azure Verified Modules |

## Prerequisites

- **Python 3.13** — required runtime for the backend
- **[uv](https://docs.astral.sh/uv/)** — Python package/environment manager (the **only** tool used for Python; do not use pip, poetry, or conda)
- **Node.js 20+** — required for the CLI
- **npm** — Node package manager

### Installing uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Getting Started

### API Backend (Python)

```bash
cd apps/api

# Create virtual environment and install dependencies (uses uv exclusively)
uv venv --python 3.13
uv sync --all-groups

# Run the API server
uv run m2la-api

# Or run directly
uv run uvicorn m2la_api.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. API docs at `http://127.0.0.1:8000/docs`.

#### API Endpoints

**Transform Endpoints:**
- `POST /transform` — Traditional transform (returns complete result)
- `POST /transform/stream` — Streaming transform with Server-Sent Events (SSE)

**Other Endpoints:**
- `POST /analyze` — Analyze MuleSoft project and estimate migration complexity
- `POST /validate` — Validate generated Logic Apps artifacts
- `GET /health` — Health check endpoint

**Streaming Example (curl):**
```bash
curl -N -F "file=@project.zip" http://127.0.0.1:8000/transform/stream
```

The streaming endpoint emits SSE events:
```
event: agent_started
data: {"agent_name": "AnalyzerAgent", "correlation_id": "..."}

event: agent_completed
data: {"agent_name": "AnalyzerAgent", "status": "success", "duration_ms": 1234}

event: complete
data: {"overall_status": "success", "total_duration_ms": 5678}
```

#### API Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `M2LA_HOST` | `127.0.0.1` | API server bind address |
| `M2LA_PORT` | `8000` | API server port |
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | (none) | Azure Monitor connection string for telemetry export |

### CLI (TypeScript)

```bash
cd apps/cli

# Install dependencies
npm install

# Run the CLI (development)
npm run dev

# Build the CLI
npm run build

# Run the built CLI
node dist/index.js
```

### CLI Usage

#### Transform Command

```bash
# Transform with default (non-streaming) mode
m2la transform path/to/mule-project

# Transform with streaming mode for real-time progress
m2la transform path/to/mule-project --stream

# Transform with custom output directory
m2la transform path/to/mule-project -o ./my-output

# Transform single flow XML
m2la transform path/to/flow.xml --stream
```

**Streaming Mode** (`--stream`):
- Provides real-time agent-by-agent progress updates
- Shows duration for each pipeline stage
- Better UX for long-running transformations
- Uses Server-Sent Events (SSE) from the backend

**Traditional Mode** (default):
- Uses a spinner while waiting for completion
- Returns full results once pipeline finishes
- Compatible with older backend versions

#### CLI Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `M2LA_BACKEND_URL` | `http://localhost:8000` | Backend API base URL |
| `M2LA_API_TOKEN` | (none) | Optional API token for backend authentication |
| `M2LA_VERBOSE` | `false` | Enable verbose output |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | (none) | Azure Monitor connection string for telemetry export |
| `OTEL_SERVICE_NAME` | `m2la-cli` | Optional service name override for OpenTelemetry |

**Azure Monitor / Application Insights Configuration:**

To enable telemetry export to Azure Application Insights, set the `APPLICATIONINSIGHTS_CONNECTION_STRING` environment variable to your Application Insights connection string:

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<key>;IngestionEndpoint=<endpoint>;LiveEndpoint=<endpoint>"
```

You can find your connection string in the Azure Portal under your Application Insights resource → Overview → Connection String.

When the connection string is not set, the CLI runs in local development mode with telemetry disabled.

## Development

### API — Lint, Format, and Test

```bash
cd apps/api

# Lint
uv run ruff check src/ tests/

# Format check
uv run ruff format --check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Auto-format
uv run ruff format src/ tests/

# Run tests
uv run pytest
```

### CLI — Lint, Format, and Test

```bash
cd apps/cli

# Lint
npm run lint

# Format check
npm run format

# Auto-fix lint issues
npm run lint:fix

# Auto-format
npm run format:fix

# Type check
npx tsc --noEmit

# Run tests
npm test
```

## Repository Structure

```
├── apps/
│   ├── api/                    # Python 3.13 FastAPI backend
│   └── cli/                    # TypeScript CLI
├── packages/
│   ├── contracts/              # Shared schemas and DTOs
│   ├── mapping-config/         # Connector mapping configuration
│   └── sample-projects/        # MuleSoft test fixtures
├── services/
│   ├── parser/                 # Mule project/flow parsing
│   ├── ir/                     # Intermediate representation
│   ├── transform/              # IR → Logic Apps transformation
│   ├── validate/               # Output validation
│   └── agents/                 # Agent Framework orchestration
├── infra/
│   └── bicep/                  # Azure infrastructure (Bicep + AVM)
├── docs/
│   ├── architecture/           # Architecture documentation
│   ├── adrs/                   # Architecture Decision Records
│   ├── runbooks/               # Operational runbooks
│   ├── mule2logic-cli-spec.md  # Product specification
│   └── copilot-coding-agent-implementation-plan.md
└── README.md
```

## Key Design Decisions

- **uv exclusively** for Python dependency management — no pip, poetry, or conda
- **Bicep with Azure Verified Modules** for infrastructure — no Terraform or ARM
- **User Assigned Managed Identity (UAMI) only** — no secrets in generated artifacts
- **Built-in Logic Apps connectors preferred** with identity-based authentication
- **OpenTelemetry** for end-to-end observability

## Infrastructure & Deployment

Infrastructure is defined in `infra/bicep/` using Azure Verified Modules (AVM). CI/CD uses GitHub Actions with OIDC federated identity.

- [Deployment Guide](docs/deployment.md) — OIDC setup, manual deployment, CI/CD overview
- [Infrastructure README](infra/bicep/README.md) — Bicep module structure and parameters

### CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|----------|
| PR Validation | Pull request | Lint, test, build, Bicep validate, Docker build |
| Deploy | Push to main / manual | Deploy infra → build image → update Container App |
| Bicep What-If | PR with infra changes | Infrastructure diff in PR comment |

## Documentation

- [Product Specification](docs/mule2logic-cli-spec.md)
- [Implementation Plan](docs/copilot-coding-agent-implementation-plan.md)
- [Deployment Guide](docs/deployment.md)

## License

[MIT](LICENSE)