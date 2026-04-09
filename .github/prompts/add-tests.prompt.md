---
mode: "agent"
description: "Add comprehensive tests for all modules plus the three required test cases from the spec"
---

# Add Tests

Create tests for all modules and the three required end-to-end test cases.

## Test Framework Setup

- Install Jest with ES Module support: `npm install --save-dev jest @jest/globals`
- Configure Jest for ES modules in `package.json` or `jest.config.js`

## Test Files to Create

### `tests/core/validate.test.js`

- Valid JSON with `definition.triggers` and `definition.actions` → returns parsed object
- Non-JSON string → throws `"Invalid JSON output"`
- JSON missing `definition` → throws
- JSON missing `definition.actions` → throws
- JSON missing `definition.triggers` → throws (if validated)

### `tests/core/prompt.test.js`

- `buildPrompt(xml)` includes the XML content
- `buildPrompt(xml)` includes "Convert MuleSoft XML to Logic Apps JSON"
- `SYSTEM_PROMPT` contains "Azure Integration Architect"
- `SYSTEM_PROMPT` contains "Output ONLY valid JSON"

### `tests/core/io.test.js`

- `readInput` successfully reads a fixture file
- `readInput` throws on non-existent file
- `readInput` throws on empty file
- `writeOutput` writes to file when path provided

### `tests/commands/convert.test.js`

Mock `copilot.js` and test the full pipeline:
- Happy path with valid Copilot response → valid JSON output
- First Copilot call returns bad JSON, retry succeeds
- Both calls return bad JSON → process exits with code 1

## Test Fixtures

Create these in `tests/fixtures/`:

**`simple-flow.xml`:**
```xml
<flow name="test">
  <http:listener path="/hello"/>
  <set-payload value="Hello"/>
</flow>
```

**`conditional.xml`:**
```xml
<choice>
  <when expression="#[payload == 'A']">
    <set-payload value="A"/>
  </when>
</choice>
```

**`loop.xml`:**
```xml
<foreach>
  <set-payload value="item"/>
</foreach>
```

## Conventions

- Never make real Copilot SDK calls in tests — always mock
- Use `jest.mock()` or manual mocks for `copilot.js`
- Use descriptive test names
- Keep fixtures in `tests/fixtures/`
