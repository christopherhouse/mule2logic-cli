<div align="center">

# 🔄 mule2logic-cli

**Migrate MuleSoft flows → Azure Logic Apps Standard workflows with AI ✨**

[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Copilot](https://img.shields.io/badge/Powered%20by-GitHub%20Copilot-8957e5?logo=github)](https://github.com/features/copilot)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/christopherhouse/mule2logic-cli/pulls)
[![Experimental](https://img.shields.io/badge/Status-Experimental-orange)]()

<br />

<img src="https://img.shields.io/badge/MuleSoft%20XML-→-blue?style=for-the-badge" alt="" /> <img src="https://img.shields.io/badge/Azure%20Logic%20Apps%20JSON-✔-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" alt="" />

<br />

*Drop in your MuleSoft XML, get back Logic Apps JSON. A starting point, not a finished product.* 🧪

</div>

---

## ⚠️ Disclaimer

> **This project is experimental and under active development.** It uses AI (GitHub Copilot SDK) to generate Logic Apps JSON from MuleSoft XML. AI-generated output can be incorrect, incomplete, or subtly wrong. **Do not deploy the output to production without thorough manual review and testing.** There are no guarantees that any conversion is correct. Use at your own risk.

## 🤔 What is this?

`mule2logic` is an experimental Node.js CLI that uses the **GitHub Copilot SDK** — grounded with [Microsoft Learn MCP](https://learn.microsoft.com/api/mcp) and [Context7 MCP](https://mcp.context7.com) — to convert MuleSoft XML flow definitions into Azure Logic Apps Standard workflow JSON.

The tool *attempts* to handle a wide range of MuleSoft components: connectors, processors, routers, scopes, error handlers, DataWeave transformations, and enterprise integration patterns. A built-in QC review agent does a second pass on every conversion, but this is best-effort — **always review the output yourself**.

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

- **Node.js 18+** — [Download](https://nodejs.org/)
- **GitHub Copilot SDK access** — needed for AI-powered conversion

### Installation

```bash
# Clone the repo
git clone https://github.com/christopherhouse/mule2logic-cli.git
cd mule2logic-cli

# Install dependencies
npm install

# Link the CLI globally
npm link
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

### Skip the QC review agent

```bash
mule2logic convert flow.xml --no-review
```

### Increase timeout for large flows

```bash
mule2logic convert big-flow.xml --timeout 600000
```

### 🎛️ All CLI Flags

| Flag | Description |
|---|---|
| `--output <file>` | 📁 Write JSON to a file instead of stdout |
| `--explain` | 💡 Include an AI-generated explanation of the conversion |
| `--pretty` | 🎨 Pretty-print the JSON output (2-space indent) |
| `--verbose` | 🔍 Print debug information to stderr |
| `--debug` | 🐛 Dump raw Copilot response to stderr |
| `--model <model>` | 🧠 Model to use (default: `claude-opus-4.6`) |
| `--timeout <ms>` | ⏱️ Timeout per Copilot call in ms (default: `300000`) |
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
        "inputs": "Hello"
      }
    }
  }
}
```

---

## 🏗️ Architecture

```
                    ┌──────────────┐
XML Input  →  io.js  →  prompt.js  →  copilot.js  →  validate.js  →  review.js  →  JSON Output
 (file          (read)    (build        (Copilot SDK    (parse &        (QC review    (stdout
  or stdin)                prompt)       + MCP servers)   validate)       agent)        or file)
```

The CLI follows a pipeline with a **two-pass AI architecture**:

1. **📥 Load** — Read MuleSoft XML from a file or stdin (`io.js`)
2. **📝 Prompt** — Build structured prompts from markdown templates (`prompt.js` + `prompts/`)
3. **🤖 Convert** — Send to GitHub Copilot SDK, grounded via Microsoft Learn MCP (Logic Apps schema) and Context7 MCP (MuleSoft docs) (`copilot.js`)
4. **✅ Validate** — Ensure the response is valid Logic Apps JSON with structural checks (`validate.js`)
5. **🔍 Review** — A second AI pass validates semantic correctness, checks for dropped elements, and fixes issues (`review.js`)
6. **📤 Output** — Write to stdout or a file

> If validation fails on step 4, the tool **retries once** automatically.

For a deep dive, check out the [Architecture doc](docs/architecture.md).

---

## 📂 Project Structure

```
mule2logic-cli/
├── src/
│   ├── cli.js                 # CLI entry point (commander)
│   ├── commands/
│   │   └── convert.js         # Conversion pipeline orchestrator
│   ├── core/
│   │   ├── copilot.js         # Copilot SDK + MCP server client
│   │   ├── prompt.js          # Prompt template loader
│   │   ├── io.js              # File and stdin reader
│   │   ├── validate.js        # JSON structure validator
│   │   └── review.js          # QC review agent
│   └── prompts/
│       ├── system.prompt.md   # System prompt (conversion rules)
│       ├── user.prompt.md     # User prompt template
│       └── review.prompt.md   # Review agent system prompt
├── test/
│   ├── *.test.js              # Unit tests (Node.js test runner)
│   └── fixtures/              # Test XML fixtures
├── docs/
│   ├── mule2logic-cli-spec-v2.md
│   ├── architecture.md
│   └── test-cases.md
├── package.json
└── LICENSE
```

---

## 🧪 Testing

Tests use the **Node.js built-in test runner**:

```bash
npm test
```

Test coverage includes:

- ✅ End-to-end conversion pipeline
- ✅ Pretty-print, explain, and output-to-file flags
- ✅ Verbose logging
- ✅ Missing file and empty input error handling
- ✅ Invalid JSON retry logic
- ✅ Copilot SDK client lifecycle
- ✅ MCP server configuration
- ✅ Prompt building and template loading
- ✅ JSON validation and structural checks
- ✅ Review agent workflow

See [test-cases.md](docs/test-cases.md) for full details.

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| 📄 Missing file | Friendly error message → exit code `1` |
| 📭 Empty input | Friendly error message → exit code `1` |
| ❌ Invalid JSON from AI | Retry once automatically |
| ❌❌ Retry also fails | Error message → exit code `1` |
| ⏱️ Timeout | Configurable via `--timeout` (default 5 min) |
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
   npm test
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
