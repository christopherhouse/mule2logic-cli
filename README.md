<div align="center">

# 🔄 mule2logic-cli

**Migrate MuleSoft flows → Azure Logic Apps Standard workflows with AI ✨**

[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Copilot](https://img.shields.io/badge/Powered%20by-GitHub%20Copilot-8957e5?logo=github)](https://github.com/features/copilot)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/christopherhouse/mule2logic-cli/pulls)

<br />

<img src="https://img.shields.io/badge/MuleSoft%20XML-→-blue?style=for-the-badge" alt="" /> <img src="https://img.shields.io/badge/Azure%20Logic%20Apps%20JSON-✔-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" alt="" />

<br />

*Drop in your MuleSoft XML, get back deployable Logic Apps JSON. It's that simple.* 🚀

</div>

---

## 🤔 What is this?

`mule2logic` is a lightweight Node.js CLI that uses the **GitHub Copilot SDK** — grounded with [Microsoft Learn MCP](https://learn.microsoft.com/api/mcp) — to intelligently convert MuleSoft XML flow definitions into **production-ready Azure Logic Apps Standard workflow JSON**.

No manual rewriting. No copy-paste marathons. Just point it at your MuleSoft XML and let AI do the heavy lifting. 💪

### 🧩 Supported MuleSoft → Logic Apps Mappings

| MuleSoft Element | Logic Apps Equivalent |
|---|---|
| `<http:listener>` | HTTP trigger (Request trigger) |
| `<set-payload>` | Compose action |
| `<choice>` / `<when>` | Condition action (If) |
| `<foreach>` | For_each action |
| `<logger>` | Compose action (for logging) |
| `<flow>` | Workflow definition wrapper |

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

That's it — you now have the `mule2logic` command ready to go! 🎉

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
mule2logic convert flow.xml --explain
```

### Debug mode

```bash
mule2logic convert flow.xml --verbose
```

### 🎛️ All CLI Flags

| Flag | Description |
|---|---|
| `--output <file>` | 📁 Write JSON to a file instead of stdout |
| `--explain` | 💡 Include an AI-generated explanation of the conversion |
| `--pretty` | 🎨 Pretty-print the JSON output (2-space indent) |
| `--verbose` | 🔍 Print debug information to stderr |

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

✅ Ready to deploy to Azure Logic Apps Standard!

---

## 🏗️ Architecture

```
XML Input  →  io.js  →  prompt.js  →  copilot.js  →  validate.js  →  JSON Output
 (file          (read)    (build        (Copilot SDK    (parse &        (stdout
  or stdin)                prompt)       + Learn MCP)     validate)       or file)
```

The CLI follows a clean, linear pipeline:

1. **📥 Load** — Read MuleSoft XML from a file or stdin
2. **📝 Prompt** — Build a structured prompt for the AI model
3. **🤖 Convert** — Send to GitHub Copilot SDK (grounded via Microsoft Learn MCP)
4. **✅ Validate** — Ensure the response is valid Logic Apps JSON
5. **📤 Output** — Write to stdout or a file

> If validation fails, the tool **automatically retries once** before giving up — because even AI deserves a second chance 😄

For a deep dive, check out the [Architecture doc](docs/architecture.md).

---

## 📂 Project Structure

```
mule2logic-cli/
├── src/
│   ├── cli.js                 # 🎯 CLI entry point (commander)
│   ├── commands/
│   │   └── convert.js         # 🔄 Conversion pipeline orchestrator
│   └── core/
│       ├── copilot.js         # 🤖 Copilot SDK + Learn MCP client
│       ├── prompt.js          # 📝 System & user prompt builder
│       ├── io.js              # 📥 File and stdin reader
│       └── validate.js        # ✅ JSON structure validator
├── test/
│   └── fixtures/              # 📋 Test XML fixtures
├── docs/
│   ├── mule2logic-cli-spec-v2.md   # 📘 Full product spec
│   ├── architecture.md              # 🏗️ Architecture overview
│   └── test-cases.md                # 🧪 Test case definitions
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

- ✅ Simple HTTP flow conversion
- ✅ Conditional (`choice`/`when`) conversion
- ✅ Loop (`foreach`) conversion
- ✅ Missing file error handling
- ✅ Empty input error handling
- ✅ Invalid JSON retry logic
- ✅ All CLI flags (`--output`, `--pretty`, `--explain`, `--verbose`)

See [test-cases.md](docs/test-cases.md) for full details.

---

## 🛡️ Error Handling

The CLI is designed to fail gracefully:

| Scenario | Behavior |
|---|---|
| 📄 Missing file | Friendly error message → exit code `1` |
| 📭 Empty input | Friendly error message → exit code `1` |
| ❌ Invalid JSON from AI | Retry once automatically |
| ❌❌ Retry also fails | Error message → exit code `1` |

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
