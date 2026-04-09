# Test Cases

All test cases are derived from the product spec (section 7). Each test must pass for the tool to be considered complete.

---

## Test 1: Simple HTTP Flow

**Description:** A basic MuleSoft flow with an HTTP listener and a set-payload.

**Input XML:**

```xml
<flow name="test">
  <http:listener path="/hello"/>
  <set-payload value="Hello"/>
</flow>
```

**Expected Output Structure:**

- `definition.triggers` must contain an HTTP request trigger.
- `definition.actions` must contain a Compose action with the value "Hello".

**Validation Criteria:**

- Output is valid JSON.
- `definition` key exists.
- `definition.triggers` is a non-empty object.
- `definition.actions` is a non-empty object.

---

## Test 2: Conditional (Choice/When)

**Description:** A MuleSoft choice block with a conditional expression.

**Input XML:**

```xml
<choice>
  <when expression="#[payload == 'A']">
    <set-payload value="A"/>
  </when>
</choice>
```

**Expected Output Structure:**

- `definition.actions` must contain a Condition (If) action.
- The condition should evaluate a payload expression.
- The true branch should contain a Compose action.

**Validation Criteria:**

- Output is valid JSON.
- `definition` key exists.
- `definition.actions` contains at least one action of type condition or If.

---

## Test 3: Loop (Foreach)

**Description:** A MuleSoft foreach loop with an inner action.

**Input XML:**

```xml
<foreach>
  <set-payload value="item"/>
</foreach>
```

**Expected Output Structure:**

- `definition.actions` must contain a For_each (foreach) action.
- The loop body should contain a Compose action.

**Validation Criteria:**

- Output is valid JSON.
- `definition` key exists.
- `definition.actions` contains at least one foreach-type action.

---

## Error Handling Tests

### Test 4: Missing File

**Input:** A non-existent file path.

**Expected:** Process exits with code 1 and an error message to stderr.

### Test 5: Empty Input

**Input:** An empty file or empty stdin.

**Expected:** Process exits with code 1 and an error message to stderr.

### Test 6: Invalid JSON Response (Retry)

**Input:** A valid XML file, but mock the Copilot response to return invalid JSON on the first attempt.

**Expected:** The tool retries once. If the second attempt returns valid JSON, it succeeds. If not, it exits with code 1.

---

## Flag Tests

### Test 7: `--output` Flag

**Input:** A valid XML file with `--output result.json`.

**Expected:** The JSON output is written to `result.json` instead of stdout.

### Test 8: `--pretty` Flag

**Input:** A valid XML file with `--pretty`.

**Expected:** The JSON output is indented (pretty-printed with 2-space indentation).

### Test 9: `--explain` Flag

**Input:** A valid XML file with `--explain`.

**Expected:** Output wraps the workflow in a `workflow` key and includes an `explanation` string.

```json
{
  "workflow": { "definition": { "triggers": {}, "actions": {} } },
  "explanation": "..."
}
```

### Test 10: `--verbose` Flag

**Input:** A valid XML file with `--verbose`.

**Expected:** Debug information is printed to stderr during execution (e.g., prompt content, response metadata).

---

## Test Fixtures

Store fixture files in `/test/fixtures/`:

| File               | Contents                          |
|--------------------|-----------------------------------|
| `simple-flow.xml`  | Test 1 input XML                  |
| `conditional.xml`  | Test 2 input XML                  |
| `loop.xml`         | Test 3 input XML                  |
| `empty.xml`        | Empty file for Test 5             |
