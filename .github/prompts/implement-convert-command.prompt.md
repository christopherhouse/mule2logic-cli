---
mode: "agent"
description: "Implement the convert command that orchestrates the conversion pipeline"
---

# Implement Convert Command

Implement `src/commands/convert.js` — the main conversion pipeline.

## Pipeline Steps

The `convert(input, options)` function must:

1. **Load input** — call `readInput(input)` from `../core/io.js`
2. **Build prompt** — call `buildPrompt(xml)` from `../core/prompt.js`
3. **Call Copilot** — call `runCopilot(prompt)` from `../core/copilot.js`
4. **Validate JSON** — call `validateJson(response)` from `../core/validate.js`
5. **Output result** — write to stdout or file via `--output`

## Error Handling

- If input file is missing or empty → log error and `process.exit(1)`
- If Copilot returns invalid JSON → **retry once**
- If retry also fails → log error and `process.exit(1)`

## Flag Handling

- `--explain` → wrap output as `{ workflow, explanation }`
- `--pretty` → use `JSON.stringify(result, null, 2)`
- `--verbose` → log each pipeline step to stderr
- `--output <file>` → write to file instead of stdout

## Constraints

- Export as named export: `export async function convert(input, options)`
- Use async/await throughout
- Import only from `../core/` modules

Refer to `.github/instructions/src-commands.instructions.md` for detailed guidance.
