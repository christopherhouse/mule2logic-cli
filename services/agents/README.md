# Agent Orchestration Service

Microsoft Agent Framework orchestration layer for the MuleSoft → Logic Apps
migration platform.

## Architecture Overview

Agents are **thin orchestration wrappers** around the deterministic migration
services. They do **not** replace the services — they compose them into a
structured pipeline with correlation IDs, telemetry propagation, and
human-readable reasoning summaries.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MigrationOrchestrator                        │
│                                                                 │
│  ┌──────────┐  ┌─────────┐  ┌─────────────┐  ┌───────────┐    │
│  │ Analyzer │→ │ Planner │→ │ Transformer │→ │ Validator │──┐ │
│  └────┬─────┘  └────┬────┘  └──────┬──────┘  └─────┬─────┘  │ │
│       │              │              │                │         │ │
│       ▼              ▼              ▼                ▼         ▼ │
│  ┌─────────┐  ┌───────────┐ ┌───────────┐  ┌──────────┐ ┌────┐│
│  │ Parser  │  │ Mapping   │ │ Transform │  │ Validate │ │Rep.││
│  │ IR Build│  │ Config    │ │ Generator │  │ Engine   │ │Adv.││
│  │ Validate│  │ Resolver  │ │           │  │          │ │    ││
│  └─────────┘  └───────────┘ └───────────┘  └──────────┘ └────┘│
│       ▲              ▲              ▲                ▲          │
│       └──────────────┴──────────────┴────────────────┘          │
│                  Deterministic Services                          │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
AgentContext (correlation_id, input_path, accumulated_data)
    │
    ├─ AnalyzerAgent
    │   ├─ Calls: m2la_parser.parse()
    │   ├─ Calls: m2la_ir.builders.build_*_ir()
    │   ├─ Calls: m2la_validate.engine.validate_mule_input()
    │   └─ Deposits: inventory, ir, input_validation, input_mode
    │
    ├─ PlannerAgent
    │   ├─ Calls: m2la_mapping_config.loader.load_all()
    │   ├─ Calls: MappingResolver.resolve_construct()
    │   └─ Deposits: migration_plan, mapping_config
    │
    ├─ TransformerAgent
    │   ├─ Calls: m2la_validate.engine.validate_ir()
    │   ├─ Calls: m2la_transform.generator.generate_project()
    │   │    or   m2la_transform.single_flow.generate_single_flow_workflow()
    │   └─ Deposits: transform_output, migration_gaps, ir_validation
    │
    ├─ ValidatorAgent
    │   ├─ Calls: m2la_validate.engine.validate_output()
    │   └─ Deposits: output_validation
    │
    └─ RepairAdvisorAgent (optional)
        ├─ Reads: output_validation, migration_gaps
        └─ Deposits: repair_suggestions
```

## Agent Descriptions

| Agent | Responsibility | Deterministic Services Used |
|-------|---------------|---------------------------|
| **AnalyzerAgent** | Parse input, build IR, validate input | `m2la_parser`, `m2la_ir`, `m2la_validate` |
| **PlannerAgent** | Evaluate mapping availability, create plan | `m2la_mapping_config` |
| **TransformerAgent** | Generate Logic Apps artifacts from IR | `m2la_transform`, `m2la_validate` |
| **ValidatorAgent** | Validate generated output artifacts | `m2la_validate` |
| **RepairAdvisorAgent** | Suggest fixes for issues and gaps | Rule-based mapping (no external services) |

## Where Deterministic Logic Ends and Orchestration Begins

- **Deterministic logic** lives in the service packages (`m2la_parser`,
  `m2la_ir`, `m2la_transform`, `m2la_validate`, `m2la_mapping_config`).
  These services parse XML, build data structures, generate JSON, and
  validate output — all with predictable, testable behaviour.

- **Orchestration logic** lives here in `m2la_agents`. Agents decide which
  services to call, in what order, how to handle errors, and how to compose
  results into a pipeline. They also produce human-readable reasoning summaries.

The agents do **not** contain LLM calls. They are fully deterministic today.

## Extension Points for Future MCP/LLM Integration

Each agent has a `tools: list[Any]` attribute (currently empty). Future
integrations can:

1. Add MCP tool definitions to specific agents.
2. Extend the `execute()` method to invoke LLM-backed reasoning alongside
   deterministic service calls.
3. Use the `RepairAdvisorAgent` as the first candidate for LLM-enhanced
   suggestions, since its current rule-based approach has the most to gain
   from LLM reasoning.

The `BaseAgent` protocol is designed to remain stable through this evolution.

## Usage

```python
from m2la_agents import MigrationOrchestrator

orchestrator = MigrationOrchestrator()
result = orchestrator.run(
    input_path="/path/to/mule-project",
    output_directory="/path/to/output",
)

print(result.overall_status)
for step in result.steps:
    print(f"{step.step_name}: {step.agent_result.reasoning_summary}")
```

## Development

```bash
cd services/agents
uv sync
uv run pytest
uv run ruff check src/ tests/
```
