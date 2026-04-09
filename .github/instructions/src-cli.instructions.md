---
applyTo: "src/cli.js"
---

# CLI Entry Point Instructions

This file is the CLI entry point for `mule2logic-cli`.

## Responsibilities

- Import and configure `commander`
- Define the `convert` command with positional `<input>` argument
- Register flags: `--output <file>`, `--explain`, `--pretty`, `--verbose`
- Route the parsed arguments to the convert command handler in `commands/convert.js`
- Set the binary name to `mule2logic`

## Conventions

- Use ES Module syntax (`import`/`export`)
- Keep this file thin — no business logic, only CLI wiring
- Use `commander`'s `.action()` to invoke the convert handler
- Set `process.exitCode` or call `process.exit(1)` for fatal errors
- Include a shebang line: `#!/usr/bin/env node`

## Example skeleton

```js
#!/usr/bin/env node
import { Command } from "commander";
import { convert } from "./commands/convert.js";

const program = new Command();
program
  .name("mule2logic")
  .description("Convert MuleSoft XML flows to Azure Logic Apps JSON")
  .version("1.0.0");

program
  .command("convert <input>")
  .description("Convert a MuleSoft XML file to Logic Apps workflow JSON")
  .option("--output <file>", "Write JSON to file")
  .option("--explain", "Include explanation")
  .option("--pretty", "Pretty-print JSON")
  .option("--verbose", "Debug logs")
  .action(convert);

program.parse();
```
