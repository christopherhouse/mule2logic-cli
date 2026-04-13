# MuleSoft → Logic Apps Standard Migration Platform

## Required Reading

Before making any changes, read these documents:

- `docs/mule2logic-cli-spec.md` — authoritative product spec. **If instructions here conflict with the spec, the spec wins.**
- `docs/copilot-coding-agent-implementation-plan.md` — delivery plan, PR sequence, toolchain decisions, and living document policy.

## Architecture

The platform converts MuleSoft (Anypoint) projects into Azure Logic Apps Standard projects. It supports two input modes:

- **Project mode**: full MuleSoft project root (pom.xml + flows) → full Logic Apps Standard project
- **Single-flow mode**: individual Mule flow XML → standalone workflow JSON

Key components: CLI (TypeScript), API (Python FastAPI), IR Engine, Validator, Agent Orchestrator (Microsoft Agent Framework). See `docs/mule2logic-cli-spec.md` §3 for details.

## Tech Stack Rules

### Python (backend, services)

- **Python 3.13** required.
- **`uv` exclusively** for environment management, dependency resolution, locking, and installation. Never use pip, pip-tools, poetry, or conda.
- Framework: **FastAPI**.
- Models/validation: **Pydantic**.
- Testing: **pytest**. Every feature PR must include tests.
- Linting: **ruff** (lint + format). Configure in `pyproject.toml`.
- Type hints required on all public interfaces.

### TypeScript (CLI)

- **Latest GA TypeScript**.
- UX: **chalk** for colors, emoji/icons for status, progress spinners for long operations.
- Testing: use a standard runner (vitest or similar). Every feature PR must include tests.
- Linting: **ESLint** + **Prettier**.
- Strict mode enabled in `tsconfig.json`.

### Infrastructure as Code

- **Bicep with Azure Verified Modules (AVM) only**. Fall back to raw Bicep only when no AVM exists for a required resource.
- **Do not use** Terraform, OpenTofu, Pulumi, or ARM templates.

## Identity and Security

- **User Assigned Managed Identity (UAMI) only**. No system-assigned, no service principals with secrets.
- **No secrets** in generated artifacts. `.env` files contain placeholders/mock values only.
- **Built-in Logic Apps connectors preferred**, with identity-based authentication.
- Managed/API connectors are a last resort.

## Error Handling

- Use structured error models with error codes, messages, and severity levels.
- Never swallow exceptions silently.
- In single-flow mode, missing external references (connector configs, properties) produce warnings, not failures.
- Unsupported constructs produce explicit migration gaps, never silent drops.

## Observability

- **OpenTelemetry** for all new spans and traces.
- Propagate trace/correlation context from CLI through API to services.
- Export to Azure Monitor / Application Insights.
- Structured logging correlated with trace context.

## Code Organization

Keep concerns separated — do not collapse into monolithic modules:

| Concern | Location |
|---------|----------|
| API routes | `apps/api/` |
| CLI | `apps/cli/` |
| Shared contracts | `packages/contracts/` |
| Mapping config | `packages/mapping-config/` |
| Mule parsing | `services/parser/` |
| IR models | `services/ir/` |
| Transformation | `services/transform/` |
| Validation | `services/validate/` |
| Agent orchestration | `services/agents/` |
| Infrastructure | `infra/bicep/` |

## Connector Mapping

Mappings are externalized in config files (YAML), not hardcoded. Priority order:

1. Built-in Logic Apps connectors
2. Identity-based authentication
3. Managed/API connectors (last resort)

## Available Agents and Skills

Use specialized agents for focused work:

| Agent | When to use |
|-------|------------|
| `bicep-infra` | Bicep, AVM, UAMI, Azure resource provisioning |
| `python-backend` | FastAPI, Pydantic, uv, pytest, service layer |
| `typescript-cli` | CLI UX, chalk, emoji, command structure |
| `foundry-agent` | Agent Framework, Foundry, model deployment |
| `qa` | Test strategy, golden tests, coverage, fixtures |

Use skills for domain knowledge:

| Skill | When to use |
|-------|------------|
| `logic-apps-standard` | Logic Apps project structure, workflow.json schema |
| `mulesoft-project` | Mule XML conventions, project layout, pom.xml |
| `connector-mapping` | Mapping resolution, priority rules, config format |

## Documentation Validation

When implementing or reviewing code, use available MCP servers to validate against current documentation:

- **Microsoft Learn MCP** (`mcp_microsoft-lea`): Use for Azure-specific docs — Bicep modules, Logic Apps connectors, Azure Container Apps, Managed Identity, App Insights, Agent Framework. Search first with `microsoft_docs_search`, fetch full pages with `microsoft_docs_fetch` when needed.
- **context7 MCP** (`mcp_context7`): Use for library/framework docs — FastAPI, Pydantic, chalk, commander, pytest, ruff, OpenTelemetry SDKs. Resolve the library ID first with `resolve-library-id`, then query with `query-docs`.

Prefer these over general web search for any library, SDK, or Azure service documentation. Your training data may not reflect recent API changes.

## PR Workflow

- Every feature PR must include tests.
- After completing a PR, update `docs/copilot-coding-agent-implementation-plan.md`:
  - Mark the PR heading with `✅ COMPLETE`
  - Add a brief completion note (date, deviations, follow-ups)
- Before starting a PR, re-read its section in the implementation plan — requirements may have been updated.
- Keep PRs small and independently reviewable.
