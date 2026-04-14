# Validation Service

Deterministic validation engine for MuleSoft to Logic Apps migration platform.

## Responsibilities

- Validate Mule project input completeness (project mode)
- Validate single-flow XML input validity (single-flow mode)
- Validate IR integrity (flow references, variable usage, trigger presence)
- Validate generated Logic Apps output integrity (file layout, schema, runAfter refs)
- Check connector preference compliance (built-in > managed, identity-based auth)
- Emit structured validation reports with severity levels and remediation hints

## Usage

```python
from pathlib import Path
from m2la_contracts.enums import InputMode
from m2la_validate import validate_mule_input, validate_ir, validate_output
from m2la_validate.engine import validate_all

# Validate Mule project input
report = validate_mule_input(Path("path/to/project"), InputMode.PROJECT)

# Validate IR
report = validate_ir(ir)

# Validate generated output
report = validate_output(Path("path/to/output"), InputMode.PROJECT)

# Or run all stages at once
report = validate_all(
    input_path=Path("path/to/project"),
    mode=InputMode.PROJECT,
    ir=ir,
    output=Path("path/to/output"),
)
```

## Development

```bash
cd services/validate
uv sync
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest -v
```
