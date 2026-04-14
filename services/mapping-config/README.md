# m2la-mapping-config

Externalized connector and construct mapping configuration for the MuleSoft → Azure Logic Apps Standard migration platform.

## Overview

This service provides:

- **YAML config files** (in `packages/mapping-config/`) that declare how MuleSoft connectors and control-flow constructs map to Azure Logic Apps equivalents.
- **Pydantic models** for type-safe representation of all config entries.
- **A loader** that reads the YAML files from the canonical location in the repository.
- **A resolver** (`MappingResolver`) that looks up the best mapping for a given Mule element, applying priority rules.

## Priority Rules (spec §6)

Mappings are resolved in strict priority order:

1. **Built-in Logic Apps connectors** (`serviceProviderConnections`) — always preferred
2. **Identity-based authentication** (`managed-identity`) — preferred over key/secret
3. **Managed/API connectors** (`managedApiConnections`) — last resort only

## Config Files

| File | Purpose |
|------|---------|
| `packages/mapping-config/connector_mappings.yaml` | Maps Mule connector namespaces + elements → Logic Apps connector kind |
| `packages/mapping-config/construct_mappings.yaml` | Maps Mule control-flow constructs → Logic Apps action types |
| `packages/mapping-config/auth_preferences.yaml` | Defines priority ordering for auth types and connector types |

## Usage

```python
from m2la_mapping_config import load_all, MappingResolver

config = load_all()
resolver = MappingResolver(config)

# Resolve a connector
entry = resolver.resolve_connector(
    mule_namespace="http://www.mulesoft.org/schema/mule/http",
    mule_element="listener",
)
# entry.logic_apps.kind == "Request"

# Resolve a construct
construct = resolver.resolve_construct("foreach")
# construct.logic_apps_type == "Foreach"

# Check if an element has a supported mapping
resolver.is_supported("ee:transform")  # True
resolver.is_supported("logger")        # False
```

## Development

All commands must be run from within `services/mapping-config/`.

### Sync dependencies

```bash
uv sync
```

### Lint

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

### Format (auto-fix)

```bash
uv run ruff format src/ tests/
```

### Run tests

```bash
uv run pytest -v
```

## Package Structure

```
services/mapping-config/
├── pyproject.toml
├── README.md
├── src/
│   └── m2la_mapping_config/
│       ├── __init__.py     # Public API exports
│       ├── models.py       # Pydantic models
│       ├── loader.py       # YAML loader functions
│       └── resolver.py     # MappingResolver class
└── tests/
    ├── __init__.py
    ├── test_loader.py      # Tests for YAML loading
    ├── test_resolver.py    # Tests for resolver lookup against real config
    └── test_ranking.py     # Tests for rank_connectors with synthetic data
```
