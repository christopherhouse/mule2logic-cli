# MuleSoft → Logic Apps Standard Migration Platform
## Copilot Coding Agent Implementation Plan

This document is a **coding-agent-ready execution plan** for implementing the revised product spec. It is optimized for **GitHub Copilot Coding Agent** and assumes the primary repo already contains the revised product spec.

The plan is intentionally broken into:
- **small, reviewable PRs**
- **clear dependencies**
- **explicit acceptance criteria**
- **copy/paste prompts for Copilot Coding Agent**

The goal is to maximize build reliability and minimize thrash.

### Living document policy

This implementation plan is a **living document**.

- **Progress tracking**: When completing a PR task, the implementing agent **must** update this document to mark the PR as complete (e.g., add a `✅ COMPLETE` tag to the PR heading) and include a brief completion note (date, any deviations from the original scope, follow-up items discovered).
- **Evolving requirements**: PRs that have not yet started may have their scope, acceptance criteria, or requirements updated at any time. The agent must re-read the PR section before starting work — do not rely on a cached understanding from a prior session.
- **Additive changes only for completed PRs**: Once a PR is marked complete, its section becomes a historical record. New work discovered after completion should be captured as a new PR or added to an existing not-yet-started PR.

---

# 0. References

> **Every PR prompt in this plan assumes the implementing agent has read the authoritative product spec first.**

| Document | Path | Purpose |
|----------|------|---------|
| Product Spec | `docs/mule2logic-cli-spec.md` | Authoritative source of truth for all requirements, contracts, connector strategy, identity rules, UX, and supported constructs. |
| This Plan | `docs/copilot-coding-agent-implementation-plan.md` | Execution plan — how to deliver the spec in small PRs. |

### Spec-first rule

Before starting **any** PR, the implementing agent **must**:
1. Read `docs/mule2logic-cli-spec.md` in full.
2. Treat the spec as the authority on product behavior. If a PR prompt and the spec conflict, **the spec wins**.
3. Reference specific spec sections (listed in each PR prompt below) for the requirements that apply.

### Key toolchain decisions (supplement to spec)

- **Python 3.13** — required runtime version.
- **`uv`** — the **only** tool for managing the Python environment and installing dependencies. Do not use `pip`, `pip-tools`, `poetry`, or `conda`. Use `uv` for venv creation, dependency resolution, locking, and installation.
- **TypeScript (latest GA)** — for the CLI.
- **Bicep with Azure Verified Modules (AVM)** — the **only** IaC toolchain. Fall back to raw Bicep only when no AVM exists for a required service or configuration. Do not use Terraform, OpenTofu, Pulumi, or ARM templates.

---

# 1. Delivery Strategy

## Principles
1. Build the platform in **vertical slices**.
2. Land **deterministic foundations first** before complex agent behavior.
3. Keep the agent layer thin until:
   - Mule project parsing
   - IR generation
   - mapping config
   - project generation
   - validation
   are all working.
4. Prefer **testable Python code** over prompt-only logic.
5. Treat the agent as an orchestrator over deterministic components, not a magical converter.
6. Keep every PR independently reviewable and runnable.

## Recommended sequence

> **PRs below are numbered in execution order.** Start at PR-001 and work down the list. Each PR is independently reviewable but assumes prior PRs have landed.

---

# 2. Proposed Repository Layout

```text
repo-root/
├─ apps/
│  ├─ api/                          # Python 3.13 FastAPI backend
│  │  ├─ src/
│  │  │  ├─ m2la_api/
│  │  │  │  ├─ main.py
│  │  │  │  ├─ routes/
│  │  │  │  ├─ services/
│  │  │  │  ├─ telemetry/
│  │  │  │  ├─ config/
│  │  │  │  └─ models/
│  │  ├─ tests/
│  │  └─ pyproject.toml
│  └─ cli/                          # TypeScript CLI
│     ├─ src/
│     │  ├─ commands/
│     │  ├─ services/
│     │  ├─ ui/
│     │  ├─ telemetry/
│     │  └─ index.ts
│     ├─ package.json
│     └─ tsconfig.json
├─ packages/
│  ├─ contracts/                    # shared schemas / JSON schemas / DTOs
│  ├─ mapping-config/               # connector and construct mapping files
│  └─ sample-projects/              # representative Mule projects
├─ services/
│  ├─ parser/                       # Mule parsing logic
│  ├─ ir/                           # intermediate representation models/builders
│  ├─ transform/                    # Mule IR -> Logic Apps artifacts
│  ├─ validate/                     # validators, repair suggestions
│  └─ agents/                       # Microsoft Agent Framework orchestration
├─ infra/
│  ├─ bicep/
│  ├─ github-actions/
│  └─ scripts/
├─ docs/
│  ├─ architecture/
│  ├─ prompts/
│  ├─ adrs/
│  └─ runbooks/
├─ .github/
│  └─ workflows/
├─ README.md
└─ Makefile / task runner
```

---

# 3. Architecture Boundaries

## Backend
- Language: **Python 3.13**
- Framework: **FastAPI**
- Package/env management: **uv** exclusively (no pip, poetry, conda)
- Responsibilities:
  - accept Mule project **or** single flow XML input (dual-mode)
  - analyze Mule project or individual flow
  - build IR
  - run transformation pipeline
  - run validation
  - optionally invoke agent orchestration
  - produce Logic Apps Standard output artifacts (full project or standalone workflow JSON)
  - expose telemetry

## CLI
- Language: **TypeScript (latest GA)**
- UX requirements:
  - use **chalk**
  - use **emoji/icons**
  - engaging formatting
  - progress states
  - readable failures
- Responsibilities:
  - validate local project path **or** single flow XML file path
  - auto-detect input mode (directory → project, .xml file → single-flow)
  - package and submit project or flow to backend
  - display analysis/progress/results
  - write output locally if applicable
  - preserve trace context if possible

