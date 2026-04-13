# MuleSoft to Logic Apps Standard Migration Agent - Revised Product Spec

## 1. Overview
This product converts MuleSoft (Anypoint) projects into Azure Logic Apps Standard projects using an agentic architecture.

## 2. Core Changes (Revision Summary)
- Backend: Python 3.13
- Python toolchain: **uv** exclusively (no pip, pip-tools, poetry, or conda). Use uv for venv creation, dependency resolution, locking, and installation.
- Frontend/CLI UX: TypeScript (latest GA) with rich terminal UI (chalk, emojis, icons)
- Input: Full MuleSoft project (pom.xml + flows)
- Output: Full Logic Apps Standard project structure (connections.json, host.json, parameters.json, .env)
- Hosting: Azure Container Apps (default)
- Identity: User Assigned Managed Identity ONLY
- Observability: OpenTelemetry + Azure Monitor + App Insights (end-to-end)
- Connector preference: Built-in + identity-based auth first
- Infra + CI/CD included
- Expanded supported constructs + externalized mappings

---

## 3. Architecture

### Components
- CLI (TypeScript)
- API Layer (Python FastAPI)
- Agent Orchestrator (Microsoft Agent Framework)
- Optional Foundry Agents (only if needed)
- IR Engine (Python)
- Validator Engine (Python)

---

## 4. Input Contract

CLI accepts:
- Path to MuleSoft project root
- Must contain:
  - pom.xml
  - src/main/mule/*.xml
  - configs

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

Default:
- Azure Container Apps

Foundry Agents:
- Only used if orchestration requires it

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
  🔍 Analyzing project
  🧠 Planning migration
  ⚙️ Converting flows
  ✅ Validating output

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

- Valid Logic Apps project output
- Deployable to Azure
- No secrets used
- Observability enabled
- CLI is user-friendly

