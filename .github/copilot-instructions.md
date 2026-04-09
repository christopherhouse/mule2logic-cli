# Copilot Instructions — mule2logic-cli

## Project Overview

mule2logic-cli is a **Node.js CLI tool** that converts MuleSoft XML flows into deployable **Azure Logic Apps Standard workflow JSON**. It uses the GitHub Copilot SDK with Microsoft Learn MCP for grounding.

The full product specification lives in [`docs/mule2logic-cli-spec-v2.md`](../docs/mule2logic-cli-spec-v2.md).

---

## Technology Stack

| Area | Technology |
|------|-----------|
| Runtime | Node.js 18+ |
| Language | JavaScript (ES Modules) |
| CLI framework | `commander` |
| File I/O | `fs/promises` (Node built-in) |
| AI integration | Copilot SDK (`copilot-sdk`) with Microsoft Learn MCP |
| Testing | Jest (or Node built-in test runner) |

---

## Project Structure

```
/src
  cli.js            # CLI entry point — parses args, routes to commands
  /commands
    convert.js      # Convert command — orchestrates the full pipeline
  /core
    copilot.js      # Copilot SDK client — manages sessions and completions
    prompt.js        # Prompt builder — constructs the system + user prompt
    io.js            # Input/output helpers — file reading, stdin, writing
    validate.js      # JSON validation — ensures output conforms to Logic Apps schema
/tests               # Test files mirroring src structure
/docs
  mule2logic-cli-spec-v2.md  # Product specification
package.json
```

---

## CLI Contract

The CLI exposes a single command:

```bash
mule2logic convert <input>
```

### Flags

| Flag | Description |
|------|------------|
| `--output <file>` | Write JSON to file instead of stdout |
| `--explain` | Include a natural-language explanation alongside the workflow JSON |
| `--pretty` | Pretty-print the JSON output |
| `--verbose` | Enable debug/verbose logging |

Input can be a file path **or** piped via stdin.

---

## Output Format

### Default output

```json
{
  "definition": {
    "triggers": { },
    "actions": { }
  }
}
```

### With `--explain`

```json
{
  "workflow": { "definition": { "triggers": {}, "actions": {} } },
  "explanation": "Human-readable explanation of the conversion"
}
```

---

## Coding Conventions

1. **ES Modules** — use `import`/`export`, not `require`/`module.exports`. Set `"type": "module"` in `package.json`.
2. **Async/await** — all I/O and Copilot SDK calls must use async/await.
3. **Small, focused modules** — each file in `/src/core` has a single responsibility.
4. **No over-engineering** — do not add features, abstractions, or dependencies not listed in the spec.
5. **Error handling** — follow the error table exactly:
   - Missing file → `process.exit(1)`
   - Empty input → `process.exit(1)`
   - Invalid JSON from Copilot → retry **once**, then `process.exit(1)`
6. **No markdown in AI output** — the system prompt must instruct the model to return **only** valid JSON, no markdown fences.
7. **Minimal dependencies** — only `commander` and `fs/promises` (plus Copilot SDK). Do not add libraries unless absolutely necessary.

---

## System Prompt (for Copilot SDK calls)

Use this exact system prompt when calling the Copilot SDK:

```
You are an expert Azure Integration Architect.

Convert MuleSoft flows into Azure Logic Apps Standard workflows.

Rules:
- Output ONLY valid JSON
- No markdown
- Include triggers and actions
- Preserve logic
- Use Azure best practices
```

---

## MCP Configuration

The Copilot SDK session must attach Microsoft Learn MCP:

```js
mcpServers: {
  learn: {
    type: "http",
    url: "https://learn.microsoft.com/api/mcp"
  }
}
```

---

## Implementation Order

Follow this order when building the project:

1. **CLI parsing** — set up `commander` with the `convert` command and flags
2. **Input loader** (`io.js`) — read from file path or stdin
3. **Prompt builder** (`prompt.js`) — construct the conversion prompt from XML input
4. **Copilot call with mock** (`copilot.js`) — implement with a mock/stub first for testability
5. **JSON validation** (`validate.js`) — parse and validate the output structure
6. **Real Copilot integration** — replace mock with actual Copilot SDK calls
7. **Add flags** — wire up `--output`, `--explain`, `--pretty`, `--verbose`

---

## Validation Rules

Output JSON **must** satisfy:

- `JSON.parse()` succeeds
- Top-level `definition` key exists
- `definition.triggers` exists
- `definition.actions` exists

---

## Test Cases

All three test cases from the spec must pass:

### Test 1 — Simple HTTP Flow
- Input: `<flow>` with `<http:listener>` and `<set-payload>`
- Expected: HTTP trigger + Compose action

### Test 2 — Conditional
- Input: `<choice>` with `<when>` expression
- Expected: Condition action

### Test 3 — Loop
- Input: `<foreach>` with `<set-payload>`
- Expected: Foreach action

---

## Non-Goals (Do NOT implement)

- Azure deployment
- Full Logic Apps JSON schema validation
- Any UI or web interface
- Features not listed in the spec

---

## Stretch Goals (only if core is complete)

- JSON Schema validation against Logic Apps schema
- Retry with exponential backoff
- Logging middleware
