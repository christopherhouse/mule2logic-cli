# IR (Intermediate Representation) Service

Intermediate representation v1 for the MuleSoft → Logic Apps Standard migration pipeline.

## Responsibilities

- Define the IR schema for MuleSoft projects and flows
- Provide JSON serialization/deserialization for debugging and tests
- Supply builder helpers for constructing IR nodes

## IR Structure

The IR is a tree rooted at `MuleIR`:

```
MuleIR
├── ir_metadata (version, timestamp, source mode, source path)
├── project_metadata (name, group_id, artifact_id, version — optional in single-flow mode)
├── flows[]
│   ├── kind (flow | sub_flow)
│   ├── name
│   ├── trigger? (HTTP listener, scheduler, etc.)
│   ├── steps[] — discriminated union (FlowStep):
│   │   ├── Processor (logger, set-variable, flow-ref, etc.)
│   │   ├── VariableOperation (set/remove)
│   │   ├── Transform (DataWeave, set-payload, expression)
│   │   ├── ConnectorOperation (HTTP request, DB, MQ, etc.)
│   │   ├── Router (choice, scatter-gather, etc.)
│   │   └── Scope (foreach, try, until-successful, etc.)
│   └── error_handlers[]
└── warnings[] (reuses Warning from m2la-contracts)
```

## Usage

```python
from m2la_ir import build_project_ir, make_flow, make_http_trigger, to_json, from_json

ir = build_project_ir(
    source_path="/my-project",
    project_name="my-app",
    flows=[make_flow(name="main", trigger=make_http_trigger(path="/api"))],
)

json_str = to_json(ir)
restored = from_json(json_str)
```

## Development

```bash
cd services/ir
uv sync
uv run pytest -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
