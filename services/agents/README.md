# Agent Orchestration Service

Microsoft Agent Framework orchestration layer for the MuleSoft → Logic Apps
migration platform, powered by the
[Azure AI Agents SDK](https://learn.microsoft.com/en-us/azure/ai-services/agents/)
(`azure-ai-agents`).

## Architecture Overview

Agents are **thin orchestration wrappers** around the deterministic migration
services. They do **not** replace the services — they compose them into a
structured pipeline with correlation IDs, telemetry propagation, and
human-readable reasoning summaries.

Each agent registers its deterministic service logic as `FunctionTool`
callables via the Azure AI Agents SDK. This enables two execution modes:

* **Offline mode** (default) — agents call their deterministic services
  directly via `execute()`.  No LLM calls or network access.  Used in
  tests and CI.
* **Online mode** — agents are created on the Azure AI Agent Service via
  `AgentsClient`.  The backing LLM can reason about the migration and
  invoke the registered `FunctionTool` callables.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MigrationOrchestrator                        │
│          (online via AgentsClient  /  offline via execute())    │
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
│              (exposed as FunctionTool callables)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
AgentContext (correlation_id, input_path, accumulated_data)
    │
    ├─ AnalyzerAgent  [tool: analyze_mule_input]
    │   ├─ Calls: m2la_parser.parse()
    │   ├─ Calls: m2la_ir.builders.build_*_ir()
    │   ├─ Calls: m2la_validate.engine.validate_mule_input()
    │   └─ Deposits: inventory, ir, input_validation, input_mode
    │
    ├─ PlannerAgent  [tool: create_migration_plan]
    │   ├─ Calls: m2la_mapping_config.loader.load_all()
    │   ├─ Calls: MappingResolver.resolve_construct()
    │   └─ Deposits: migration_plan, mapping_config
    │
    ├─ TransformerAgent  [tool: transform_to_logic_apps]
    │   ├─ Calls: m2la_validate.engine.validate_ir()
    │   ├─ Calls: m2la_transform.generator.generate_project()
    │   │    or   m2la_transform.single_flow.generate_single_flow_workflow()
    │   └─ Deposits: transform_output, migration_gaps, ir_validation
    │
    ├─ ValidatorAgent  [tool: validate_output_artifacts]
    │   ├─ Calls: m2la_validate.engine.validate_output()
    │   └─ Deposits: output_validation
    │
    └─ RepairAdvisorAgent (optional)  [tool: suggest_repairs]
        ├─ Reads: output_validation, migration_gaps
        └─ Deposits: repair_suggestions
```

## Online vs Offline Mode

### Offline Mode (Default)

No Azure credentials or network required.  Each agent's `execute()` method
is called directly.  This is the mode used in tests and CI.

```python
from m2la_agents import MigrationOrchestrator

orchestrator = MigrationOrchestrator()
result = orchestrator.run(input_path="/path/to/mule-project")

print(result.overall_status)
for step in result.steps:
    print(f"{step.step_name}: {step.agent_result.reasoning_summary}")
```

### Online Mode (Azure AI Agent Service)

Requires an Azure AI Foundry project endpoint and credentials.  Agents
are created on the service, and the backing LLM can invoke registered
`FunctionTool` callables.

```python
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

from m2la_agents import AgentsClientConfig, MigrationOrchestrator

client = AgentsClient(
    endpoint="https://<project>.api.azureml.ms",
    credential=DefaultAzureCredential(),
)
config = AgentsClientConfig(
    endpoint="https://<project>.api.azureml.ms",
    model_deployment="gpt-4o",
)

orchestrator = MigrationOrchestrator(client=client, config=config)
result = orchestrator.run(
    input_path="/path/to/mule-project",
    output_directory="/path/to/output",
)
```

## Configuration

`AgentsClientConfig` controls the SDK connection:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endpoint` | `str \| None` | `None` | Azure AI Foundry project endpoint.  When `None` → offline mode. |
| `model_deployment` | `str` | `"gpt-4o"` | Model deployment name for agent LLM backing. |

## Agent Descriptions

| Agent | Responsibility | FunctionTool | Deterministic Services Used |
|-------|---------------|-------------|---------------------------|
| **AnalyzerAgent** | Parse input, build IR, validate input | `analyze_mule_input` | `m2la_parser`, `m2la_ir`, `m2la_validate` |
| **PlannerAgent** | Evaluate mapping availability, create plan | `create_migration_plan` | `m2la_mapping_config` |
| **TransformerAgent** | Generate Logic Apps artifacts from IR | `transform_to_logic_apps` | `m2la_transform`, `m2la_validate` |
| **ValidatorAgent** | Validate generated output artifacts | `validate_output_artifacts` | `m2la_validate` |
| **RepairAdvisorAgent** | Suggest fixes for issues and gaps | `suggest_repairs` | Rule-based mapping (no external services) |

## Where Deterministic Logic Ends and Orchestration Begins

- **Deterministic logic** lives in the service packages (`m2la_parser`,
  `m2la_ir`, `m2la_transform`, `m2la_validate`, `m2la_mapping_config`).
  These services parse XML, build data structures, generate JSON, and
  validate output — all with predictable, testable behaviour.

- **Orchestration logic** lives here in `m2la_agents`. Agents decide which
  services to call, in what order, how to handle errors, and how to compose
  results into a pipeline. They also produce human-readable reasoning summaries.

- **SDK integration** exposes deterministic logic as `FunctionTool` callables.
  When running online, the LLM can invoke these tools and add reasoning on top.
  The tools do not replace the deterministic logic — they wrap it.

## Development

```bash
cd services/agents
uv sync
uv run pytest
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
