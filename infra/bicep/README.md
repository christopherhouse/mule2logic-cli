# Infrastructure as Code (Bicep)

Azure infrastructure for the **MuleSoft → Logic Apps Standard Migration Platform**, authored in Bicep with [Azure Verified Modules (AVM)](https://aka.ms/avm).

## Architecture

```text
┌────────────────────────────────────────────────────────────────┐
│  Resource Group (created out-of-band)                          │
│                                                                │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Log Analytics │──│ Application      │  │ User Assigned    │ │
│  │ Workspace     │  │ Insights         │  │ Managed Identity │ │
│  └──────────────┘  └──────────────────┘  └───────┬──────────┘ │
│                                                   │            │
│  ┌──────────────┐  ┌──────────────────┐           │            │
│  │ Container    │  │ Container Apps   │           │ AcrPull    │
│  │ Registry     │◄─│ Environment      │           │ + OpenAI   │
│  │ (ACR)        │  │  └─ Container App│◄──────────┘ User       │
│  └──────────────┘  └──────────────────┘                        │
│                                                                │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ AI Services  │──│ AI Foundry Hub   │──│ AI Foundry       │ │
│  │ (Cognitive)  │  │                  │  │ Project          │ │
│  └──────┬───────┘  └──────────────────┘  └──────────────────┘ │
│         │                                                      │
│  ┌──────┴───────┐                                              │
│  │ GPT-4o Model │                                              │
│  │ Deployment   │                                              │
│  └──────────────┘                                              │
└────────────────────────────────────────────────────────────────┘
```

## Resources Provisioned

| # | Resource | AVM Module | Purpose |
|---|----------|-----------|---------|
| 1 | Log Analytics Workspace | `avm/res/operational-insights/workspace:0.11.1` | Centralized logging |
| 2 | Application Insights | `avm/res/insights/component:0.6.0` | APM & telemetry |
| 3 | User Assigned Managed Identity | `avm/res/managed-identity/user-assigned-identity:0.5.0` | Workload identity (no secrets) |
| 4 | Azure Container Registry | `avm/res/container-registry/registry:0.8.0` | Container image store |
| 5 | Container Apps Environment | `avm/res/app/managed-environment:0.11.1` | App hosting platform |
| 6 | Container App (API) | `avm/res/app/container-app:0.14.0` | Backend FastAPI service |
| 7 | AI Services Account | `avm/res/cognitive-services/account:0.11.0` | OpenAI model hosting |
| 8 | AI Foundry Hub + Project | `avm/res/machine-learning-services/workspace:0.11.1` | Agent orchestration |
| 9 | GPT-4o Model Deployment | Raw Bicep (`Microsoft.CognitiveServices`) | LLM for migration agents |
| 10 | Role Assignments | Raw Bicep (`Microsoft.Authorization`) | Least-privilege RBAC |

## File Structure

```
infra/bicep/
├── main.bicep                    # Orchestrator — single entry point
├── modules/
│   ├── log-analytics.bicep       # Log Analytics workspace
│   ├── app-insights.bicep        # Application Insights
│   ├── managed-identity.bicep    # User Assigned Managed Identity
│   ├── container-registry.bicep  # Azure Container Registry
│   ├── container-apps-env.bicep  # Container Apps Environment
│   ├── container-app.bicep       # Container App (API)
│   ├── ai-services.bicep         # AI Services / Cognitive Services
│   ├── ai-foundry.bicep          # AI Foundry hub + project
│   ├── model-deployment.bicep    # GPT-4o model deployment
│   └── role-assignments.bicep    # RBAC role assignments
├── parameters/
│   ├── dev.bicepparam            # Development environment
│   ├── test.bicepparam           # Test environment
│   └── prod.bicepparam           # Production environment
└── README.md                     # This file
```

## Prerequisites

1. **Azure CLI** ≥ 2.61 with Bicep CLI ≥ 0.28
2. **Azure subscription** with the following resource providers registered:
   - `Microsoft.OperationalInsights`
   - `Microsoft.Insights`
   - `Microsoft.ManagedIdentity`
   - `Microsoft.ContainerRegistry`
   - `Microsoft.App`
   - `Microsoft.CognitiveServices`
   - `Microsoft.MachineLearningServices`
3. **Resource Group** created out-of-band (name available as `AZURE_RESOURCE_GROUP_NAME`)
4. Sufficient permissions to create resources and assign roles

## Deployment

### Deploy to Development

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam
```

### Deploy to Test

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/test.bicepparam
```

### Deploy to Production

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/prod.bicepparam
```

### Preview Changes (What-If)

```bash
az deployment group what-if \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam
```

### Validate Without Deploying

```bash
az deployment group validate \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/parameters/dev.bicepparam
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **UAMI only** | No system-assigned identities, no service principals with secrets. Aligns with §8 Identity spec. |
| **AVM modules** | Consistent, Microsoft-maintained, tested modules reduce maintenance burden. |
| **Modular design** | Each resource type in its own file for readability and independent evolution. |
| **Environment parameterization** | Single template set with `.bicepparam` files per environment. |
| **Raw Bicep for roles/models** | Role assignments and model deployments are simple enough that AVM adds no value. |
| **Placeholder container image** | Backend image will be replaced once CI/CD pushes to ACR. |
| **External ingress** | API is publicly accessible; restrict in prod via networking if needed. |

## Environment Differences

| Parameter | Dev | Test | Prod |
|-----------|-----|------|------|
| ACR SKU | Basic | Basic | Standard |
| Log retention (days) | 30 | 30 | 90 |
| Min replicas | 0 | 0 | 1 |
| Max replicas | 3 | 3 | 3 |
| GPT-4o capacity (TPM) | 10k | 10k | 30k |

## Role Assignments

The UAMI receives these least-privilege roles:

| Role | Scope | Purpose |
|------|-------|---------|
| **AcrPull** | Container Registry | Pull container images |
| **Cognitive Services OpenAI User** | AI Services Account | Invoke OpenAI models |

## Naming Convention

Resources follow the pattern: `{abbreviation}-{prefix}-{environment}`

| Resource | Pattern | Example (dev) |
|----------|---------|---------------|
| Log Analytics | `log-{prefix}-{env}` | `log-m2l-dev` |
| App Insights | `appi-{prefix}-{env}` | `appi-m2l-dev` |
| Managed Identity | `id-{prefix}-{env}` | `id-m2l-dev` |
| Container Registry | `acr{prefix}{env}` | `acrm2ldev` |
| Container Apps Env | `cae-{prefix}-{env}` | `cae-m2l-dev` |
| Container App | `ca-api-{prefix}-{env}` | `ca-api-m2l-dev` |
| AI Services | `ais-{prefix}-{env}` | `ais-m2l-dev` |
| AI Foundry Hub | `hub-{prefix}-{env}` | `hub-m2l-dev` |
| AI Foundry Project | `proj-{prefix}-{env}` | `proj-m2l-dev` |
