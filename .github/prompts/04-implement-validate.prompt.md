# Implement the JSON Validator

## Task

Implement `src/core/validate.js` — the module that validates Copilot's JSON response.

## Requirements

- Export a function `validateJson(output)` that:
  - Parses the `output` string as JSON.
  - Checks that the parsed object has a `definition` property.
  - Checks that `definition.actions` exists and is an object.
  - Optionally checks that `definition.triggers` exists.
  - Returns the parsed object on success.
  - Throws an `Error` with a descriptive message on failure.
  - If the output contains markdown code fences (```json ... ```), strips them before parsing.

## Tests

Create `test/validate.test.js` with tests for:
- Valid Logic Apps JSON parses successfully and returns the object.
- Missing `definition` key throws an error.
- Missing `definition.actions` throws an error.
- Non-JSON string throws an error.
- JSON wrapped in markdown code fences is handled gracefully.

### Test Data

Valid JSON:
```json
{
  "definition": {
    "triggers": {
      "manual": { "type": "Request", "kind": "Http" }
    },
    "actions": {
      "Compose": { "type": "Compose", "inputs": "Hello" }
    }
  }
}
```

Invalid JSON examples:
- `"not json at all"`
- `'{ "foo": "bar" }'` (no definition)
- `'{ "definition": {} }'` (no actions)
