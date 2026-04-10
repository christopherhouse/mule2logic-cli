# Architecture Overview

## Design Principles

The project is split into **two packages** designed for future separation:

- **`mule2logic_agent`** — The conversion engine. Stateless, no CLI dependencies. Can be deployed as a standalone container app / REST API.
- **`mule2logic_cli`** — A thin CLI shell. Handles terminal I/O, spinners, colours. Calls the agent package directly today; will switch to HTTP calls when the agent is deployed remotely.

The boundary between them is the `ConvertRequest` / `ConvertResult` data contract in `mule2logic_agent.models`.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Shell (mule2logic_cli)                                 │
│  ┌─────────────┐  ┌───────────────────┐  ┌───────────────┐ │
│  │ cli.py       │→│ commands/convert.py│→│ display.py     │ │
│  │ (argparse)   │  │ (orchestrator)    │  │ (colours/spin) │ │
│  └─────────────┘  └────────┬──────────┘  └───────────────┘ │
└─────────────────────────────┼───────────────────────────────┘
                              │ calls service.convert()
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent Package (mule2logic_agent)                           │
│                                                             │
│  service.py  ← PUBLIC API: convert(ConvertRequest)          │
│      │                                                      │
│      ├── core/io.py       Read file or stdin                │
│      ├── core/prompt.py   Load markdown templates           │
│      ├── core/agent.py    FoundryChatClient + Agent + MCP   │
│      ├── core/validate.py JSON parsing & structural checks  │
│      ├── core/review.py   QC review agent pass              │
│      └── core/report.py   Migration report agent pass       │
│                                                             │
│  models.py  ← ConvertRequest / ConvertResult contracts      │
│  prompts/   ← Markdown prompt templates                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
    ┌──────────────┐ ┌──────────┐ ┌─────────────────┐
    │ Azure AI     │ │ MS Learn │ │ Context7         │
    │ Foundry      │ │ MCP      │ │ MCP              │
    │ (model host) │ │ Server   │ │ Server           │
    └──────────────┘ └──────────┘ └─────────────────┘
```

## Module Responsibilities

### mule2logic_agent (the agent package)

#### `service.py`
- The **public API** of the agent. Exposes a single `convert()` async function.
- Orchestrates the full pipeline: prompt → agent → validate → review → report.
- Returns a `ConvertResult` dataclass.

#### `models.py`
- Defines `ConvertRequest` and `ConvertResult` — the data contract between CLI and agent.
- Designed to be serialisable to/from JSON for future REST API use.

#### `core/agent.py`
- Owns the `FoundryChatClient` and `Agent` lifecycle.
- Creates MCP tool connections (Microsoft Learn + Context7).
- Exposes `run_agent()` — a single async function that sends a prompt and returns text.

#### `core/prompt.py`
- Loads markdown prompt templates from the `prompts/` directory.
- Exports `SYSTEM_PROMPT`, `REVIEW_PROMPT`, `REPORT_SYSTEM_PROMPT` constants.
- Provides `build_prompt(xml)` and `build_report_prompt(xml, json)`.

#### `core/io.py`
- Reads MuleSoft XML from a file path or stdin.
- Validates that input is non-empty.

#### `core/validate.py`
- Strips markdown code fences and extracts JSON.
- Validates the Logic Apps workflow structure (`definition`, `triggers`, `actions`).
- Deep structural checks (runAfter refs, If/Foreach shape, etc.).

#### `core/review.py`
- Sends original XML + generated JSON through a second agent pass with a review-focused prompt.
- Returns the corrected workflow + remaining issues.

#### `core/report.py`
- Generates a Markdown migration-analysis report via a third agent pass.

### mule2logic_cli (the CLI shell)

#### `cli.py`
- Entry point. Uses `argparse` to define the `convert` subcommand and all flags.
- Delegates to `commands/convert.py`.

#### `commands/convert.py`
- CLI orchestrator. Reads input, calls `service.convert()`, formats output.
- Handles spinners, ANSI colours, file writing, `--explain`, `--pretty`, etc.

#### `display.py`
- ANSI colour helpers and terminal spinner.

## Data Flow

```
XML Input  →  io.py  →  prompt.py  →  agent.py  →  validate.py  →  review.py  →  report.py  →  Output
  (file         (read)    (build        (Agent        (parse &        (QC review    (migration    (JSON +
   or stdin)               prompt)       Framework     validate)       agent)        report)      report)
                                         + MCP)
```

## Error Flow

```
                          ┌──────────────┐
                          │ validate.py  │
                          │ returns error│
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │  Retry once  │
                          │ (agent.py)   │
                          └──────┬───────┘
                                 │
                      ┌──────────┴──────────┐
                      │                     │
               ┌──────▼───────┐    ┌────────▼────────┐
               │  Success     │    │  Fail again      │
               │  Output JSON │    │  Exit code 1     │
               └──────────────┘    └─────────────────┘
```

## Future: Agent as Container App

When the agent is deployed as a standalone container:

1. `mule2logic_agent` gets a thin HTTP wrapper (e.g., FastAPI) exposing `POST /convert` that accepts `ConvertRequest` JSON and returns `ConvertResult` JSON.
2. `mule2logic_cli` switches from `import service; service.convert(req)` to `httpx.post("http://agent-host/convert", json=req)`.
3. The `models.py` contract stays the same — it's the interface between them.
