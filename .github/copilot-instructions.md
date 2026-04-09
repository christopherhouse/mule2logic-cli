# Copilot Instructions for mule2logic-cli

## Project Overview

This is a Node.js CLI tool that converts MuleSoft XML flows into deployable Azure Logic Apps Standard workflow JSON. It uses the GitHub Copilot SDK with Microsoft Learn MCP for grounding.

## Product Spec

The full product specification is at `docs/mule2logic-cli-spec-v2.md`. Always refer to it for detailed requirements, acceptance criteria, and test cases.

## Tech Stack

- **Runtime:** Node.js 18+
- **Language:** JavaScript (ES modules)
- **CLI Framework:** commander
- **File I/O:** fs/promises (built-in)
- **AI:** Copilot SDK with Microsoft Learn MCP server

## Project Structure

```
/src
  cli.js              # CLI entry point — parses args, routes to commands
  /commands
    convert.js         # Convert command — orchestrates the conversion pipeline
  /core
    copilot.js         # Copilot SDK client — manages sessions and completions
    prompt.js          # Prompt builder — constructs system and user prompts
    io.js              # I/O utilities — reads files and stdin
    validate.js        # JSON validator — ensures output is valid Logic Apps JSON
/test
  convert.test.js      # Tests for the convert command
  prompt.test.js       # Tests for prompt building
  validate.test.js     # Tests for JSON validation
  io.test.js           # Tests for I/O utilities
  /fixtures
    simple-flow.xml    # Test fixture: simple HTTP flow
    conditional.xml    # Test fixture: choice/when flow
    loop.xml           # Test fixture: foreach flow
/docs
  mule2logic-cli-spec-v2.md  # Full product specification
  architecture.md             # Architecture overview
  test-cases.md               # Structured test cases
/package.json
```

## CLI Contract

The CLI exposes one command:

```bash
mule2logic convert <input>
```

### Flags

| Flag              | Description            |
|-------------------|------------------------|
| `--output <file>` | Write JSON to file     |
| `--explain`       | Include explanation    |
| `--pretty`        | Pretty-print JSON      |
| `--verbose`       | Debug logs             |

Input can come from a file path argument or from stdin (piped input).

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

## Coding Conventions

### General

- Use ES module syntax (`import`/`export`), not CommonJS (`require`/`module.exports`).
- Set `"type": "module"` in `package.json`.
- Keep modules small and single-purpose, following the structure above.
- Do not over-engineer. Keep it simple and match the spec exactly.
- Do not add features not listed in the spec.

### Error Handling

| Case           | Behavior                          |
|----------------|-----------------------------------|
| Missing file   | Print error message and exit with code 1 |
| Empty input    | Print error message and exit with code 1 |
| Invalid JSON   | Retry Copilot call once           |
| Retry fails    | Print error message and exit with code 1 |

- Use `process.exit(1)` for fatal errors.
- Always provide a user-friendly error message to stderr before exiting.

### Validation Rules

The `validate.js` module must check that Copilot's response:
1. Is parseable as JSON.
2. Contains a `definition` object at the top level.
3. Contains `definition.actions` (object).
4. Contains `definition.triggers` (object) when a trigger source is present in the MuleSoft XML.

### Prompts

- The system prompt is defined in `prompt.js` and must instruct the model to output **only valid JSON** with no markdown wrapping.
- The user prompt wraps the MuleSoft XML and asks for conversion to Logic Apps JSON.
- Refer to spec section 6 for the exact system prompt text.

### Testing

- Use Node.js built-in test runner (`node --test`) or a lightweight framework like vitest.
- Place tests in `/test` directory, mirroring `/src` structure.
- Create XML fixture files in `/test/fixtures/` for each test case in the spec.
- Test the validate, prompt, and io modules with unit tests.
- For the Copilot client, test with mock responses.

## Implementation Order

Follow this exact order when building features:

1. **CLI parsing** — Set up commander with the `convert` command and all flags.
2. **Input loader** (`io.js`) — Read from file path or stdin.
3. **Prompt builder** (`prompt.js`) — Build system and user prompts from XML input.
4. **Copilot call with mock** (`copilot.js`) — Implement with a mock response first.
5. **JSON validation** (`validate.js`) — Validate the output structure.
6. **Real Copilot integration** — Replace mock with actual Copilot SDK calls with Learn MCP.
7. **Add flags** — Wire up `--output`, `--explain`, `--pretty`, `--verbose`.

## Non-Goals

- No Azure deployment functionality.
- No deep schema validation beyond basic structural checks.
- No graphical UI.

## MuleSoft-to-Logic Apps Mapping Reference

When converting MuleSoft XML elements, use these mappings:

| MuleSoft Element         | Logic Apps Equivalent           |
|--------------------------|---------------------------------|
| `<http:listener>`        | HTTP trigger (Request trigger)  |
| `<set-payload>`          | Compose action                  |
| `<choice>` / `<when>`    | Condition action (If)           |
| `<foreach>`              | For_each action                 |
| `<logger>`               | Compose action (for logging)    |
| `<flow>`                 | Workflow definition wrapper     |

## Microsoft Learn MCP Configuration

The Copilot SDK session must be configured with the Microsoft Learn MCP server:

```js
mcpServers: {
  learn: {
    type: "http",
    url: "https://learn.microsoft.com/api/mcp"
  }
}
```

This provides grounding for Azure Logic Apps best practices and schema details.