## Agent Layer
- Use **Microsoft Agent Framework**
- Agents orchestrate deterministic services:
  - analyzer
  - planner
  - transformer
  - validator
  - repair adviser

## Hosting
- Default: **Azure Container Apps**
- Use Foundry hosted agents only if later justified by a clear operational or capability benefit.

---

# 4. Delivery Phases

## Phase 0 — Foundations
Deliver working repo scaffolding, local dev environment, contracts, and CI skeleton.

## Phase 1 — Deterministic Core
Deliver Mule project parsing, IR creation, mapping config, Logic Apps project generation.

## Phase 2 — Agentic Orchestration
Add Microsoft Agent Framework orchestration around deterministic services.

## Phase 3 — Observability + Hosting
Instrument everything with OpenTelemetry and deploy to Azure Container Apps.

## Phase 4 — Production Hardening
Expand supported constructs, improve validation, repair suggestions, test coverage, and UX polish.

---

# 5. PR Plan

---

## PR-000 — GitHub Copilot / Coding Agent Artifacts ✅ COMPLETE

**Completed: 2025-04-13**

Delivered all required and optional artifacts:
- `.github/copilot-instructions.md` — project-wide instructions covering all tech stack rules, identity, testing, observability, and PR workflow conventions.
- `.github/agents/` — 5 custom agents: `bicep-infra`, `python-backend`, `typescript-cli`, `foundry-agent`, `qa`.
- `.github/skills/` — 3 domain skills: `logic-apps-standard` (project structure/schema), `mulesoft-project` (Mule XML conventions), `connector-mapping` (resolution logic/priority rules).
- Skipped IR schema skill (would be an empty placeholder until IR is designed in PR-006).
- All formats validated against VS Code Copilot customization documentation.

### Goal
Establish GitHub Copilot customization artifacts that ensure every subsequent PR benefits from project-aware AI assistance with enforced quality standards and best practices.

### Scope

**Required:**
- `.github/copilot-instructions.md` — project-wide Copilot instructions covering:
  - always read `docs/mule2logic-cli-spec.md` (product spec) and `docs/copilot-coding-agent-implementation-plan.md` (this plan) before making changes
  - Python 3.13 + `uv` only (no pip/poetry/conda)
  - TypeScript latest GA + chalk/emoji UX conventions
  - Bicep + AVM only for IaC (no Terraform/ARM/Pulumi)
  - UAMI-only identity strategy, no secrets in generated artifacts
  - built-in Logic Apps connectors preferred, identity-based auth preferred
  - testing requirements: every feature PR must include tests; Python uses pytest, TypeScript uses a standard test runner
  - linting/formatting standards for both stacks
  - structured error handling patterns
  - OpenTelemetry conventions for new spans/traces
  - living document policy: update the implementation plan when completing PRs

**Optional (as beneficial):**
- Custom Copilot agents (`.github/agents/*.md`) for specialized development areas:
  - **Bicep/Infra agent** — Azure Verified Modules expertise, Bicep best practices, resource naming conventions, UAMI role assignments
  - **Python backend agent** — FastAPI patterns, Python 3.13 features, uv workflows, pytest conventions, Pydantic models
  - **TypeScript CLI agent** — CLI UX patterns, chalk/ora usage, commander/yargs patterns, Node.js best practices
  - **Foundry/Agent Framework agent** — Microsoft Agent Framework patterns, Foundry project structure, model deployment, agent orchestration
  - **QA agent** — test strategy, golden test patterns, coverage expectations, contract test validation, edge case generation
- Custom Copilot skills (`.github/skills/*.md`) that encode reusable domain knowledge:
  - Logic Apps Standard project structure and workflow.json schema
  - MuleSoft/Anypoint project layout and XML conventions
  - Connector mapping resolution logic
  - IR schema reference

### Acceptance Criteria
- `.github/copilot-instructions.md` exists and covers all key project conventions
- Copilot suggestions in the repo respect the tech stack constraints (uv, AVM, UAMI, etc.)
- Any custom agents are invocable and scoped to their domain
- Any custom skills provide accurate, project-specific context

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
**Read `docs/copilot-coding-agent-implementation-plan.md` for the full delivery plan, toolchain decisions, and living document policy.**
Relevant spec sections: all — this PR establishes conventions for the entire project.

Implement PR-000.

Create GitHub Copilot customization artifacts for the MuleSoft to Logic Apps migration platform.

Required:
- Create `.github/copilot-instructions.md` with project-wide instructions that enforce:
  - Always read `docs/mule2logic-cli-spec.md` and `docs/copilot-coding-agent-implementation-plan.md` before making changes
  - Python 3.13 with uv exclusively (no pip, poetry, conda)
  - TypeScript latest GA for CLI
  - Bicep with Azure Verified Modules (AVM) only for IaC — no Terraform, OpenTofu, Pulumi, or ARM
  - User Assigned Managed Identity only, no secrets in generated artifacts
  - Built-in Logic Apps connectors preferred, identity-based auth preferred
  - Every feature PR must include tests (pytest for Python, appropriate runner for TypeScript)
  - Linting and formatting standards for both stacks
  - Structured error handling and OpenTelemetry conventions
  - After completing a PR, update the implementation plan to mark it complete with notes

Optional but recommended:
- Create custom Copilot agents under `.github/agents/` for specialized domains:
  - Bicep/Infrastructure (AVM expertise, UAMI, role assignments)
  - Python backend (FastAPI, uv, pytest, Pydantic)
  - TypeScript CLI (chalk, emoji, CLI UX patterns)
  - Foundry/Agent Framework (Microsoft Agent Framework, model deployment)
  - QA (test strategy, golden tests, coverage, edge cases)
- Create custom Copilot skills under `.github/skills/` for reusable domain knowledge:
  - Logic Apps Standard project structure
  - MuleSoft project layout and XML conventions
  - Connector mapping resolution
  - IR schema reference

