---
applyTo: "tests/**"
---

# Test Instructions

## Test Framework

Use Jest (or Node.js built-in test runner) with ES Module support.

## Test Structure

Mirror the `src/` structure:

```
/tests
  cli.test.js
  /commands
    convert.test.js
  /core
    copilot.test.js
    prompt.test.js
    io.test.js
    validate.test.js
  /fixtures
    simple-flow.xml
    conditional.xml
    loop.xml
```

## Required Test Cases

### Validation Tests (`validate.test.js`)

- Valid JSON with `definition.triggers` and `definition.actions` → passes
- Invalid JSON string → throws
- Missing `definition` key → throws
- Missing `definition.actions` → throws

### Prompt Tests (`prompt.test.js`)

- `buildPrompt(xml)` includes the XML in the output
- `buildPrompt(xml)` includes conversion instructions
- `SYSTEM_PROMPT` contains required rules

### I/O Tests (`io.test.js`)

- `readInput` reads a file correctly
- `readInput` throws on missing file
- `readInput` throws on empty file

### Convert Command Tests (`convert.test.js`)

Mock the Copilot client and test the full pipeline:
- Happy path: valid XML → valid JSON output
- Retry: first Copilot call returns invalid JSON, second succeeds
- Failure: both Copilot calls return invalid JSON → exit 1

### End-to-End Test Fixtures

Include these three XML fixtures from the spec:

**simple-flow.xml:**
```xml
<flow name="test">
  <http:listener path="/hello"/>
  <set-payload value="Hello"/>
</flow>
```

**conditional.xml:**
```xml
<choice>
  <when expression="#[payload == 'A']">
    <set-payload value="A"/>
  </when>
</choice>
```

**loop.xml:**
```xml
<foreach>
  <set-payload value="item"/>
</foreach>
```

## Conventions

- Test file names end in `.test.js`
- Use descriptive test names that state the expected behavior
- Mock external dependencies (Copilot SDK) — never make real API calls in tests
- Use fixtures from `tests/fixtures/` for XML inputs
