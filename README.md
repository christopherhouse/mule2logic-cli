# mule2logic-cli

Convert MuleSoft XML flows to Azure Logic Apps Standard workflow JSON using AI.

## Overview

mule2logic-cli is a Node.js CLI tool that uses the GitHub Copilot SDK with Microsoft Learn MCP to convert MuleSoft XML flow definitions into deployable Azure Logic Apps Standard workflow JSON.

## Requirements

- Node.js 18+

## Installation

```bash
npm install
npm link  # makes the `mule2logic` command available globally
```

## Usage

```bash
# Convert a MuleSoft XML file
mule2logic convert flow.xml

# Pipe XML via stdin
cat flow.xml | mule2logic convert -

# Write output to a file
mule2logic convert flow.xml --output workflow.json

# Pretty-print the output
mule2logic convert flow.xml --pretty

# Include an explanation of the conversion
mule2logic convert flow.xml --explain

# Enable verbose/debug logging
mule2logic convert flow.xml --verbose
```

## Project Structure

```
src/
  cli.js                  # CLI entry point
  commands/
    convert.js            # Convert command handler
  core/
    copilot.js            # Copilot SDK client
    prompt.js             # Prompt builder
    io.js                 # Input/output helpers
    validate.js           # JSON validation
tests/                    # Tests mirroring src structure
docs/
  mule2logic-cli-spec-v2.md  # Product specification
```

## Development

```bash
# Run tests
npm test

# Run the CLI locally
node src/cli.js convert <file>
```

## Copilot Development

This repository includes GitHub Copilot instructions and prompt files to help with development:

- **`.github/copilot-instructions.md`** — Global project context and coding conventions
- **`.github/instructions/`** — File-specific code generation guidance
- **`.github/prompts/`** — Reusable prompt templates for common development tasks

### Recommended Prompt Order

Follow these prompts in sequence to build the project from scratch:

1. `setup-project` — Initialize Node.js project and folder structure
2. `implement-cli` — Build the CLI entry point
3. `implement-core-modules` — Build I/O, prompt, validation, and Copilot client (with mock)
4. `implement-convert-command` — Wire up the conversion pipeline
5. `add-tests` — Add unit and integration tests
6. `integrate-copilot-sdk` — Replace mock with real Copilot SDK

## License

See [LICENSE](LICENSE) for details.