Only create agents and skills where they provide clear value. Do not create empty placeholders.
Keep instructions concise and actionable — avoid walls of text.
```

---

## PR-001 — Monorepo Scaffolding ✅ COMPLETE

**Completed: 2026-04-13**

Delivered all scaffolding:
- Monorepo directory structure matching spec §3 layout
- Python 3.13 FastAPI backend (`apps/api`) with uv, ruff, pytest — health endpoint with test
- TypeScript CLI (`apps/cli`) with chalk/emoji banner, ESLint, Prettier, vitest — 3 passing tests
- Placeholder packages: contracts, mapping-config, sample-projects
- Placeholder services: parser, ir, transform, validate, agents
- Placeholder infra/bicep
- Placeholder docs: architecture, adrs, runbooks
- Root README with full local dev instructions (uv-based setup)
- .gitignore covering Python, Node.js, TypeScript, IDE, and OS artifacts
- No deviations from scope. API binds to configurable host/port via env vars (M2LA_HOST, M2LA_PORT).

### Goal
Create the repository structure and baseline toolchain for Python backend and TypeScript CLI.

### Scope
- Create folders
- Configure Python 3.13 project
- Configure TypeScript CLI project
- Add linting and formatting
- Add root README
- Add task runner scripts
- Add placeholder docs

### Deliverables
- backend app skeleton
- CLI app skeleton
- common package locations
- basic local run instructions

### Acceptance Criteria
- `api` starts locally
- `cli` runs locally and prints a placeholder banner
- lint and test commands exist
- repo structure matches spec

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §2 (Core Changes), §3 (Architecture), §13 (CLI UX).

Implement PR-001 for the MuleSoft to Logic Apps migration platform.

Goals:
- Create a monorepo structure with:
  - apps/api (Python 3.13 FastAPI)
  - apps/cli (TypeScript CLI)
  - packages/contracts
  - packages/mapping-config
  - packages/sample-projects
  - services/parser
  - services/ir
  - services/transform
  - services/validate
  - services/agents
  - infra/bicep
  - docs
- Configure Python 3.13 project tooling using **uv** exclusively (no pip, poetry, or conda). Use uv for venv creation, dependency resolution, locking, and installation.
- Configure TypeScript CLI tooling using latest GA TypeScript.
- Add lint/format/test scripts for both.
- Add a root README with local dev instructions (must document uv-based setup).
- The CLI should print a visually engaging placeholder banner using chalk and emoji/icons.
- Keep implementation minimal but clean and production-oriented.

Constraints:
- Do not implement business logic yet.
- Keep dependencies reasonable.
- Use clear naming and directory structure.
- Make the CLI pleasant and colorful.

Output:
- Commit-ready code for PR-001
- Update README with exact commands
- Include any assumptions in comments or docs
```

---

## PR-002 — Azure Infrastructure & CI/CD ✅ COMPLETE

**Completed: 2026-04-13**

Delivered all infrastructure and CI/CD:
- Bicep modules using AVM exclusively: identity (UAMI), monitoring (Log Analytics + App Insights), registry (ACR), container-apps (CAE + Container App), ai-foundry (hub + project + GPT-4o deployment at 50K TPM)
- Environment parameter files for dev/test/prod (`main.{dev,test,prod}.bicepparam`)
- Multi-stage Dockerfile for API using `uv` (no pip), non-root user
- GitHub Actions: PR validation (Python lint/test, TypeScript lint/test/build, Bicep validate, Docker build check), deploy workflow (OIDC, Bicep deploy, ACR cloud build, Container App update), Bicep what-if (separate workflow, only on infra changes)
- Composite action `.github/actions/setup-python-uv` for reusable Python+uv setup
- Deployment documentation (`docs/deployment.md`) with OIDC setup, manual deploy, CI/CD overview, troubleshooting
- Updated root README and infra README
- No deviations from scope. All resources use UAMI only, no secrets. OIDC federated identity for all Azure auth in CI/CD.

### Goal
Stand up production-ready Azure infrastructure and CI/CD pipelines immediately after scaffolding, so every subsequent PR can be validated, built, and deployed automatically. Infra and CI/CD land early and evolve incrementally as features are added.

### Infrastructure Scope (Bicep + AVM)

**Required resources:**
- Resource Group (will be created out of band, bicep does not need to create.  RG name will be available as env var AZURE_RESOURCE_GROUP_NAME)
- Azure Container Registry (AVM)
- Azure Container Apps Environment + Container App(s) (AVM)
- User Assigned Managed Identity (AVM)
- Log Analytics workspace (AVM)
- Application Insights connected to Log Analytics (AVM)
- Role assignments (least-privilege, UAMI-based)
- Azure AI Foundry hub + project
- Model deployment(s) for agent LLM backing
- AI Services / Cognitive Services account (as required by Foundry)

**Optional resources:**
- Key Vault (AVM, only if justified for non-generated runtime config)
- Storage account (AVM, if needed for artifact staging or state)

### CI/CD Scope (GitHub Actions)
- PR validation workflow: lint + test + build for Python and TypeScript
- Bicep what-if / validation on PR
- Deployment workflow: validate and deploy Bicep, build/push container images to ACR, deploy to Container Apps
- OIDC / federated identity for Azure auth — minimize stored secrets
- Environment-specific configuration (dev/test/prod)

### Acceptance Criteria
- Bicep deploys cleanly from a single `az deployment` or CI workflow
- all modules use Azure Verified Modules (AVM) where available; raw Bicep only when no AVM exists
- API can run in Container Apps using UAMI
- Foundry hub, project, and at least one model deployment are provisioned
- observability is wired (App Insights + Log Analytics)
- no secret-based auth for app identity
- environment parameterization supports dev/test/prod
- PR workflow runs lint + test + build for both Python and TypeScript
- deploy workflow can push to Azure
- pipelines are structured for incremental extension as features land

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §8 (Identity), §10 (Hosting), §11 (Infra), §12 (CI/CD).

