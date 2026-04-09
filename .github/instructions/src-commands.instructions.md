---
applyTo: "src/commands/**"
---

# Commands Instructions

Files in `src/commands/` implement CLI command handlers.

## `convert.js` — Convert Command Handler

### Pipeline

The convert command orchestrates this exact pipeline:

1. **Load input** — call `io.js` to read XML from file or stdin
2. **Build prompt** — call `prompt.js` to construct the Copilot prompt from the XML
3. **Call Copilot** — call `copilot.js` to get the AI-generated Logic Apps JSON
4. **Validate JSON** — call `validate.js` to ensure the output is valid
5. **Output result** — write to stdout or to `--output` file

### Error Handling

| Scenario | Behavior |
|----------|----------|
| File not found or empty input | Log error, `process.exit(1)` |
| Copilot returns invalid JSON | Retry **once**, then `process.exit(1)` |
| `--output` write failure | Log error, `process.exit(1)` |

### Flag Behavior

- `--explain` — wrap output in `{ workflow, explanation }` format
- `--pretty` — use `JSON.stringify(result, null, 2)` for output
- `--verbose` — log intermediate steps (input loaded, prompt built, copilot called, etc.)
- `--output <file>` — write result to file instead of stdout

### Conventions

- Use async/await throughout
- Import only from `../core/` modules
- Keep the function exported as a named export: `export async function convert(input, options)`
- Do not catch errors silently — always log before exiting
