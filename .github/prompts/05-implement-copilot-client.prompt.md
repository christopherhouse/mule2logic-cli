# Implement the Copilot Client

## Task

Implement `src/core/copilot.js` — the module that calls the Copilot SDK with Microsoft Learn MCP.

## Requirements

### Phase 1: Mock Implementation

First, implement a mock version for development and testing:

- Export an async function `runCopilot(prompt)` that:
  - Accepts a user prompt string.
  - Returns a mock Logic Apps JSON response string.
  - The mock should return a valid, realistic Logic Apps workflow JSON.

### Phase 2: Real Implementation

Replace the mock with the actual Copilot SDK call:

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

- Import `SYSTEM_PROMPT` from `./prompt.js`.
- Return the response text content.

## Tests

Create tests in `test/copilot.test.js`:
- Mock the Copilot SDK to return a known JSON string.
- Verify `runCopilot` returns the expected response.

Refer to `docs/mule2logic-cli-spec-v2.md` sections 5.3 and 6 for details.