Implement PR-002.

Build Azure infrastructure as code AND CI/CD pipelines for the platform. Infra and CI/CD land early so every subsequent PR can be validated, built, and deployed automatically.

**Infrastructure (Bicep + AVM):**
- Use **Bicep** with **Azure Verified Modules (AVM)** exclusively. Only fall back to raw Bicep when no AVM exists for a required service or configuration. Do not use Terraform, OpenTofu, Pulumi, or ARM templates.
- Provision core resources:
  - Resource Group
  - Azure Container Registry
  - Azure Container Apps Environment
  - Container App(s) for backend (and frontend/API gateway if appropriate)
  - User Assigned Managed Identity
  - Log Analytics workspace
  - Application Insights (connected to Log Analytics)
  - Least-privilege role assignments for UAMI
  - Azure AI Foundry hub + project
  - Model deployment(s) for agent LLM backing
  - AI Services / Cognitive Services account (as required by Foundry)
- Design for User Assigned Managed Identity only.
- No secret-based auth for app identity.
- Add environment parameterization for dev/test/prod.

**CI/CD (GitHub Actions):**
- PR validation workflow:
  - lint (Python + TypeScript)
  - test (Python + TypeScript)
  - build (Python + TypeScript)
  - Bicep what-if / validation
- Deployment workflow:
  - validate and deploy Bicep
  - build backend container image
  - push images to ACR
  - deploy to Azure Container Apps
  - build/publish CLI package if needed
- Use modern GitHub Actions patterns (reusable workflows, composite actions where useful).
- Prefer OIDC / federated identity for Azure auth — minimize stored secrets.
- Use **uv** for Python CI steps (install, test, lint). No pip.
- Document required repo secrets, environments, and OIDC setup.

Start lean — infra and pipelines will evolve incrementally as features land. Later PRs will add pipeline steps and Bicep modules for new services.

Keep everything modular and production-oriented.
Add deployment docs.
```

---

## PR-003 — Shared Contracts and JSON Schemas ✅ COMPLETE

> **Completed**: 2026-04-13. Delivered as planned. Python Pydantic models as source of truth, generated JSON schemas, hand-authored TypeScript interfaces. 92 Python tests + 11 TypeScript tests. Wired into apps/api (path dependency) and apps/cli (@m2la/contracts). CI updated with contracts-specific jobs.

### Goal
Define DTOs and schemas for analysis, transformation, validation, and output packaging.

### Scope
- create request/response contracts
- JSON schemas for:
  - analyze request (must support both project mode and single-flow mode)
  - analyze result
  - transform request (must support both project mode and single-flow mode)
  - transform result
  - validation report
  - migration gap
- define severity levels
- include an input mode discriminator (project vs. single-flow) in request schemas

### Acceptance Criteria
- backend and CLI can import shared contract definitions or generated schemas
- schema validation passes for sample payloads

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §4 (Input Contract), §5 (Output Contract), §7 (Supported Constructs), §9 (Observability).

Implement PR-003.

Create shared contracts for the platform:
- analyze request/response
- transform request/response
- validation report
- migration gaps
- artifact manifest
- telemetry correlation metadata

Requirements:
- Use a clean schema-first or DTO-first pattern that works well across Python backend and TypeScript CLI.
- Request schemas must support two input modes:
  - **Project mode**: full MuleSoft project root (directory path, contains pom.xml + flows)
  - **Single-flow mode**: individual Mule flow XML file path
  - Include a mode discriminator field and/or auto-detect logic based on input path
- Response schemas must accommodate both modes:
  - Project mode: multi-flow analysis, full project artifact manifest
  - Single-flow mode: single workflow result, warnings about missing external context
- Include fields for:
  - trace IDs / correlation IDs
  - warnings and gaps
  - supported/unsupported construct counts
  - output artifact summary
- Add example payloads and contract tests.

Keep the contracts stable and easy to extend.
Do not yet implement parser/transform logic.
```

---

## PR-004 — Backend API Skeleton ✅ COMPLETE

> **Completed 2026-04-13.** All routes (health, analyze, transform, validate) implemented as FastAPI routers with auto-detect input mode. Added `ValidateRequest` to contracts package (Python + TypeScript + JSON schema). Config via `pydantic-settings`, structured `ErrorResponse`/`ApiError` error handling. 26 API tests passing. No deviations from scope.

### Goal
Stand up FastAPI routes and application configuration.

### Scope
- `/health`
- `/analyze` (accepts project path or single flow XML)
- `/transform` (accepts project path or single flow XML)
- `/validate`
- configuration system
- structured error model
- auto-detect input mode from path (directory → project, .xml file → single-flow)

### Acceptance Criteria
- API starts
- OpenAPI docs render
- endpoints return placeholder structured responses

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §3 (Architecture), §4 (Input Contract), §5 (Output Contract).

Implement PR-004.

Build the FastAPI backend skeleton for the migration platform.
Use **uv** exclusively for Python environment and dependency management (no pip).

Requirements:
- Python 3.13
- Add routes:
  - GET /health
  - POST /analyze
  - POST /transform
  - POST /validate
- Routes that accept input (analyze, transform) must support **both** input modes:
  - **Project mode**: path to a MuleSoft project root directory
  - **Single-flow mode**: path to a single Mule flow XML file
  - Auto-detect mode from the input path (directory vs. .xml file), or accept an explicit mode parameter
- Use shared request/response contracts.
- Add clean config loading.
- Add structured error responses.
- Organize code under apps/api/src in a maintainable way.

