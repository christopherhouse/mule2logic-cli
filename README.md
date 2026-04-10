<div align="center">

# 🔄 mule2logic-cli

**Migrate MuleSoft flows → Azure Logic Apps Standard workflows with AI ✨**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Agent Framework](https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?logo=microsoftazure&logoColor=white)](https://learn.microsoft.com/agent-framework/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/christopherhouse/mule2logic-cli/pulls)
[![Experimental](https://img.shields.io/badge/Status-Experimental-orange)]()

<br />

<img src="https://img.shields.io/badge/MuleSoft%20XML-→-blue?style=for-the-badge" alt="" /> <img src="https://img.shields.io/badge/Azure%20Logic%20Apps%20JSON-✔-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" alt="" />

<br />

*Drop in your MuleSoft XML, get back Logic Apps JSON. A starting point, not a finished product.* 🧪

</div>

---

## ⚠️ Disclaimer

> **This project is experimental and under active development.** It uses AI (Microsoft Agent Framework + Azure Foundry) to generate Logic Apps JSON from MuleSoft XML. AI-generated output can be incorrect, incomplete, or subtly wrong. **Do not deploy the output to production without thorough manual review and testing.** There are no guarantees that any conversion is correct. Use at your own risk.

## 🤔 What is this?

`mule2logic` is an experimental Python CLI that uses the **Microsoft Agent Framework SDK** — grounded with [Microsoft Learn MCP](https://learn.microsoft.com/api/mcp) and [Context7 MCP](https://mcp.context7.com) — to convert MuleSoft XML flow definitions into Azure Logic Apps Standard workflow JSON.

The tool *attempts* to handle a wide range of MuleSoft components: connectors, processors, routers, scopes, error handlers, DataWeave transformations, and enterprise integration patterns. A built-in QC review agent does a second pass on every conversion, but this is best-effort — **always review the output yourself**.

> **Architecture note:** The project is split into two packages — `mule2logic_agent` (the conversion engine) and `mule2logic_cli` (the thin CLI shell). This design enables future deployment of the agent as a standalone container app / API service.

### 🧩 MuleSoft → Logic Apps Coverage (Aspirational)

The tables below show the mappings the tool *attempts*. Coverage varies — simple flows tend to convert well, complex ones may need manual fixes.

<details>
<summary><strong>Triggers — Inbound Endpoints</strong></summary>

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `http:listener` | Request trigger (Http) |
| `scheduler` / `poll` / cron | Recurrence trigger |
| `jms:listener` / `amqp:listener` | Service Bus trigger |
| `file:listener` / `ftp:listener` / `sftp:listener` | File/FTP/SFTP connector trigger |
| `email:listener-imap` / `email:listener-pop3` | Office 365 Outlook trigger |
| `vm:listener` | Service Bus / Storage Queue trigger |
| `salesforce:replay-topic-listener` | Salesforce connector trigger |
| `db:listener` (polling) | Recurrence + SQL query polling |
| APIkit router (`apikit:router`) | Request trigger + condition routing |
| Sub-flows (no inbound endpoint) | Child workflow or inline actions |

</details>

<details>
<summary><strong>Core Processors</strong></summary>

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `set-payload` | Compose action |
| `set-variable` / `remove-variable` | InitializeVariable / SetVariable |
| `logger` | Compose action |
| `raise-error` | Terminate action |
| `transform-message` (DataWeave) | Compose with expressions or Inline Code (JS) |
| `object-to-json` / `json-to-object` | Parse JSON / Compose |
| `object-to-xml` / `xml-to-object` | XML composition / XML Validation |
| `expression-component` | Compose or Inline Code (JS) |

</details>

<details>
<summary><strong>Flow Control & Routers</strong></summary>

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `choice` / `when` / `otherwise` | If or Switch action |
| `foreach` | Foreach action |
| `parallel-foreach` | Foreach (parallel concurrency) |
| `scatter-gather` | Parallel branches via shared `runAfter` |
| `first-successful` | Chained scopes with failure `runAfter` |
| `until-successful` | Until action or `retryPolicy` |
| `flow-ref` | Inlined actions or HTTP call to child workflow |

</details>

<details>
<summary><strong>Error Handling</strong></summary>

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `try` scope | Scope action |
| `on-error-continue` | `runAfter: { "Scope": ["Failed"] }` — continues |
| `on-error-propagate` | `runAfter` on failure + Terminate |
| Error type matching | Conditions checking `@result('ScopeName')` |

</details>

<details>
<summary><strong>Connectors & Outbound Operations</strong></summary>

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `http:request` | HTTP action |
| `db:select` / `db:insert` / `db:update` / `db:delete` | SQL connector actions |
| `salesforce:create` / `query` / `update` / `delete` | Salesforce connector actions |
| `email:send` | Office 365 Outlook Send action |
| `file:*` / `ftp:*` / `sftp:*` | Blob/File/FTP/SFTP connector actions |
| `jms:*` / `amqp:*` | Service Bus connector actions |
| `web-service-consumer` (SOAP) | HTTP action with SOAP envelope |
| `os:store` / `os:retrieve` (ObjectStore) | Table Storage / Redis actions |
| `batch:job` / `batch:step` | Foreach with batching |
| `crypto:*` | Inline Code (JS) or Key Vault connector |
| `validation:*` | Condition actions |

</details>

<details>
<summary><strong>Enterprise Patterns</strong></summary>

Content-based routing, message enrichment, splitter/aggregator, idempotent filtering, correlation IDs, retry/circuit breaker, and watermark polling are attempted where detected in the source XML.

</details>

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.12+** — [Download](https://www.python.org/downloads/)
- **Azure AI Foundry project** — with a deployed model (e.g., `gpt-4o`)
- **Azure CLI** — logged in via `az login` (for authentication)

### Environment Variables

```bash
export FOUNDRY_PROJECT_ENDPOINT="https://your-project.services.ai.azure.com"
export FOUNDRY_MODEL="gpt-4o"  # optional, defaults to gpt-4o
```

### Installation

#### Option 1: Install from source (editable)

```bash
git clone https://github.com/christopherhouse/mule2logic-cli.git
cd mule2logic-cli

# Install uv if you don't have it (https://docs.astral.sh/uv/)
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates venv automatically)
uv sync

# Now available:
uv run mule2logic convert flow.xml --pretty
```

#### Option 2: Install directly via uv

```bash
uv tool install mule2logic
mule2logic convert flow.xml --pretty
```

---

## 🚀 Usage

### Basic conversion

```bash
mule2logic convert flow.xml
```

### Pipe XML from stdin

```bash
cat flow.xml | mule2logic convert
```

### Save to a file with pretty-printing

```bash
mule2logic convert flow.xml --output workflow.json --pretty
```

### Get an AI explanation of the conversion

```bash
mule2logic convert flow.xml --explain --pretty
```

### Use a different model

```bash
mule2logic convert flow.xml --model gpt-4.1
```

### Generate a migration analysis report

```bash
mule2logic convert flow.xml --output workflow.json --report migration-report.md
```

### Skip the QC review agent

```bash
mule2logic convert flow.xml --no-review
```

### Increase timeout for large flows

```bash
mule2logic convert big-flow.xml --timeout 600
```

### 🎛️ All CLI Flags

| Flag | Description |
|---|---|
| `--output <file>` | 📁 Write JSON to a file instead of stdout |
| `--report <file>` | 📊 Write a migration analysis report (Markdown) to a file |
| `--explain` | 💡 Include an AI-generated explanation of the conversion |
| `--pretty` | 🎨 Pretty-print the JSON output (2-space indent) |
| `--verbose` | 🔍 Print debug information to stderr |
| `--debug` | 🐛 Dump raw agent response to stderr |
| `--model <model>` | 🧠 Foundry model deployment name (default: `gpt-4o`) |
| `--timeout <seconds>` | ⏱️ Timeout per agent call in seconds (default: `300`) |
| `--no-review` | ⏭️ Skip the QC review agent step |

---

## 📖 Example

**Input** — `hello-flow.xml`:
```xml
<flow name="test">
  <http:listener path="/hello"/>
  <set-payload value="Hello"/>
</flow>
```

**Command:**
```bash
mule2logic convert hello-flow.xml --pretty
```

**Output:**
```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "triggers": {
      "manual": {
        "type": "Request",
        "kind": "Http",
        "inputs": {
          "method": "GET",
          "relativePath": "/hello"
        }
      }
    },
    "actions": {
      "Set_Hello": {
        "type": "Compose",
        "inputs": "Hello",
        "runAfter": {}
      }
    }
  }
}
```

**With `--report`**, you also get a Markdown analysis file covering migration scope, confidence assessment, known gaps, and next steps.

---

## 🏗️ Architecture

```
                    ┌──────────────────────┐
XML Input  →  io.py  →  prompt.py  →  agent.py  →  validate.py  →  review.py  →  report.py  →  Output
 (file          (read)    (build       (Agent        (parse &        (QC review    (migration    (JSON +
  or stdin)                prompt)      Framework     validate)       agent)        report)      report)
                                        + MCP)
```

The project is split into **two packages** for future separation:

### `mule2logic_agent` — The Agent (deployable independently)

The conversion engine. Contains all AI logic, prompt templates, validation, and MCP integration. Designed to be deployed as a container app / API service.

- **`core/agent.py`** — `FoundryChatClient` + `Agent` lifecycle, MCP tool wiring
- **`core/prompt.py`** — Loads markdown prompt templates, injects XML
- **`core/validate.py`** — JSON parsing, structural validation
- **`core/review.py`** — QC review agent pass
- **`core/report.py`** — Migration report agent pass
- **`core/io.py`** — File/stdin reader
- **`service.py`** — High-level `convert()` function (the public API)
- **`models.py`** — `ConvertRequest` / `ConvertResult` data contracts

### `mule2logic_cli` — The CLI Shell

A thin CLI that calls into the agent package. When the agent is deployed remotely, this package will switch to HTTP calls instead of direct imports.

- **`cli.py`** — argparse entry point
- **`commands/convert.py`** — Pipeline orchestrator with spinners / colours
- **`display.py`** — ANSI colour and spinner helpers

> If validation fails on the conversion step, the tool **retries once** automatically.

For a deep dive, check out the [Architecture doc](docs/architecture.md).

---

## 📂 Project Structure

```
mule2logic-cli/
├── src/
│   ├── mule2logic_agent/             # Agent package (deployable independently)
│   │   ├── __init__.py
│   │   ├── models.py                 # ConvertRequest / ConvertResult contracts
│   │   ├── service.py                # High-level convert() API
│   │   ├── core/
│   │   │   ├── agent.py              # FoundryChatClient + Agent + MCP tools
│   │   │   ├── prompt.py             # Prompt template loader
│   │   │   ├── io.py                 # File and stdin reader
│   │   │   ├── validate.py           # JSON structure validator
│   │   │   ├── review.py             # QC review agent
│   │   │   └── report.py             # Migration report generator
│   │   └── prompts/
│   │       ├── system.prompt.md      # System prompt (conversion rules)
│   │       ├── user.prompt.md        # User prompt template
│   │       ├── review.prompt.md      # Review agent system prompt
│   │       ├── report.prompt.md      # Report agent system prompt
│   │       └── report.user.prompt.md # Report user prompt template
│   └── mule2logic_cli/               # CLI package (thin shell)
│       ├── __init__.py
│       ├── cli.py                    # argparse entry point
│       ├── display.py                # ANSI colours and spinners
│       └── commands/
│           └── convert.py            # Convert command orchestrator
├── tests/
│   ├── test_validate.py
│   ├── test_prompt.py
│   ├── test_io.py
│   ├── test_agent.py
│   ├── test_review.py
│   ├── test_convert.py
│   └── fixtures/
│       ├── simple-flow.xml
│       ├── not-simple-flow.xml
│       └── even-less-simple-flow.xml
├── docs/
│   ├── mule2logic-cli-spec-v2.md
│   ├── architecture.md
│   └── test-cases.md
├── pyproject.toml
└── LICENSE
```

---

## 🧪 Testing

Tests use **pytest** via **uv**:

```bash
uv sync
uv run pytest
```

Test coverage includes:

- ✅ End-to-end conversion pipeline (mocked agent)
- ✅ Pretty-print, explain, and output-to-file flags
- ✅ Missing file and empty input error handling
- ✅ Agent Framework client lifecycle and MCP tool setup
- ✅ Prompt building and template loading
- ✅ JSON validation and structural checks
- ✅ Review agent workflow
- ✅ Migration report generation

See [test-cases.md](docs/test-cases.md) for full details.

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| 📄 Missing file | Friendly error message → exit code `1` |
| 📭 Empty input | Friendly error message → exit code `1` |
| ❌ Invalid JSON from AI | Retry once automatically |
| ❌❌ Retry also fails | Error message → exit code `1` |
| ⏱️ Timeout | Configurable via `--timeout` (default 300s) |
| 🔍 Review agent fails | Falls back to original conversion output |

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```
3. **Make your changes** and add tests
4. **Run the tests** to make sure everything passes:
   ```bash
   uv sync
   uv run pytest
   ```
5. **Open a Pull Request** 🎉

### Development Resources

- **[Product Spec](docs/mule2logic-cli-spec-v2.md)** — The source of truth for all features
- **[Architecture](docs/architecture.md)** — How the pieces fit together
- **[Test Cases](docs/test-cases.md)** — What needs to be tested

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 💬 Questions & Feedback

Got an idea? Found a bug? 🐛

- **[Open an Issue](https://github.com/christopherhouse/mule2logic-cli/issues)** — We'd love to hear from you!

---

<div align="center">

Made with ❤️ and a healthy dose of AI

**[⬆ Back to top](#-mule2logic-cli)**

</div>
