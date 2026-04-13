# Infrastructure as Code (Bicep)

Azure infrastructure definitions using [Bicep](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/) with [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/).

## Module Structure

```
infra/bicep/
├── main.bicep                  # Orchestrator — composes all modules
├── main.dev.bicepparam          # Dev environment parameters
├── main.test.bicepparam         # Test environment parameters
├── main.prod.bicepparam         # Prod environment parameters
└── modules/
    ├── identity.bicep           # User Assigned Managed Identity
    ├── monitoring.bicep         # Log Analytics + Application Insights
    ├── registry.bicep           # Azure Container Registry
    ├── container-apps.bicep     # Container Apps Environment + API App
    └── ai-foundry.bicep         # AI Foundry account + project + model deployments (raw Bicep)
```

## Resources Provisioned

| Resource | Module | Purpose |
|----------|--------|----------|
| UAMI | AVM `avm.res.managed-identity.user-assigned-identity` | Workload identity (no secrets) |
| Log Analytics | AVM `avm.res.operational-insights.workspace` | Centralized logging |
| Application Insights | AVM `avm.res.insights.component` | APM and telemetry |
| ACR | AVM `avm.res.container-registry.registry` | Container image storage |
| Container Apps Env | AVM `avm.res.app.managed-environment` | Hosting environment |
| Container App | AVM `avm.res.app.container-app` | Backend API service |
| AI Foundry | Raw Bicep (`Microsoft.CognitiveServices`) | LLM model access for agents |

> **Note:** AI Foundry uses raw Bicep instead of AVM. The AVM pattern module
> (`avm/ptn/ai-ml/ai-foundry`) deploys a full landing zone (VMs, VNets, etc.)
> which is too heavy for this project. The AVM resource module
> (`avm/res/cognitive-services/account`) does not manage child project resources,
> and the hybrid AVM + raw child-resource approach caused deployment failures.
> Raw Bicep with the GA API (`2025-06-01`) is the most reliable approach.

## Deployment

### Prerequisites

- Azure CLI v2.60+
- Bicep CLI v0.26+
- An existing resource group

### Deploy (dev)

```bash
az deployment group create \
  --resource-group rg-m2la-dev \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/main.dev.bicepparam
```

### Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `environmentName` | `dev` \| `test` \| `prod` | Controls naming and SKU defaults |
| `location` | string | Azure region (defaults to RG location) |
| `acrSkuName` | `Basic` \| `Standard` \| `Premium` | ACR tier |
| `containerImage` | string | Full image ref (empty = placeholder) |
| `aiModelDeployments` | array | OpenAI model deployments |

See [docs/deployment.md](../../docs/deployment.md) for full deployment guide including CI/CD setup.
