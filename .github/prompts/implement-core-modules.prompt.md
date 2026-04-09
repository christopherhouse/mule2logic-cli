---
mode: "agent"
description: "Implement all core modules: copilot client, prompt builder, I/O helpers, and JSON validator"
---

# Implement Core Modules

Implement the four core modules in `src/core/`.

---

## 1. `src/core/io.js` — Input/Output Helpers

### Exports

- `readInput(filePath)` — Read XML content from a file using `fs/promises`. Throw if file doesn't exist or content is empty.
- `readStdin()` — Read from `process.stdin` and return the full content as a string.
- `writeOutput(data, filePath)` — If `filePath` is provided, write to file; otherwise write to stdout.

---

## 2. `src/core/prompt.js` — Prompt Builder

### Exports

- `SYSTEM_PROMPT` — The exact system prompt string:
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

- `buildPrompt(xml)` — Returns the user prompt:
  ```
  Convert MuleSoft XML to Logic Apps JSON:

  <xml content>

  Return only JSON.
  ```

---

## 3. `src/core/copilot.js` — Copilot SDK Client

### Exports

- `runCopilot(prompt)` — Create a Copilot SDK session with Learn MCP, send system prompt + user prompt, return the response text.

### MCP Server Config

```js
mcpServers: {
  learn: {
    type: "http",
    url: "https://learn.microsoft.com/api/mcp"
  }
}
```

### Mock-first approach

Start by implementing a mock that returns a valid Logic Apps JSON structure. This allows all other modules to be tested before the real SDK is wired in.

---

## 4. `src/core/validate.js` — JSON Validator

### Exports

- `validateJson(output)` — Parse the output string with `JSON.parse()`. Verify `definition`, `definition.triggers`, and `definition.actions` exist. Return the parsed object on success, throw `Error("Invalid JSON output")` on failure.

---

## Constraints

- ES Module syntax everywhere
- Use only `fs/promises` for file I/O
- No extra dependencies
- Each module is a single file with focused exports

Refer to `.github/instructions/src-core.instructions.md` for detailed guidance.
