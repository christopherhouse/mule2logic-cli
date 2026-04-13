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
    └── ai-foundry.bicep         # AI Foundry hub + project + model deployments
```

## Resources Provisioned

| Resource | AVM Module | Purpose |
|----------|-----------|----------|
| UAMI | `avm.res.managed-identity.user-assigned-identity` | Workload identity (no secrets) |
| Log Analytics | `avm.res.operational-insights.workspace` | Centralized logging |
| Application Insights | `avm.res.insights.component` | APM and telemetry |
| ACR | `avm.res.container-registry.registry` | Container image storage |
| Container Apps Env | `avm.res.app.managed-environment` | Hosting environment |
| Container App | `avm.res.app.container-app` | Backend API service |
| AI Foundry | `avm.ptn.ai-ml.ai-foundry` | LLM model access for agents |

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
