# Scaffold the mule2logic-cli Project

## Task

Initialize the Node.js project and set up the directory structure as defined in the product spec.

## Steps

1. Run `npm init -y` to create `package.json`.
2. In `package.json`:
   - Set `"type": "module"` for ES module support.
   - Set `"name": "mule2logic-cli"`.
   - Set `"bin": { "mule2logic": "./src/cli.js" }` so the CLI can be invoked as `mule2logic`.
   - Add `"engines": { "node": ">=18.0.0" }`.
   - Add a `"start"` script: `"node src/cli.js"`.
   - Add a `"test"` script: `"node --test test/**/*.test.js"`.
3. Install `commander` as a dependency: `npm install commander`.
4. Create the directory structure:
   ```
   src/
   src/commands/
   src/core/
   test/
   test/fixtures/
   ```
5. Create placeholder files with module boilerplate in each:
   - `src/cli.js`
   - `src/commands/convert.js`
   - `src/core/copilot.js`
   - `src/core/prompt.js`
   - `src/core/io.js`
   - `src/core/validate.js`

Refer to `docs/mule2logic-cli-spec-v2.md` for the full spec and `.github/copilot-instructions.md` for coding conventions.
