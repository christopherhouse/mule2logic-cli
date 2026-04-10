# Copilot Instructions for mule2logic-cli

## ⚠️ Obsolete TypeScript Implementation

The `src/tsx/` directory contains an **obsolete** Node.js/TypeScript implementation. **Do not modify, extend, or reference it.** All active development uses the Python implementation under `src/python/`. Ignore `package.json`, `tsconfig.json`, and `package-lock.json` — they are legacy artifacts.

## Project Overview

`mule2logic` is a Python CLI that converts MuleSoft XML flows into deployable Azure Logic Apps Standard workflow JSON. It is powered by the **Microsoft Agent Framework SDK for Python** (`agent-framework` + `agent-framework-foundry`), grounded with **Microsoft Learn MCP** and **Context7 MCP** tool servers via Azure AI Foundry.

The project is split into two packages designed for future separation:

- **`mule2logic_agent`** — The conversion engine. Stateless, no CLI dependencies. Can be deployed as a standalone container app or REST API.
- **`mule2logic_cli`** — A thin CLI shell. Handles terminal I/O, spinners, colours. Calls the agent package directly today; will switch to HTTP calls when the agent is deployed remotely.

The boundary between them is the `ConvertRequest` / `ConvertResult` data contract in `mule2logic_agent.models`.

## Key References

- **Product spec:** `docs/mule2logic-cli-spec-v2.md` — the source of truth for all features.
- **Architecture:** `docs/architecture.md` — how the pieces fit together.
- **Test cases:** `docs/test-cases.md` — structured test case definitions.
- **Agent Framework docs:** <https://learn.microsoft.com/agent-framework/overview/agent-framework-overview>
- **Foundry Python provider:** <https://learn.microsoft.com/agent-framework/agents/providers/microsoft-foundry>

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Build system | setuptools (via `pyproject.toml`) |
| AI framework | Microsoft Agent Framework SDK (`agent-framework`, `agent-framework-foundry`) |
| Authentication | `azure-identity` (`AzureCliCredential`) |
| CLI framework | `argparse` (stdlib) |
| Testing | `pytest` + `pytest-asyncio` |
| MCP servers | Microsoft Learn (`https://learn.microsoft.com/api/mcp`), Context7 (`https://mcp.context7.com/mcp`) |

## Project Structure

```
mule2logic-cli/
├── src/python/
│   ├── mule2logic_agent/              # Agent package (deployable independently)
│   │   ├── __init__.py
│   │   ├── models.py                  # ConvertRequest / ConvertResult dataclasses
│   │   ├── service.py                 # High-level convert() API — the public entry-point
│   │   ├── core/
│   │   │   ├── agent.py               # FoundryChatClient + Agent + MCP tool wiring
│   │   │   ├── prompt.py              # Markdown prompt template loader
│   │   │   ├── io.py                  # File and stdin reader
│   │   │   ├── validate.py            # JSON parsing and structural validation
│   │   │   ├── review.py              # QC review agent pass
│   │   │   └── report.py              # Migration report agent pass
│   │   └── prompts/                   # Markdown prompt templates (packaged as data)
│   │       ├── system.prompt.md
│   │       ├── user.prompt.md
│   │       ├── review.prompt.md
│   │       ├── report.prompt.md
│   │       └── report.user.prompt.md
│   └── mule2logic_cli/               # CLI package (thin shell)
│       ├── __init__.py
│       ├── cli.py                     # argparse entry point
│       ├── display.py                 # ANSI colour and spinner helpers
│       └── commands/
│           └── convert.py             # Convert command orchestrator
├── tests/                             # All tests (pytest)
│   ├── test_validate.py
│   ├── test_prompt.py
│   ├── test_io.py
│   ├── test_agent.py
│   ├── test_review.py
│   ├── test_convert.py
│   └── fixtures/                      # MuleSoft XML test fixtures
│       ├── simple-flow.xml
│       ├── not-simple-flow.xml
│       └── even-less-simple-flow.xml
├── docs/
│   ├── mule2logic-cli-spec-v2.md
│   ├── architecture.md
│   └── test-cases.md
├── pyproject.toml                     # Project config, dependencies, pytest settings
├── uv.lock                            # Lockfile (committed, do not edit manually)
├── src/tsx/                           # ⛔ OBSOLETE — do not modify
└── LICENSE
```

## Environment Setup and Build Commands

Always use `uv` to manage dependencies and run commands. Never use raw `pip` or `python` directly.

```bash
# Install all dependencies (creates .venv automatically)
uv sync

# Run the CLI
uv run mule2logic convert <file.xml> --pretty

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_validate.py

# Run tests with verbose output
uv run pytest -v

# Run tests matching a keyword
uv run pytest -k "test_parses_valid"
```

### Required Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint URL |
| `FOUNDRY_MODEL` | No | Model deployment name (defaults to `gpt-4o`) |

Authentication is via `az login` (Azure CLI credential).

## CLI Contract

```bash
mule2logic convert <input> [options]
cat flow.xml | mule2logic convert [options]
```

