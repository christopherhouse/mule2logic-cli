# Agent Orchestration Service

**Multi-agent orchestration** layer for the MuleSoft → Logic Apps migration
platform, powered by the
[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
(`agent-framework-core`) and the
[SequentialBuilder](https://github.com/microsoft/agent-framework)
multi-agent orchestration pattern.

## Architecture Overview

The orchestrator implements **multi-agent orchestration** where agents are
composed into a sequential workflow using the Microsoft Agent Framework (MAF).

Each agent:
- Has rich **system prompts** (loaded from `prompts/*.md`) with domain-specific instructions
- Returns deterministic services as callable **tool functions** via `_get_tools()`
- Can be constructed as a MAF `Agent` via `build_maf_agent(client)`
- Is composed into a `SequentialBuilder` workflow for LLM-driven orchestration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Microsoft Agent Framework (MAF)                       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              SequentialBuilder Workflow                          │  │
│  │              [Analyzer → Planner → Transformer → Validator →    │  │
│  │               RepairAdvisor]                                     │  │
│  └──────────┬───────────┬───────────┬───────────┬──────────────────┘  │
│             │           │           │           │                      │
│    ┌────────▼──┐  ┌─────▼─────┐  ┌─▼──────────┐ ┌──▼───────┐         │
│    │ Analyzer  │  │  Planner  │  │ Transformer │ │Validator │  ┌────┐ │
│    │ Agent     │  │  Agent    │  │ Agent       │ │Agent     │  │Rep.│ │
│    │           │  │           │  │             │ │          │  │Adv.│ │
│    │ tools:    │  │ tools:    │  │ tools:      │ │tools:    │  │    │ │
│    │ [analyze] │  │ [plan]    │  │ [transform] │ │[validate]│  │    │ │
│    └─────┬─────┘  └─────┬─────┘  └──────┬─────┘ └────┬─────┘  └──┬─┘ │
│          │              │               │             │            │   │
│  ┌───────▼──────────────▼───────────────▼─────────────▼────────────▼─┐ │
│  │                    Deterministic Services                         │ │
│  │  m2la_parser │ m2la_ir │ m2la_transform │ m2la_validate │ config  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

Workflow: user message → agents process sequentially → each agent invokes
          tool functions → final agent produces migration summary
```

## Multi-Agent Orchestration (Online Mode)

In online mode, the orchestrator uses the Microsoft Agent Framework:

1. **Build MAF agents** — Each agent (`AnalyzerAgent`, `PlannerAgent`, etc.)
   is constructed as a MAF `Agent` with its tool functions and domain-specific
   system prompt via `build_maf_agent(client)`.

2. **Compose with SequentialBuilder** — Agents are composed into a sequential
   workflow using `SequentialBuilder(participants=[...]).build()`.

3. **Run workflow** — The workflow is executed with a user message describing
   the migration request.  Each agent reasons about its task, invokes tool
   functions, and passes results to the next agent.

4. **Structured output** — The deterministic `execute()` path is also run
   to produce structured `AgentResult` objects. The LLM's reasoning is
   attached as `orchestrator_reasoning` in the final output.

```python
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from m2la_agents import FoundryClientConfig, MigrationOrchestrator

client = FoundryChatClient(
    project_endpoint="https://<project>.api.azureml.ms",
    model="gpt-4o",
    credential=AzureCliCredential(),
)
config = FoundryClientConfig(
    endpoint="https://<project>.api.azureml.ms",
    model="gpt-4o",
)

orchestrator = MigrationOrchestrator(client=client, config=config)
result = orchestrator.run(
    input_path="/path/to/mule-project",
    output_directory="/path/to/output",
)

# LLM reasoning from the workflow
if isinstance(result.final_output, dict):
    print(result.final_output.get("orchestrator_reasoning"))
```

## Offline Mode (Default)

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

## System Prompts

Each agent has a rich, domain-specific system prompt loaded from `prompts/*.md`:

| Prompt File | Agent | Purpose |
|-------------|-------|---------|
| `orchestrator.md` | Main orchestrator | Pipeline coordination, delegation rules, output format |
| `analyzer.md` | AnalyzerAgent | Input parsing, IR building, validation reporting |
| `planner.md` | PlannerAgent | Mapping evaluation, plan generation, gap estimation |
| `transformer.md` | TransformerAgent | IR→Logic Apps conversion, gap tracking |
| `validator.md` | ValidatorAgent | Schema validation, issue reporting |
| `repair_advisor.md` | RepairAdvisorAgent | Issue analysis, repair suggestion, confidence levels |

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

## Configuration

`FoundryClientConfig` controls the MAF connection:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endpoint` | `str \| None` | `None` | Azure AI Foundry project endpoint.  When `None` → offline mode. |
| `model` | `str` | `"gpt-4o"` | Model deployment name for agent LLM backing. |

## Agent Descriptions

| Agent | Responsibility | Tool Function |
|-------|---------------|--------------|
| **AnalyzerAgent** | Parse input, build IR, validate input | `analyze_mule_input` |
| **PlannerAgent** | Evaluate mapping availability, create plan | `create_migration_plan` |
| **TransformerAgent** | Generate Logic Apps artifacts from IR | `transform_to_logic_apps` |
| **ValidatorAgent** | Validate generated output artifacts | `validate_output_artifacts` |
| **RepairAdvisorAgent** | Suggest fixes for issues and gaps | `suggest_repairs` |

## Where Deterministic Logic Ends and AI Begins

- **Deterministic logic** lives in the service packages (`m2la_parser`,
  `m2la_ir`, `m2la_transform`, `m2la_validate`, `m2la_mapping_config`).
  These services parse XML, build data structures, generate JSON, and
  validate output — all with predictable, testable behaviour.

- **Agent orchestration** lives here in `m2la_agents`. Each agent has a rich
  system prompt and deterministic tool functions registered via `_get_tools()`.

- **AI-driven orchestration** happens in online mode. A `SequentialBuilder`
  workflow chains agents together, allowing each agent's LLM to reason about
  its task, invoke tool functions, and produce results for the next agent.
  The LLM adds reasoning, explanations, and recommendations on top of the
  deterministic tool outputs.

## Development

```bash
cd services/agents
uv sync
uv run pytest -v          # 126 tests
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