Do not implement full domain logic yet.
Use placeholders that conform to the contracts.
Add tests for route availability and response shape.
```

---

## PR-005 — CLI Skeleton with Polished UX ✅ COMPLETE

**Completed: 2026-04-13**

Delivered as planned. Added commander for CLI framework, ora for spinners, fast-xml-parser for XML validation. Implemented three commands (analyze, transform, validate) with auto-detection of project vs single-flow mode. Input validation checks pom.xml + src/main/mule/ for project mode and <flow>/<sub-flow> elements for single-flow mode. Backend URL configurable via --backend-url flag or M2LA_BACKEND_URL env var. Colorful output with chalk, emoji/icons, progress spinners, and structured error handling with CliError class. 36 tests (config, input-detector, input-validator, commands, output, banner). No deviations from scope.

### Goal
Build a polished TypeScript CLI shell.

### Scope
- commands:
  - `analyze` (project path or single flow XML file)
  - `transform` (project path or single flow XML file)
  - `validate`
- auto-detect input mode (directory → project mode, .xml file → single-flow mode)
- path validation appropriate to each mode
- colorful output
- emoji/icons
- progress spinners or status display
- config for backend URL

### Acceptance Criteria
- CLI help works
- command structure is intuitive
- project mode: validates that input path is a Mule project root
- single-flow mode: validates that input path is a .xml file containing Mule flow elements
- CLI clearly indicates which mode is active

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §4 (Input Contract), §13 (CLI UX).

Implement PR-005.

Build a polished TypeScript CLI for the migration platform.

Requirements:
- Use latest GA TypeScript
- Add commands:
  - analyze <inputPath>
  - transform <inputPath>
  - validate <outputPath>
- `inputPath` can be either a MuleSoft project root directory or a single Mule flow XML file.
- The CLI must auto-detect input mode:
  - directory → project mode
  - .xml file → single-flow mode
- The CLI must feel engaging:
  - use chalk for colors
  - use emoji/icons
  - show progress states
  - use clear section headers and readable status summaries
- Validate input based on detected mode:
  - **Project mode**: must include pom.xml and Mule config locations typical of a Mule project
  - **Single-flow mode**: must be a valid XML file containing at least one `<flow>` or `<sub-flow>` element
- Clearly indicate which mode is active in CLI output
- Add configuration for backend endpoint
- Return friendly errors

Do not make the CLI depend on transformation logic yet beyond calling placeholder endpoints.
```

---

## PR-006 — Mule Project Discovery and Parsing ✅ COMPLETE

> **Completed**: 2026-04-13. Delivered as planned. Used `defusedxml` for safe XML parsing (addresses XML bomb/entity expansion attacks). `db:config` (bare `config` local name) is detected as a global config element. 35 tests covering both project and single-flow modes. No deviations from scope. Follow-up: IR generation (PR-007) will consume `ProjectInventory` from this parser.

### Goal
Parse a valid Mule project **or** a single Mule flow XML file.

### Scope
- **Project mode:**
  - identify project root
  - parse `pom.xml`
  - discover flow XML files
  - discover config files
  - build a normalized project inventory
- **Single-flow mode:**
  - parse a standalone Mule XML file
  - extract flows/subflows from the file
  - emit warnings for unresolvable external references (connector configs, properties, global elements)
  - produce a minimal inventory (single file, no project metadata)

### Acceptance Criteria
- project mode: analyzer can produce a project inventory from sample projects
- project mode: inventory includes flows, subflows, configs, connectors, properties files, key metadata
- single-flow mode: analyzer can parse a standalone flow XML and extract flows/subflows
- single-flow mode: missing external references produce structured warnings, not failures

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §4 (Input Contract), §7 (Supported Constructs).

Implement PR-006.

Build MuleSoft/Anypoint project discovery and parsing.

Requirements:
- Support two input modes:

**Project mode** (input is a directory):
- Input is a Mule project root, not an arbitrary folder of flows.
- Parse:
  - pom.xml
  - src/main/mule/**/*.xml
  - relevant config/property files if present
- Build a normalized project inventory model including:
  - project metadata
  - Mule XML files discovered
  - flows
  - subflows
  - global elements
  - referenced connector configs
  - property files
- Handle malformed files gracefully and emit structured warnings.

**Single-flow mode** (input is a .xml file):
- Parse the standalone Mule XML file.
- Extract all `<flow>` and `<sub-flow>` elements.
- Build a minimal inventory with no project metadata (no pom.xml, no config discovery).
- Emit structured warnings for any unresolvable external references (connector configs, property placeholders, global elements defined outside the file).
- Do not fail on missing external context — degrade gracefully.

Add representative tests for both modes using sample Mule projects and standalone flow XML files.
```

---

## PR-007 — Intermediate Representation (IR) v1 ✅ COMPLETE

> **Completed**: 2026-04-13. Delivered IR v1 at `services/ir/` with 74 tests across 6 modules. All IR entities implemented as Pydantic models with discriminated union FlowStep type. JSON serialization roundtrip is lossless. Builder helpers provide convenient construction for tests and future parser integration. Message state tracking deferred to a follow-up (config dicts on nodes can carry this later). No deviations from scope.

### Goal
Create a canonical, deterministic Mule IR.

### Scope
- IR entities:
  - project
  - flow
  - subflow
  - trigger
  - processor
  - router
  - scope
  - variable mutation
  - transform
  - error handler
  - connector operation
- message state tracking basics
- project analysis summary

### Acceptance Criteria
- a parsed Mule project can be converted to IR v1
- a single parsed flow XML can be converted to IR v1 (with warnings for missing context)
- IR can be serialized to JSON
- IR tests cover at least 3 sample flows with branching and transforms
- IR tests include at least 1 single-flow-mode case

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §3 (Architecture — IR Engine), §7 (Supported Constructs).

Implement PR-007.

Create IR v1 for the migration platform.

Requirements:
- Build a deterministic intermediate representation for Mule projects.
- The IR must represent:
  - project metadata
  - flows/subflows
  - triggers
  - processors
  - routers
  - scopes
  - variable operations
  - transforms
  - connector operations
  - error handlers
- Include enough detail to support later transformation into Logic Apps Standard.
- Provide JSON serialization for debugging and tests.
- Add tests for representative Mule patterns:
  - HTTP listener + transform + outbound call
  - scheduler + loop
  - choice router + error handling
  - standalone single-flow XML (no project context)

The IR must be practical and extensible, not academic.
The IR must work for both project mode (full inventory) and single-flow mode (partial inventory with warnings).
```

