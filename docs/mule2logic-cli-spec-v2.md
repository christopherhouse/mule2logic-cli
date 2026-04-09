# Mule-to-Logic Apps CLI (MVP) – Agent-Ready Product Spec

## 0. Goal
Build a Node.js CLI that converts MuleSoft XML flows into **deployable Azure Logic Apps Standard workflow JSON** using GitHub Copilot SDK with **Microsoft Learn MCP** for grounding.

---

## 1. Acceptance Criteria (MANDATORY)

The tool is complete when:

1. `mule2logic convert <file>` runs successfully
2. Accepts XML via file or stdin
3. Calls Copilot SDK with Learn MCP attached
4. Returns **valid JSON** (parsable)
5. Output conforms to Logic Apps structure:
   - `definition.triggers`
   - `definition.actions`
6. Works on ALL test cases in section 7

---

## 2. CLI Contract

### Commands

```bash
mule2logic convert <input>
```

### Flags

| Flag | Description |
|-----|------------|
| --output <file> | Write JSON to file |
| --explain | Include explanation |
| --pretty | Pretty-print JSON |
| --verbose | Debug logs |

---

## 3. Project Structure

```
/src
  /cli.js
  /commands/convert.js
  /core/copilot.js
  /core/prompt.js
  /core/io.js
  /core/validate.js
/package.json
```

---

## 4. Dependencies

- Node.js 18+
- commander
- fs/promises

(Assume Copilot SDK is available via import)

---

## 5. Core Modules

### 5.1 CLI Entry (cli.js)
- Parse args
- Route to command

### 5.2 Convert Command
Steps:
1. Load input
2. Build prompt
3. Call Copilot
4. Validate JSON
5. Output result

---

### 5.3 Copilot Client (copilot.js)

Pseudo-code:

```js
import { createSession } from "copilot-sdk";

export async function runCopilot(prompt) {
  const session = await createSession({
    mcpServers: {
      learn: {
        type: "http",
        url: "https://learn.microsoft.com/api/mcp"
      }
    }
  });

  const response = await session.complete({
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: prompt }
    ]
  });

  return response;
}
```

---

### 5.4 Prompt Builder (prompt.js)

```js
export function buildPrompt(xml) {
  return `Convert MuleSoft XML to Logic Apps JSON:

${xml}

Return only JSON.`;
}
```

---

### 5.5 Validation (validate.js)

```js
export function validateJson(output) {
  try {
    const parsed = JSON.parse(output);

    if (!parsed.definition) throw "Missing definition";
    if (!parsed.definition.actions) throw "Missing actions";

    return parsed;
  } catch (err) {
    throw new Error("Invalid JSON output");
  }
}
```

---

## 6. System Prompt (STRICT)

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

## 7. Test Cases (REQUIRED)

### Test 1: Simple Flow

Input:

```xml
<flow name="test">
  <http:listener path="/hello"/>
  <set-payload value="Hello"/>
</flow>
```

Expected:
- HTTP trigger
- Compose action

---

### Test 2: Conditional

Input:
```xml
<choice>
  <when expression="#[payload == 'A']">
    <set-payload value="A"/>
  </when>
</choice>
```

Expected:
- Condition action

---

### Test 3: Loop

Input:
```xml
<foreach>
  <set-payload value="item"/>
</foreach>
```

Expected:
- Foreach action

---

## 8. Error Handling

| Case | Behavior |
|-----|--------|
| Missing file | exit 1 |
| Empty input | exit 1 |
| Invalid JSON | retry once |
| Retry fails | exit 1 |

---

## 9. Output Format

Default:

```json
{
  "definition": {
    "triggers": {},
    "actions": {}
  }
}
```

With --explain:

```json
{
  "workflow": {...},
  "explanation": "..."
}
```

---

## 10. Implementation Order (IMPORTANT)

1. CLI parsing
2. Input loader
3. Prompt builder
4. Copilot call (mock first)
5. JSON validation
6. Real Copilot integration
7. Add flags

---

## 11. Non-Goals

- No Azure deployment
- No schema validation beyond basic
- No UI

---

## 12. Stretch Goals

- Add schema validation
- Add retry backoff
- Add logging middleware

---

## FINAL INSTRUCTION TO AGENT

Build this EXACTLY as specified.

Do not over-engineer.
Do not add features not listed.

Focus on:
- correctness
- valid JSON output
- working CLI
