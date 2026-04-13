# Contracts

Shared schemas, JSON schemas, and DTOs for the MuleSoft to Logic Apps migration platform.

This package provides the canonical contract definitions used by both the **Python backend** (FastAPI) and the **TypeScript CLI**.

## Architecture

- **Source of truth**: Python Pydantic models (`src/m2la_contracts/`)
- **JSON Schemas**: Auto-generated from Pydantic models (`schemas/`)
- **TypeScript types**: Hand-authored interfaces mirroring Pydantic models (`typescript/`)
- **Example payloads**: Sample request/response JSON files (`examples/`)

## Python Package (`m2la-contracts`)

### Installation

```bash
cd packages/contracts
uv venv --python 3.13
uv sync --all-groups
```

### Usage

```python
from m2la_contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    InputMode,
    detect_input_mode,
)

# Create a request
request = AnalyzeRequest(input_path="/path/to/mule-project")

# Auto-detect mode
mode = detect_input_mode("/path/to/flow.xml")  # -> InputMode.SINGLE_FLOW
mode = detect_input_mode("/path/to/project/")  # -> InputMode.PROJECT
```

### Models

| Module | Models |
|--------|--------|
| `enums` | `InputMode`, `Severity`, `GapCategory`, `ConstructCategory` |
| `telemetry` | `TelemetryContext` |
| `common` | `MigrationGap`, `ConstructCount`, `Warning`, `ArtifactEntry`, `ArtifactManifest` |
| `analyze` | `AnalyzeRequest`, `AnalyzeResponse`, `FlowAnalysis` |
| `transform` | `TransformRequest`, `TransformResponse` |
| `validate` | `ValidationIssue`, `ValidationReport` |
| `helpers` | `detect_input_mode()` |

### Generate JSON Schemas

```bash
uv run generate-schemas
```

Schemas are written to `schemas/`.

### Run Tests

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest -v
```

## TypeScript Package (`@m2la/contracts`)

### Installation

```bash
cd packages/contracts/typescript
npm install
```

### Usage

```typescript
import type { AnalyzeRequest, AnalyzeResponse, InputMode } from "@m2la/contracts";
```

### Build & Test

```bash
npm run build
npm test
```

## Input Modes

The platform supports two input modes, controlled by the `mode` field in request schemas:

- **`project`**: Full MuleSoft project root (directory containing `pom.xml` + flow XMLs)
- **`single_flow`**: Individual Mule flow XML file

When `mode` is `null`/omitted, it is auto-detected from the input path:
- Directory → `project`
- `.xml` file → `single_flow`

## Example Payloads

See `examples/` for sample request/response JSON files covering both modes.