---

## PR-008 — Externalized Connector and Construct Mapping Config

### Goal
Move mapping logic into data-driven config.

### Scope
- `connector_mappings.yaml`
- `construct_mappings.yaml`
- ranking rules:
  1. built-in connectors first
  2. identity-based auth first
  3. managed/api connectors last resort
- indicate MVP-supported constructs

### Acceptance Criteria
- mapping files load successfully
- config model can resolve preferred connector mapping for known Mule constructs
- tests verify preference rules

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §6 (Connector Strategy), §7 (Supported Constructs).

Implement PR-008.

Create externalized mapping configuration for MuleSoft -> Logic Apps conversion.

Requirements:
- Add config files, e.g. YAML, for:
  - connector mappings
  - construct mappings
  - auth preferences
- Rules must favor:
  1. Logic Apps built-in connectors
  2. identity-based authorization
  3. managed/API connectors only as a last resort
- Include mappings for an expanded MVP set, including at least:
  - HTTP
  - scheduler
  - file/FTP/SFTP
  - SQL/database
  - Service Bus / messaging
  - storage
  - common control flow constructs
- Expose a Python service that loads and resolves mappings.
- Add tests for ranking behavior and unsupported cases.
```

---

## PR-009 — Logic Apps Standard Project Generator v1 ✅ COMPLETE

**Completed**: 2026-04-14. Implemented `m2la_transform` package at `services/transform/` with full project-mode generation (host.json, connections.json, parameters.json, .env, workflows/) and single-flow mode. 40 pytest tests pass. No deviations from spec. Follow-up: PR-010 adds full construct transformation and golden tests.

### Goal
Generate a valid Logic Apps Standard project structure from IR for supported cases.

### Scope
- when converting a full Mule project:
  - generate valid directory structure
  - `host.json`
  - `connections.json`
  - `parameters.json`
  - `.env` with required variables and mock values
  - `workflows/<name>/workflow.json` or equivalent valid structure
- when converting a single flow:
  - generate only workflow JSON
- use UAMI placeholders/config

### Acceptance Criteria
- project output structure is valid and consistent
- generated files are deterministic
- output includes no secrets
- `.env` uses mock values/placeholders only

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §5 (Output Contract), §6 (Connector Strategy), §8 (Identity).

Implement PR-009.

Build Logic Apps Standard project generation v1.

Requirements:
- Input: IR + mapping resolution
- Output for full project conversion:
  - valid Logic Apps Standard project structure
  - host.json
  - connections.json
  - parameters.json
  - .env containing all required env vars with mock values/placeholders only
  - workflow files in a valid project layout
- Output for single-flow conversion:
  - only workflow JSON
- Always design for User Assigned Managed Identity.
- No secrets in generated artifacts.
- Keep generation deterministic and testable.

Include tests that verify:
- expected file layout
- file content shape
- no secrets
- stable output for repeated runs
```

---

## PR-010 — Supported Construct Transformations v1

### Goal
Implement actual conversion for a solid MVP set.

### Minimum supported constructs
- HTTP Listener → Request trigger
- Scheduler → Recurrence
- Flow reference / subflow call → Scope or internal workflow strategy
- Set payload
- Set variable
- Choice router
- For each
- Scatter-gather to parallel branches
- Basic DataWeave patterns
- HTTP outbound
- File / FTP / SFTP
- SQL/database operation
- Messaging to Service Bus
- Basic error handling via scopes/runAfter

### Acceptance Criteria
- conversion works for representative sample projects (project mode)
- conversion works for standalone flow XML files (single-flow mode)
- unsupported constructs create explicit migration gaps, not silent drops

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §6 (Connector Strategy), §7 (Supported Constructs), §8 (Identity).

Implement PR-010.

Add supported construct transformations v1.

Requirements:
- Convert a meaningful MVP set, including:
  - HTTP listener
  - scheduler
  - flow references/subflows
  - set payload
  - set variable
  - choice router
  - foreach
  - scatter-gather
  - basic DataWeave patterns
  - outbound HTTP
  - file/FTP/SFTP
  - SQL/database
  - messaging mapped to Service Bus where appropriate
  - basic error handling via scopes and runAfter
- Emit explicit migration gaps for unsupported features.
- Never silently drop behavior.
- Prefer maintainable Logic Apps structures that preserve semantics.

Add golden tests using sample Mule projects and compare generated artifacts against approved outputs where practical.
Include at least one golden test for single-flow mode (standalone XML → standalone workflow JSON).
```

---

## PR-011 — Validation Engine v1

### Goal
Add deterministic validation before and after generation.

### Scope
- validate Mule project input completeness (project mode)
- validate single-flow XML input (single-flow mode)
- validate IR consistency
- validate generated Logic Apps artifact integrity
- validate:
  - action reference integrity
  - runAfter references
  - variable usage
  - presence of expected files (project mode only)
  - parameter placeholder completeness
  - identity/auth strategy warnings
  - unresolvable external references in single-flow mode (emit warnings, not failures)

### Acceptance Criteria
- validator produces structured report
- failures are categorized by severity
- transform endpoint can optionally run validation automatically

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §4 (Input Contract), §5 (Output Contract), §6 (Connector Strategy), §8 (Identity), §15 (Acceptance Criteria).

Implement PR-011.

Build the validation engine v1.

Requirements:
- Validate:
  - Mule project completeness (project mode)
  - Single-flow XML validity (single-flow mode)
  - IR integrity
  - generated Logic Apps project integrity (project mode)
  - generated standalone workflow JSON integrity (single-flow mode)
- Checks should include:
  - missing references
  - invalid runAfter references
  - missing variables
  - malformed file layout
  - missing placeholder env vars
  - use of a managed/API connector when a built-in or identity-based option should have been preferred
- Emit structured validation reports with severity levels and remediation hints.
- In single-flow mode, unresolvable external references (connector configs, properties) should produce warnings, not hard failures.

Add tests for both passing and failing cases in both project mode and single-flow mode.
```

