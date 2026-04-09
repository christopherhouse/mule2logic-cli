# Implement the Prompt Builder

## Task

Implement `src/core/prompt.js` — the module that constructs the system and user prompts.

## Requirements

- Export a constant `SYSTEM_PROMPT` containing the exact system prompt from the spec:

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

- Export a function `buildPrompt(xml)` that returns the user prompt:

  ```
  Convert MuleSoft XML to Logic Apps JSON:

  <the xml content here>

  Return only JSON.
  ```

## Tests

Create `test/prompt.test.js` with tests for:
- `SYSTEM_PROMPT` is a non-empty string containing key phrases like "Azure" and "JSON".
- `buildPrompt(xml)` includes the provided XML in the returned string.
- `buildPrompt(xml)` includes the instruction "Return only JSON".

Refer to `docs/mule2logic-cli-spec-v2.md` section 6 for the exact system prompt.
