---
mode: "agent"
description: "Implement the CLI entry point with commander"
---

# Implement CLI Entry Point

Implement `src/cli.js` — the CLI entry point for the mule2logic tool.

## Requirements

1. Add a shebang line: `#!/usr/bin/env node`
2. Import `Command` from `commander`
3. Import the `convert` handler from `./commands/convert.js`
4. Create a program with:
   - Name: `mule2logic`
   - Description: `Convert MuleSoft XML flows to Azure Logic Apps JSON`
   - Version: from `package.json`
5. Register the `convert <input>` command with these options:
   - `--output <file>` — Write JSON to file
   - `--explain` — Include explanation
   - `--pretty` — Pretty-print JSON
   - `--verbose` — Debug logs
6. Route the command action to the `convert` handler
7. Call `program.parse()`

## Constraints

- Use ES Module syntax
- Keep this file thin — no business logic
- The convert handler should receive `(input, options)` from commander

Refer to `.github/instructions/src-cli.instructions.md` for detailed guidance.