---

## PR-012 — Microsoft Agent Framework Orchestration

### Goal
Wrap deterministic services in agentic orchestration.

### Agents
- AnalyzerAgent
- PlannerAgent
- TransformerAgent
- ValidatorAgent
- RepairAdvisorAgent

### Scope
- the agents should **call deterministic services**
- not replace them
- maintain trace context
- provide reasoning summaries without exposing hidden chain-of-thought
- produce structured orchestration output

### Acceptance Criteria
- orchestration can run analyze → plan → transform → validate sequence
- deterministic services remain primary execution path

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §3 (Architecture — Agent Orchestrator), §10 (Hosting).

Implement PR-012.

Add Microsoft Agent Framework orchestration around the deterministic migration services.

Requirements:
- Create specialized agents:
  - AnalyzerAgent
  - PlannerAgent
  - TransformerAgent
  - ValidatorAgent
  - RepairAdvisorAgent
- The agents should orchestrate deterministic code paths rather than replacing them.
- Preserve structured outputs and correlation IDs.
- Keep the design extensible for future MCP integrations.
- Do not rely on giant prompts for core logic.
- Add tests or integration harnesses for the orchestration flow.

Document clearly where deterministic logic ends and agent orchestration begins.
```

---

## PR-013 — MCP Tool Integration Abstractions

### Goal
Prepare tool interfaces for grounding and future capability expansion.

### Scope
- abstract tool provider interface
- Logic Apps grounding provider
- MuleSoft grounding provider
- result normalization
- retry/timeouts
- caching hooks if useful

### Acceptance Criteria
- backend can call through abstractions even with mocked providers
- orchestration layer can consume provider outputs

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §3 (Architecture), §6 (Connector Strategy).

Implement PR-013.

Create abstractions for grounding/tool providers.

Requirements:
- Add provider interfaces for external grounding sources.
- Prepare implementations/adapters suitable for:
  - Logic Apps documentation grounding
  - MuleSoft documentation grounding
- Normalize tool results into a common format.
- Add timeout/error handling.
- Keep the design easy to mock in tests.
- Do not hard-code business logic into provider adapters.

This PR is primarily about clean interfaces and extension points.
```

---

## PR-014 — OpenTelemetry End-to-End Instrumentation

### Goal
Implement end-to-end observability across CLI, backend, and agent orchestration.

### Scope
- OpenTelemetry in CLI
- OpenTelemetry in FastAPI
- spans for parser/IR/transform/validate/orchestrate
- propagation of trace context
- Azure Monitor / App Insights exporter config
- structured logs correlated with traces

### Acceptance Criteria
- trace context flows from CLI to backend
- backend spans show major pipeline stages
- exporters configurable via env vars
- docs included

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §9 (Observability).

Implement PR-014.

Add end-to-end OpenTelemetry instrumentation.

Requirements:
- Instrument:
  - TypeScript CLI
  - Python FastAPI backend
  - parser
  - IR builder
  - transform engine
  - validation engine
  - agent orchestration
- Propagate correlation/trace context from CLI to backend.
- Configure exporters for Azure Monitor / Application Insights.
- Add structured logging correlated with traces.
- Provide local-dev-friendly defaults and docs.

Keep the implementation production-oriented and easy to extend.
```

---

## PR-015 — UX Polish and Rich CLI Output

### Goal
Make the CLI delightful and informative.

### Scope
- summary cards
- colored risk/warning sections
- migration gap reporting
- file generation summary
- validation summary
- pretty formatting
- emoji/icons
- maybe optional verbose mode

### Acceptance Criteria
- CLI output is attractive and readable
- warnings/failures are obvious
- success output includes next steps

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §13 (CLI UX).

Implement PR-015.

Polish the TypeScript CLI UX.

Requirements:
- Make the CLI feel engaging and premium:
  - use chalk colors tastefully
  - use emoji/icons
  - use clean section formatting
  - highlight warnings, risks, and success clearly
- Add summaries for:
  - project analysis
  - supported vs unsupported constructs
  - files generated
  - validation results
  - next steps
- Keep output readable in both normal and verbose modes.

Avoid making it noisy or gimmicky.
```

---

## PR-016 — Expanded MVP Connector Coverage

### Goal
Expand supported mappings and test coverage.

### Suggested additions
- Azure Storage mappings
- SMB/file patterns where feasible
- basic email or webhook patterns if relevant
- JMS-like messaging cases mapped cautiously
- API-led HTTP patterns
- richer SQL operations
- common property/config reference patterns

### Acceptance Criteria
- mapping config expanded
- test matrix expanded
- unsupported cases remain explicit

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §6 (Connector Strategy), §7 (Supported Constructs).

Implement PR-016.

Expand the MVP mapping and connector support.

Requirements:
- Add more supported mappings and related tests.
- Favor built-in Logic Apps connectors and identity-based auth wherever possible.
- Managed/API connectors are fallback only.
- Update mapping config and transformation logic together.
- Add representative sample Mule projects or focused fixtures.

