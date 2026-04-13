# Parser Service

MuleSoft project and flow XML parsing logic.

## Responsibilities

- Parse MuleSoft project structure (pom.xml, configs, flow XMLs)
- Parse individual Mule flow XML files
- Extract connectors, flows, sub-flows, and configurations
- Build a normalized `ProjectInventory` model for downstream consumption

## Input Modes

### Project Mode

Given a MuleSoft project root directory:
- Parses `pom.xml` for project metadata and connector dependencies
- Discovers `src/main/mule/**/*.xml` flow files
- Discovers `src/main/resources/*.properties` configuration files
- Cross-references config-refs, flow-refs, and property placeholders
- Emits structured warnings for unresolvable references

### Single-Flow Mode

Given a standalone Mule XML file:
- Extracts flows and sub-flows from the file
- Emits warnings for external references (connector configs, properties, flow-refs)
- Does not require project structure (no pom.xml, no config discovery)

## Usage

```python
from m2la_parser import parse

# Project mode (auto-detected from directory path)
inventory = parse("/path/to/mule-project")

# Single-flow mode (auto-detected from .xml extension)
inventory = parse("/path/to/flow.xml")
```

## Development

```bash
cd services/parser
uv sync
uv run pytest -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
