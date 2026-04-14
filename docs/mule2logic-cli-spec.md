# MuleSoft to Logic Apps Standard Migration Agent - Revised Product Spec

## 1. Overview
This product converts MuleSoft (Anypoint) projects into Azure Logic Apps Standard projects using an agentic architecture.

## 2. Core Changes (Revision Summary)
- Backend: Python 3.13
- Python toolchain: **uv** exclusively (no pip, pip-tools, poetry, or conda). Use uv for venv creation, dependency resolution, locking, and installation.
- Frontend/CLI UX: TypeScript (latest GA) with rich terminal UI (chalk, emojis, icons)
- Input: Full MuleSoft project (pom.xml + flows) **or** a single Mule flow XML file
- Output: Full Logic Apps Standard project structure (connections.json, host.json, parameters.json, .env) **or** standalone workflow JSON (single-flow mode)
- Hosting: Azure Container Apps (default)
- Identity: User Assigned Managed Identity ONLY
- Observability: OpenTelemetry + Azure Monitor + App Insights (end-to-end)
- Connector preference: Built-in + identity-based auth first
- Infra + CI/CD included
- Expanded supported constructs + externalized mappings

---

## 3. Architecture

### Components
- **CLI** (TypeScript) — validates input, submits to API, displays results
- **API Layer** (Python FastAPI) — receives requests, manages Foundry client lifecycle, delegates to Agent Orchestrator
- **Agent Orchestrator** (Microsoft Agent Framework) — the core execution engine. All API requests flow through LLM-backed agents composed into a `SequentialBuilder` workflow via `FoundryChatClient`. Five specialized agents (Analyzer, Planner, Transformer, Validator, RepairAdvisor) each call deterministic tool functions.
- **Azure AI Foundry** — required dependency providing LLM backing (e.g., GPT-4o) for all agent operations. Not optional.
- **Deterministic Tool Functions** (Python) — parsing, IR generation, mapping resolution, transformation, and validation implemented as testable Python functions. Agents invoke these as tools — the LLM decides when and how to call them.

### Request Flow
```
CLI → API → Agent Orchestrator → LLM (Foundry) → Tool Calls → Structured Response
```

---

## 4. Input Contract

The platform supports two input modes. Both are **hard requirements** for MVP.

### Project Mode (default)
CLI accepts a path to a MuleSoft project root.
- Must contain:
  - pom.xml
  - src/main/mule/*.xml
  - configs

### Single-Flow Mode
CLI accepts a path to an individual Mule flow XML file.
- The file must be a valid Mule XML containing at least one `<flow>` or `<sub-flow>` element.
- No pom.xml or project structure required.
- Connector configs and property references outside the file are unavailable — the platform must emit warnings for unresolvable references rather than failing.
- Output is a standalone workflow JSON (no host.json, connections.json, etc.).

The CLI and API must auto-detect the mode from the input path (directory → project mode, `.xml` file → single-flow mode), or accept an explicit flag/parameter to override.

---

## 5. Output Contract

### Project Conversion Output
- /logicapp/
  - host.json
  - connections.json
  - parameters.json
  - .env (mock values)
  - workflows/
    - <workflow>.json

### Single Flow Output
- Only workflow JSON

---

## 6. Connector Strategy

Priority:
1. Built-in connectors
2. Identity-based auth
3. Managed/API connectors (last resort)

Mappings stored in:
- config/connector_mappings.yaml

Example:
http: HTTP built-in
ftp: SFTP built-in
mq: Service Bus
db: SQL built-in

---

## 7. Supported Constructs (MVP Expanded)

- HTTP Listener -> Request Trigger
- Scheduler -> Recurrence
- Flow Ref -> Scope
- Choice Router -> Condition/Switch
- For Each -> Foreach
- Scatter Gather -> Parallel branches
- DataWeave -> Expressions / Inline Code
- MQ -> Service Bus
- FTP/SFTP -> Built-in connectors
- DB -> SQL built-in
- Error Handlers -> Scopes + runAfter

---

## 8. Identity

- Always use User Assigned Managed Identity
- No secrets allowed
- .env contains placeholders only

---

## 9. Observability

End-to-end OpenTelemetry:
- CLI traces
- API traces
- Agent traces
- Export to Azure Monitor + App Insights

---

## 10. Hosting

Runtime:
- **Azure Container Apps** for the API backend

LLM Backing:
- **Azure AI Foundry** is a required dependency — provides the LLM (e.g., GPT-4o) that powers all agent operations
- The API connects to Foundry via `FoundryChatClient` using UAMI credentials
- Configured via `M2LA_FOUNDRY_ENDPOINT` and `M2LA_FOUNDRY_MODEL` env vars

---

## 11. Infra (IaC)

Tooling:
- **Bicep** with **Azure Verified Modules (AVM)** exclusively. Only fall back to raw Bicep when no AVM exists for a required service or configuration.
- Do not use Terraform, OpenTofu, Pulumi, or ARM templates.

Required resources:
- Resource Group
- Azure Container Registry
- Azure Container Apps Environment + Container App(s)
- User Assigned Managed Identity
- Log Analytics workspace
- Application Insights (connected to Log Analytics)
- Role assignments (least-privilege, UAMI-based)
- Azure AI Foundry hub + project
- Model deployment(s) for agent LLM backing
- AI Services / Cognitive Services account (as required by Foundry)

Optional resources:
- Key Vault (only if justified for non-generated runtime config)
- Storage account (if needed for artifact staging or state)

---

## 12. CI/CD

GitHub Actions:
- Build
- Test
- Lint
- Deploy infra
- Deploy containers

---

## 13. CLI UX (TypeScript)

Features:
- Colored output (chalk)
- Emojis/icons
- Progress bars
- Sections:
  🔍 Analyzing project / flow
  🧠 Planning migration
  ⚙️ Converting flows
  ✅ Validating output
- Single-flow mode must clearly indicate it is operating on a single file, warn about missing external context (connector configs, properties), and output only workflow JSON.

---

## 14. Milestones

MVP:
1. Project parsing
2. IR generation
3. Basic conversion
4. Project output structure
5. CLI UX

V2:
- More connectors
- Better DataWeave support
- Repair loop

---

## 15. Acceptance Criteria

- Valid Logic Apps project output (project mode)
- Valid standalone workflow JSON output (single-flow mode)
- Both modes are functional and tested in MVP
- Deployable to Azure
- No secrets used
- Observability enabled
- CLI is user-friendly

