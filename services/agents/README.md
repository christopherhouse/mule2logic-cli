# Agent Orchestration Service

**Multi-agent orchestration** layer for the MuleSoft → Logic Apps migration
platform, powered by the
[Azure AI Agents SDK](https://learn.microsoft.com/en-us/azure/ai-services/agents/)
(`azure-ai-agents`) and the
[ConnectedAgentTool](https://learn.microsoft.com/en-us/azure/foundry-classic/agents/how-to/connected-agents)
multi-agent pattern.

## Architecture Overview

The orchestrator implements true **multi-agent orchestration** where a main
orchestrator agent delegates to specialized sub-agents via the Azure AI Agent
Service.

Each sub-agent:
- Has rich **system prompts** (`prompts.py`) with domain-specific instructions
- Registers deterministic services as **`FunctionTool`** callables via `ToolSet`
- Is created on the Azure AI Agent Service via `AgentsClient.create_agent()`
- Is wired to the orchestrator as a **`ConnectedAgentTool`** for LLM-driven delegation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Azure AI Agent Service                         │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              MigrationOrchestrator Agent (main)                  │  │
│  │              Instructions: ORCHESTRATOR_PROMPT                    │  │
│  │              Tools: ConnectedAgentTool × 5 sub-agents           │  │
│  └──────────┬───────────┬───────────┬───────────┬──────────────────┘  │
│             │           │           │           │                      │
│    ┌────────▼──┐  ┌─────▼─────┐  ┌─▼──────────┐ ┌──▼───────┐         │
│    │ Analyzer  │  │  Planner  │  │ Transformer │ │Validator │  ┌────┐ │
│    │ Agent     │  │  Agent    │  │ Agent       │ │Agent     │  │Rep.│ │
│    │           │  │           │  │             │ │          │  │Adv.│ │
│    │ FuncTool: │  │ FuncTool: │  │ FuncTool:   │ │FuncTool: │  │    │ │
│    │ analyze   │  │ plan      │  │ transform   │ │validate  │  │    │ │
│    └─────┬─────┘  └─────┬─────┘  └──────┬─────┘ └────┬─────┘  └──┬─┘ │
│          │              │               │             │            │   │
│  ┌───────▼──────────────▼───────────────▼─────────────▼────────────▼─┐ │
│  │                    Deterministic Services                         │ │
│  │  m2la_parser │ m2la_ir │ m2la_transform │ m2la_validate │ config  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

Thread: user message → orchestrator reasons → delegates to sub-agents →
        sub-agents invoke FunctionTools → orchestrator compiles response
```

## Multi-Agent Orchestration (Online Mode)

In online mode, the orchestrator creates a proper multi-agent setup:

1. **Create sub-agents** — Each agent (`AnalyzerAgent`, `PlannerAgent`, etc.)
   is created on the Azure AI Agent Service with its `FunctionTool` and
   domain-specific system prompt.

2. **Wire as ConnectedAgentTool** — Sub-agents are registered as
   `ConnectedAgentTool` definitions on the main orchestrator agent, enabling
   the LLM to delegate tasks via natural language routing.

3. **Create orchestrator agent** — A main `MigrationOrchestrator` agent is
   created with the `ORCHESTRATOR_PROMPT` and connected sub-agents as tools.

4. **Thread + message** — A conversation thread is created with a rich user
   message describing the migration request (input path, mode, correlation ID).

5. **Run** — The orchestrator agent run is executed. The LLM reasons about the
   migration pipeline, delegates to sub-agents, and compiles results.

6. **Structured output** — The deterministic `execute()` path is also run
   to produce structured `AgentResult` objects. The LLM's reasoning is
   attached as `orchestrator_reasoning` in the final output.

7. **Cleanup** — All agents (orchestrator + sub-agents) are deleted from the
   service.

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

# LLM reasoning from the orchestrator agent
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

Each agent has a rich, domain-specific system prompt in `prompts.py`:

| Prompt | Agent | Purpose |
|--------|-------|---------|
| `ORCHESTRATOR_PROMPT` | Main orchestrator | Pipeline coordination, delegation rules, output format |
| `ANALYZER_PROMPT` | AnalyzerAgent | Input parsing, IR building, validation reporting |
| `PLANNER_PROMPT` | PlannerAgent | Mapping evaluation, plan generation, gap estimation |
| `TRANSFORMER_PROMPT` | TransformerAgent | IR→Logic Apps conversion, gap tracking |
| `VALIDATOR_PROMPT` | ValidatorAgent | Schema validation, issue reporting |
| `REPAIR_ADVISOR_PROMPT` | RepairAdvisorAgent | Issue analysis, repair suggestion, confidence levels |

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

`AgentsClientConfig` controls the SDK connection:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endpoint` | `str \| None` | `None` | Azure AI Foundry project endpoint.  When `None` → offline mode. |
| `model_deployment` | `str` | `"gpt-4o"` | Model deployment name for agent LLM backing. |

## Agent Descriptions

| Agent | Responsibility | FunctionTool | ConnectedAgentTool Description |
|-------|---------------|-------------|-------------------------------|
| **AnalyzerAgent** | Parse input, build IR, validate input | `analyze_mule_input` | "Parses and analyzes MuleSoft input..." |
| **PlannerAgent** | Evaluate mapping availability, create plan | `create_migration_plan` | "Evaluates mapping availability..." |
| **TransformerAgent** | Generate Logic Apps artifacts from IR | `transform_to_logic_apps` | "Converts the MuleSoft IR into Logic Apps..." |
| **ValidatorAgent** | Validate generated output artifacts | `validate_output_artifacts` | "Validates generated Logic Apps artifacts..." |
| **RepairAdvisorAgent** | Suggest fixes for issues and gaps | `suggest_repairs` | "Analyzes validation failures and migration gaps..." |

## Where Deterministic Logic Ends and AI Begins

- **Deterministic logic** lives in the service packages (`m2la_parser`,
  `m2la_ir`, `m2la_transform`, `m2la_validate`, `m2la_mapping_config`).
  These services parse XML, build data structures, generate JSON, and
  validate output — all with predictable, testable behaviour.

- **Agent orchestration** lives here in `m2la_agents`. Each agent has a rich
  system prompt and deterministic `FunctionTool` callables.

- **AI-driven orchestration** happens in online mode. The main orchestrator
  agent uses LLM reasoning to delegate to sub-agents via `ConnectedAgentTool`,
  coordinate the pipeline, and produce a coherent migration summary. The LLM
  adds reasoning, explanations, and recommendations on top of the deterministic
  tool outputs.

## Development

```bash
cd services/agents
uv sync
uv run pytest -v          # 142 tests
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