| Flag | Description |
|---|---|
| `--output <file>` | Write JSON to file instead of stdout |
| `--report <file>` | Write migration analysis report (Markdown) to file |
| `--explain` | Include AI-generated explanation alongside the workflow |
| `--pretty` | Pretty-print the JSON output (2-space indent) |
| `--verbose` | Emit debug information to stderr |
| `--debug` | Dump raw agent response to stderr |
| `--model <model>` | Foundry model deployment name (default: `gpt-4o`) |
| `--timeout <seconds>` | Timeout per agent call in seconds (default: `300`) |
| `--no-review` | Skip the QC review agent step |

## Output Format

### Default output

```json
{
  "definition": {
    "triggers": {},
    "actions": {}
  }
}
```

### With `--explain` flag

```json
{
  "workflow": { "definition": { "triggers": {}, "actions": {} } },
  "explanation": "..."
}
```

## Python Coding Conventions

### General

- Target **Python 3.12+**. Use modern syntax: `type` unions (`X | Y`), `from __future__ import annotations`, `match` statements where appropriate.
- Use **type hints** on all function signatures and class attributes.
- Use **`dataclasses`** for data models (see `models.py`). Do not use Pydantic unless explicitly required.
- Use **`pathlib.Path`** instead of `os.path` for file operations.
- Use **`async/await`** for all I/O and agent calls. The agent framework is async-first.
- Keep modules small and single-purpose. Each file in `core/` has one job.
- Do not over-engineer. Keep it simple and match the spec exactly.
- Do not add features not listed in the spec.

### Imports

- Use **absolute imports** throughout: `from mule2logic_agent.core.agent import run_agent`.
- Group imports in the standard order: stdlib → third-party → local.
- Use `from __future__ import annotations` at the top of every module for forward-reference support.

### Async Patterns

- All agent interactions go through `run_agent()` in `core/agent.py`. This is the single point of contact with the Agent Framework.
- Use `asyncio.wait_for()` for timeout enforcement on agent calls.
- Use `async with` for credential and agent lifecycle management (`AzureCliCredential`, `Agent`).
- The CLI bridges sync → async via `asyncio.run()` in `commands/convert.py`.

### Agent Framework Patterns

The project uses the **`FoundryChatClient` + `Agent`** pattern from the Microsoft Agent Framework SDK:

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential

async with AzureCliCredential() as credential:
    client = FoundryChatClient(
        project_endpoint=endpoint,
        model=model,
        credential=credential,
    )
    # Wire up MCP tool servers
    learn_mcp = client.get_mcp_tool(
        name="Microsoft Learn MCP",
        url="https://learn.microsoft.com/api/mcp",
        approval_mode="never_require",
    )
    context7_mcp = client.get_mcp_tool(
        name="Context7 MCP",
        url="https://mcp.context7.com/mcp",
        approval_mode="never_require",
    )
    async with Agent(
        client=client,
        name="MuleSoftConverter",
        instructions=system_prompt,
        tools=[learn_mcp, context7_mcp],
    ) as agent:
        result = await agent.run(prompt)
