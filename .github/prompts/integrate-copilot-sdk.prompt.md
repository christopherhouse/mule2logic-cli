---
mode: "agent"
description: "Wire up the real Copilot SDK integration replacing the mock"
---

# Integrate Copilot SDK

Replace the mock Copilot client with the real Copilot SDK integration.

## Steps

1. Update `src/core/copilot.js` to use the real Copilot SDK:
   ```js
   import { createSession } from "copilot-sdk";
   ```

2. Create a session with Microsoft Learn MCP:
   ```js
   const session = await createSession({
     mcpServers: {
       learn: {
         type: "http",
         url: "https://learn.microsoft.com/api/mcp"
       }
     }
   });
   ```

3. Send the system prompt and user prompt:
   ```js
   const response = await session.complete({
     messages: [
       { role: "system", content: SYSTEM_PROMPT },
       { role: "user", content: prompt }
     ]
   });
   ```

4. Return the response text content

## Important

- Keep the mock version available for testing (either via dependency injection or environment flag)
- Ensure the `SYSTEM_PROMPT` from `prompt.js` is used
- The function signature `runCopilot(prompt)` must not change
- Error handling: if the SDK throws, let the error propagate to the convert command for retry logic

Refer to the spec at `docs/mule2logic-cli-spec-v2.md` section 5.3 for the exact pseudo-code.
