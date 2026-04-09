# Implement the Convert Command

## Task

Implement `src/commands/convert.js` — the main conversion pipeline and `src/cli.js` — the CLI entry point.

## Requirements

### cli.js

- Use `commander` to define the program:
  - Command: `convert <input>` — `input` is an optional file path (if omitted, read stdin).
  - Option: `--output <file>` — write output to a file instead of stdout.
  - Option: `--explain` — include an explanation in the output.
  - Option: `--pretty` — pretty-print the JSON output.
  - Option: `--verbose` — print debug info to stderr.
- Add a shebang line `#!/usr/bin/env node` at the top.
- Call `program.parse()` at the end.

### commands/convert.js

- Export an async function that receives the input path and options object.
- Pipeline:
  1. Call `readInput(inputPath)` from `core/io.js`.
  2. Call `buildPrompt(xml)` from `core/prompt.js`.
  3. Call `runCopilot(prompt)` from `core/copilot.js`.
  4. Call `validateJson(response)` from `core/validate.js`.
  5. If validation fails, retry step 3-4 once.
  6. If retry fails, print error to stderr and `process.exit(1)`.
  7. Format the output based on flags:
     - If `--explain`: wrap in `{ workflow, explanation }` structure.
     - If `--pretty`: use `JSON.stringify(result, null, 2)`.
     - Default: `JSON.stringify(result)`.
  8. If `--output`: write to the specified file. Otherwise, print to stdout.
  9. If `--verbose`: log debug info (prompt, response metadata) to stderr.

## Error Handling

- Wrap the entire pipeline in try/catch.
- On any error, print a user-friendly message to stderr and exit with code 1.

## Tests

Create `test/convert.test.js` with integration-style tests:
- Mock the Copilot client.
- Verify the full pipeline produces valid JSON for each test fixture.
- Verify error cases (missing file, empty input) exit with code 1.

Refer to `docs/mule2logic-cli-spec-v2.md` sections 2, 5.2, and 8 for details.
