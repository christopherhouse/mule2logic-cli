# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│  CLI (cli.js)                                           │
│  Parses arguments and routes to the convert command     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Convert Command (commands/convert.js)                  │
│  Orchestrates the full conversion pipeline              │
│                                                         │
│  1. Load XML input (file or stdin)                      │
│  2. Build prompt from XML                               │
│  3. Call Copilot SDK                                    │
│  4. Validate response JSON                              │
│  5. Retry once on validation failure                    │
│  6. Output result (stdout or file)                      │
└────┬──────────┬──────────┬──────────┬───────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│ io.js  │ │prompt.js│ │copilot │ │validate  │
│        │ │        │ │  .js   │ │  .js     │
│ Read   │ │ Build  │ │ Call   │ │ Check    │
│ file   │ │ system │ │Copilot │ │ JSON     │
│ or     │ │ & user │ │ SDK +  │ │ structure│
│ stdin  │ │ prompt │ │ Learn  │ │          │
│        │ │        │ │  MCP   │ │          │
└────────┘ └────────┘ └───┬────┘ └──────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Microsoft Learn   │
                │ MCP Server        │
                │ (grounding)       │
                └───────────────────┘
```

## Module Responsibilities

### cli.js
- Entry point for the application.
- Uses `commander` to define the `convert` command and CLI flags.
- Delegates to `commands/convert.js`.

### commands/convert.js
- The main orchestrator. Runs the conversion pipeline end-to-end.
- Handles the retry-once logic when JSON validation fails.
- Handles `--output`, `--explain`, `--pretty`, and `--verbose` flags.

### core/io.js
- Reads MuleSoft XML from a file path argument or from stdin (piped input).
- Validates that input is not empty.
- Returns the raw XML string.

### core/prompt.js
- Contains the system prompt (strict rules for the model).
- Builds the user prompt by wrapping the XML input.
- Exports `SYSTEM_PROMPT` constant and `buildPrompt(xml)` function.

### core/copilot.js
- Creates a Copilot SDK session with the Microsoft Learn MCP server attached.
- Sends the system prompt and user prompt to the model.
- Returns the raw response text.

### core/validate.js
- Parses the response as JSON.
- Checks for required top-level structure: `definition`, `definition.triggers`, `definition.actions`.
- Returns the parsed object on success, throws on failure.

## Data Flow

```
XML Input  →  io.js  →  prompt.js  →  copilot.js  →  validate.js  →  JSON Output
  (file         (read)    (build       (call SDK)     (parse &        (stdout
   or                      prompt)                     validate)       or file)
   stdin)
```

## Error Flow

```
                          ┌──────────────┐
                          │ validate.js  │
                          │ returns error│
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │  Retry once  │
                          │ (copilot.js) │
                          └──────┬───────┘
                                 │
                      ┌──────────┴──────────┐
                      │                     │
               ┌──────▼───────┐    ┌────────▼────────┐
               │  Success     │    │  Fail again      │
               │  Output JSON │    │  Exit code 1     │
               └──────────────┘    └─────────────────┘
```
