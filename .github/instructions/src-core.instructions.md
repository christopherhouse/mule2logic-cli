---
applyTo: "src/core/**"
---

# Core Module Instructions

Files in `src/core/` are single-responsibility modules. Each exports focused functions.

---

## `copilot.js` — Copilot SDK Client

### Responsibilities

- Create a Copilot SDK session with Microsoft Learn MCP attached
- Send the system prompt + user prompt to the model
- Return the raw text response

### MCP Configuration

```js
mcpServers: {
  learn: {
    type: "http",
    url: "https://learn.microsoft.com/api/mcp"
  }
}
```

### Key Design Decisions

- Export a single function: `export async function runCopilot(prompt)`
- The system prompt is imported from `prompt.js` (or defined as a constant)
- For testability, consider accepting an optional session factory parameter so tests can inject a mock

---

## `prompt.js` — Prompt Builder

### Responsibilities

- Export `buildPrompt(xml)` — wraps the user's XML in the conversion instruction
- Export the `SYSTEM_PROMPT` constant for use by `copilot.js`

### System Prompt (exact text)

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

### User Prompt Template

```
Convert MuleSoft XML to Logic Apps JSON:

<xml content here>

Return only JSON.
```

---

## `io.js` — Input/Output Helpers

### Responsibilities

- Export `readInput(filePath)` — reads XML from a file path using `fs/promises`
- Export `readStdin()` — reads XML from stdin (for piped input)
- Export `writeOutput(data, filePath)` — writes to file or stdout
- Validate that input is non-empty; throw if empty

### Conventions

- Use `fs/promises` for all file operations
- Handle file-not-found errors with a clear message
- Use `process.stdin` for stdin reading

---

## `validate.js` — JSON Validation

### Responsibilities

- Export `validateJson(output)` — parse the string and check structure
- Must verify:
  - `JSON.parse()` succeeds
  - `parsed.definition` exists
  - `parsed.definition.actions` exists
  - `parsed.definition.triggers` exists (for completeness)

### Error Behavior

- Throw `Error("Invalid JSON output")` if validation fails
- The caller (convert command) handles retry logic — `validate.js` just reports pass/fail
