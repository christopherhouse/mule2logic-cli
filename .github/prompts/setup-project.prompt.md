---
mode: "agent"
description: "Initialize the Node.js project with package.json, dependencies, and folder structure"
---

# Setup Project

Initialize the mule2logic-cli Node.js project.

## Steps

1. Run `npm init -y` in the project root
2. Update `package.json`:
   - Set `"name"` to `"mule2logic-cli"`
   - Set `"type"` to `"module"` (ES Modules)
   - Set `"bin"` to `{ "mule2logic": "./src/cli.js" }`
   - Set `"version"` to `"1.0.0"`
   - Set `"description"` to `"Convert MuleSoft XML flows to Azure Logic Apps Standard workflow JSON"`
   - Add `"scripts"`:  `"start": "node src/cli.js"` and `"test": "jest --experimental-vm-modules"`
   - Set `"engines"` to `{ "node": ">=18.0.0" }`
3. Run `npm install commander`
4. Create the folder structure:
   ```
   src/
   src/commands/
   src/core/
   tests/
   tests/commands/
   tests/core/
   tests/fixtures/
   ```
5. Create empty placeholder files for each module listed in the spec:
   - `src/cli.js`
   - `src/commands/convert.js`
   - `src/core/copilot.js`
   - `src/core/prompt.js`
   - `src/core/io.js`
   - `src/core/validate.js`

Refer to the product spec at `docs/mule2logic-cli-spec-v2.md` for full details.