```

Key rules:
- `FoundryChatClient` is the Foundry-first path — use it when the app owns instructions and tools.
- MCP tools are wired via `client.get_mcp_tool()` and passed to the `Agent` constructor.
- Agent lifecycle is managed with `async with`.
- Use `azure.identity.aio.AzureCliCredential` (the async version) for credential management.

### Error Handling

| Case | Behavior |
|---|---|
| Missing file | Friendly error message → `sys.exit(1)` |
| Empty input | Friendly error message → `sys.exit(1)` |
| Invalid JSON from AI | Retry agent call once automatically |
| Retry also fails | Error message → `sys.exit(1)` |
| Timeout | Configurable via `--timeout` (default 300s) |
| Review agent fails | Falls back to original conversion output (non-fatal) |

- Use `sys.exit(1)` for fatal errors.
- Always print user-friendly error messages to stderr before exiting.
- Raise `ValueError` for validation failures, `FileNotFoundError` for missing files, `RuntimeError` for configuration errors.

### Validation Rules

The `validate.py` module checks that agent output:
1. Is parseable as JSON (strips markdown code fences and extracts `{…}` blocks first).
2. Contains a `definition` object at the top level.
3. Contains `definition.triggers` (dict).
4. Contains `definition.actions` (dict).

The `validate_workflow_structure()` function performs deeper checks:
- All triggers and actions have a `type` field.
- `runAfter` references point to existing actions.
- `If` actions have an `expression`.
- `Foreach` actions have a `foreach` input and nested `actions`.

### Prompts

- Prompt templates are **Markdown files** in `src/python/mule2logic_agent/prompts/`.
- They are loaded at module import time by `core/prompt.py` and exposed as constants: `SYSTEM_PROMPT`, `REVIEW_PROMPT`, `REPORT_SYSTEM_PROMPT`.
- `build_prompt(xml)` and `build_report_prompt(xml, json_str)` inject content into the user prompt templates.
- Prompts are packaged as data via `[tool.setuptools.package-data]` in `pyproject.toml`.

## Testing

### Framework and Configuration

- Test framework: **pytest** with **pytest-asyncio** for async test support.
- Configuration is in `pyproject.toml` under `[tool.pytest.ini_options]`:
  - `testpaths = ["tests"]`
  - `asyncio_mode = "auto"` — async tests are detected automatically without explicit marks in most cases.
- Always run tests with: `uv run pytest`

### Test Organization

Tests mirror the source structure:

| Test file | Module under test |
|---|---|
| `tests/test_validate.py` | `mule2logic_agent.core.validate` |
| `tests/test_prompt.py` | `mule2logic_agent.core.prompt` |
| `tests/test_io.py` | `mule2logic_agent.core.io` |
| `tests/test_agent.py` | `mule2logic_agent.core.agent` |
| `tests/test_review.py` | `mule2logic_agent.core.review` |
| `tests/test_convert.py` | `mule2logic_cli.commands.convert` (integration) |

### Writing Tests

- Use **`pytest` classes** to group related tests (e.g., `class TestValidateJson:`).
- Mark async tests with `@pytest.mark.asyncio` on classes or individual tests.
- Use **`unittest.mock`** for mocking: `patch`, `AsyncMock`, `MagicMock`.
- Mock all external dependencies (Agent Framework, Azure credentials) — never make real API calls in tests.
- Use `pytest.raises` for asserting expected exceptions.
- Use `tmp_path` fixture for temporary file operations.
- Use `capsys` fixture to capture stdout/stderr output.

### Mocking the Agent Framework

Agent tests mock three things:
1. **`AzureCliCredential`** — mock the async context manager.
2. **`FoundryChatClient`** — mock `get_mcp_tool()` to return a `MagicMock`.
3. **`Agent`** — mock as an async context manager whose `.run()` returns a fake result with a `.text` attribute.

Use `@patch.dict("os.environ", {"FOUNDRY_PROJECT_ENDPOINT": "https://fake.endpoint"})` to provide required env vars in tests.

### Test Fixtures

- XML fixture files live in `tests/fixtures/`.
- Access fixtures via `Path(__file__).parent / "fixtures" / "filename.xml"`.
- When adding new MuleSoft conversion scenarios, add a corresponding XML fixture file.

### Running Tests

```bash
# All tests
uv run pytest

# Verbose with full tracebacks
uv run pytest -v --tb=long

# Single file
uv run pytest tests/test_validate.py

# Single test class or method
uv run pytest tests/test_validate.py::TestValidateJson::test_parses_valid_json

# With keyword filter
uv run pytest -k "review"
```

Always run the full test suite before committing changes. All tests must pass.

## Agentic Development Best Practices

- **Single responsibility per agent call.** Each agent invocation (convert, review, report) has a dedicated system prompt and a single focused task.
- **Retry on validation failure.** If the agent returns invalid JSON, retry once before failing. This is implemented in `service.py`.
- **Non-fatal fallbacks.** Review and report agent failures are non-fatal — the pipeline falls back gracefully to the original output.
- **Timeout enforcement.** Every agent call is wrapped in `asyncio.wait_for()` with a configurable timeout.
- **Encapsulated agent wiring.** All Foundry / MCP setup is in `core/agent.py`. Swapping providers requires changes in that one file only.
- **Separation of concerns.** Prompts are Markdown templates, not hardcoded strings. Validation is a distinct module. The CLI shell knows nothing about AI.
- **Testability.** The `run_agent()` function is the only external dependency. Mock it to test everything else in isolation.

## Data Flow

```
XML Input → io.py → prompt.py → agent.py → validate.py → review.py → report.py → Output
 (file       (read)   (build     (Agent      (parse &      (QC review   (migration   (JSON +
  or stdin)            prompt)    Framework    validate)     agent)       report)      report)
                                 + MCP)
```

## MuleSoft-to-Logic Apps Mapping Reference

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `http:listener` | Request trigger (Http) |
| `scheduler` / `poll` | Recurrence trigger |
| `set-payload` | Compose action |
| `set-variable` / `remove-variable` | InitializeVariable / SetVariable |
| `logger` | Compose action |
| `choice` / `when` / `otherwise` | Condition (If) or Switch action |
| `foreach` | Foreach action |
| `parallel-foreach` | Foreach (parallel concurrency) |
| `scatter-gather` | Parallel branches via shared `runAfter` |
| `try` scope | Scope action |
| `on-error-continue` | `runAfter: { "Scope": ["Failed"] }` |
| `on-error-propagate` | `runAfter` on failure + Terminate |
| `http:request` | HTTP action |
| `db:select` / `db:insert` / etc. | SQL connector actions |
| `flow-ref` | Inlined actions or HTTP call to child workflow |
| `transform-message` (DataWeave) | Compose with expressions or Inline Code (JS) |
| `raise-error` | Terminate action |
| `flow` | Workflow definition wrapper |

## Non-Goals

- No Azure deployment functionality.
- No deep JSON Schema validation beyond structural checks.
- No graphical UI.
- No modifications to the obsolete TypeScript code in `src/tsx/`.