Do not overclaim support. Unsupported or ambiguous constructs must remain explicit migration gaps.
```

---

## PR-017 — Repair Suggestions and Guided Remediation

### Goal
Help users recover from partial migrations.

### Scope
- suggest manual fixes
- identify missing env vars
- explain unsupported constructs
- recommend connector follow-up steps
- produce a migration report

### Acceptance Criteria
- partial migrations have actionable next steps
- report is structured and readable

### Prompt for Copilot Coding Agent
```text
**Read `docs/mule2logic-cli-spec.md` first. It is the authoritative product spec. If this prompt and the spec conflict, the spec wins.**
Relevant spec sections: §7 (Supported Constructs), §15 (Acceptance Criteria).

Implement PR-017.

Add guided remediation and repair suggestions.

Requirements:
- When migration is partial or validation fails, produce:
  - actionable remediation items
  - missing config/env guidance
  - unsupported construct summaries
  - connector follow-up suggestions
- Output should be structured for both API and CLI display.
- Keep suggestions practical and specific.

This is advisory output, not automatic rewriting yet.
```

---

# 6. Suggested Backlog Beyond MVP

## High-value follow-ons
- stronger DataWeave translation
- child workflow generation strategy
- richer error-handler fidelity
- policy and retry mapping
- environment overlays
- VS Code extension
- batch migration mode
- golden-output approval test framework
- sample migration cookbook
- project diff visualizer
- post-generation deploy validation against Azure resources

---

# 7. Definition of Done for MVP

The MVP is done when all of the following are true:

1. A user can point the CLI at a valid MuleSoft/Anypoint project root.
2. The platform analyzes the project and produces a structured summary.
3. For supported constructs, the platform generates a valid Logic Apps Standard project structure including:
   - `host.json`
   - `connections.json`
   - `parameters.json`
   - `.env` with mock values/placeholders
   - valid workflow JSON files
4. Single-flow conversion can generate workflow JSON without extra project scaffolding.
5. User Assigned Managed Identity is the default and only identity strategy.
6. Built-in connectors and identity-based authorization are preferred.
7. Validation catches structural issues and reports migration gaps.
8. CLI output is polished and readable.
9. OpenTelemetry traces flow end-to-end.
10. The solution can be deployed to Azure Container Apps using IaC and CI/CD.

---

# 8. Guidance for Human Reviewers

When reviewing Copilot-generated PRs, verify:

- Is deterministic logic being implemented in code instead of hidden in prompts?
- Are mappings externalized?
- Is UAMI consistently enforced?
- Are built-in connectors preferred correctly?
- Is the Logic Apps project structure actually valid?
- Are `.env` contents placeholders only?
- Are unsupported constructs explicitly surfaced?
- Is telemetry wired through every major layer?
- Is the CLI polished without being cluttered?
- Are tests meaningful and representative?

---

# 9. Recommended Copilot Operating Instructions

Use these instructions when assigning work to GitHub Copilot Coding Agent:

```text
You are implementing a production-oriented migration platform.

Priorities:
1. correctness
2. maintainability
3. deterministic behavior
4. observability
5. polished UX

Important rules:
- Do not collapse the architecture into one oversized module.
- Keep parsing, IR, transform, validate, agent orchestration, and UI concerns separate.
- Prefer simple, testable code over clever abstractions.
- Favor built-in Logic Apps connectors and identity-based auth.
- Use User Assigned Managed Identity consistently.
- Do not introduce secrets into generated artifacts.
- Externalize mappings to config where practical.
- Use **uv** exclusively for Python environment and dependency management. Never use pip, pip-tools, poetry, or conda.
- Use **Bicep with Azure Verified Modules (AVM)** for all infrastructure. Raw Bicep only when no AVM exists.
- Add tests with each feature.
- Update docs when behavior changes.
- Be honest about unsupported areas and surface them explicitly.
- After completing each PR, update `docs/copilot-coding-agent-implementation-plan.md`: mark the PR as complete, add a brief completion note, and note any deviations or follow-ups.
- Before starting a PR, re-read its section in the implementation plan — requirements may have been updated since the plan was first written.
```

---

# 10. Recommended Build Order for Fastest Visible Progress

Infra and CI/CD land immediately after scaffolding (PR-002) so every subsequent PR can be validated, built, and deployed automatically. Each later PR incrementally extends the Bicep modules and pipeline steps as needed.

1. PR-000 — GitHub Copilot / Coding Agent artifacts
2. PR-001 — Monorepo scaffolding
3. PR-002 — Azure infra + CI/CD (Bicep + AVM + GitHub Actions)
4. PR-003 — Shared contracts
5. PR-004 — Backend API skeleton
6. PR-005 — CLI skeleton with polished UX
7. PR-006 — Mule project parser
8. PR-007 — IR v1
9. PR-008 — Connector mapping config
10. PR-009 — Logic Apps project generator
11. PR-010 — Supported construct transformations
12. PR-011 — Validation engine
13. PR-012 — Agent orchestration
14. PR-013 — MCP tool abstractions
15. PR-014 — OpenTelemetry instrumentation
16. PR-015 — UX polish
17. PR-016 — Expanded connector coverage
18. PR-017 — Repair suggestions

Reason:
- Infra and CI/CD land immediately after scaffolding so every subsequent PR can be validated, built, and deployed automatically.
- Each later PR incrementally extends the Bicep modules and pipeline steps as needed.
- You get a working CLI and API early.
- You get project parsing and IR before transformation.
- You get generation and validation before complex agent orchestration.
- You delay risky agent/tool integration until the deterministic platform already works.

---

# 11. Final Recommendation

Do **not** ask Copilot Coding Agent to “build the whole platform.”
Assign one PR at a time from this document.

The best first three PRs to request immediately are:
- PR-000 GitHub Copilot / Coding Agent artifacts (sets quality baseline for everything after)
- PR-001 Monorepo scaffolding
- PR-002 Azure infra + CI/CD (AVM Bicep + Foundry + GitHub Actions pipelines)

That gives you AI-assisted development from the first keystroke, a repo structure, deployable infrastructure, and automated pipelines. Follow with PR-003 (contracts), PR-004 (API), and PR-005 (CLI) to start building application code.
