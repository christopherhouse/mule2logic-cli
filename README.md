# mule2logic-cli

Migrate MuleSoft flows to Azure Logic Apps Standard workflows with AI!

A Node.js CLI tool that converts MuleSoft XML flows into deployable Azure Logic Apps Standard workflow JSON using the GitHub Copilot SDK with Microsoft Learn MCP for grounding.

## Usage

```bash
# Convert a MuleSoft XML file
mule2logic convert flow.xml

# Pipe XML from stdin
cat flow.xml | mule2logic convert

# Write output to a file with pretty-printing
mule2logic convert flow.xml --output workflow.json --pretty

# Include an explanation of the conversion
mule2logic convert flow.xml --explain

# Enable debug logging
mule2logic convert flow.xml --verbose
```

## Flags

| Flag              | Description            |
|-------------------|------------------------|
| `--output <file>` | Write JSON to file     |
| `--explain`       | Include explanation    |
| `--pretty`        | Pretty-print JSON      |
| `--verbose`       | Debug logs             |

## Prerequisites

- Node.js 18+
- GitHub Copilot SDK access

## Getting Started

```bash
npm install
npm link   # makes the 'mule2logic' command available globally
```

## Development

See the following docs for development guidance:

- **[Product Spec](docs/mule2logic-cli-spec-v2.md)** — Full product specification
- **[Architecture](docs/architecture.md)** — System architecture overview
- **[Test Cases](docs/test-cases.md)** — Required test cases

Prompt files for guided development with GitHub Copilot are in `.github/prompts/`.

## License

See [LICENSE](LICENSE).
