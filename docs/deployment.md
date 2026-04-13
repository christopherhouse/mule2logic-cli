# Deployment Guide

This document covers Azure infrastructure deployment and CI/CD setup for the MuleSoft → Logic Apps migration platform.

## Prerequisites

- Azure subscription with Contributor + User Access Administrator roles
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) v2.60+
- [Bicep CLI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/install) v0.26+
- GitHub repository with Actions enabled

---

## Infrastructure Overview

All infrastructure is defined in `infra/bicep/` using [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/).

### Resources Provisioned

| Resource | AVM Module | Purpose |
|----------|-----------|---------|
| User Assigned Managed Identity | `avm.res.managed-identity.user-assigned-identity` | Workload identity (no secrets) |
| Log Analytics Workspace | `avm.res.operational-insights.workspace` | Centralized logging |
| Application Insights | `avm.res.insights.component` | APM and telemetry |
| Azure Container Registry | `avm.res.container-registry.registry` | Container image storage |
| Container Apps Environment | `avm.res.app.managed-environment` | Hosting environment |
| Container App (API) | Script (`infra/scripts/deploy-container-app.sh`) | Backend API service |
| AI Foundry (hub + project) | `avm.ptn.ai-ml.ai-foundry` | LLM model access for agents |

### RBAC Role Assignments (UAMI)

| Role | Scope | Purpose |
|------|-------|---------|
| AcrPull | Container Registry | Pull container images |
| Cognitive Services OpenAI User | AI Foundry account | Call LLM models |

### Environment Parameterization

Three parameter files support dev/test/prod:

| File | ACR SKU | Notes |
|------|---------|-------|
| `main.dev.bicepparam` | Basic | Development |
| `main.test.bicepparam` | Basic | Testing |
| `main.prod.bicepparam` | Standard | Production |

---

## Manual Deployment

### 1. Create Resource Group

```bash
az group create \
  --name rg-m2la-dev \
  --location eastus2
```

### 2. Deploy Infrastructure

```bash
az deployment group create \
  --resource-group rg-m2la-dev \
  --template-file infra/bicep/main.bicep \
  --parameters infra/bicep/main.dev.bicepparam \
  --name m2la-dev-manual
```

### 3. Build and Push Container Image

```bash
ACR_NAME=$(az deployment group show \
  --resource-group rg-m2la-dev \
  --name m2la-dev-manual \
  --query properties.outputs.acrName.value -o tsv)

az acr build \
  --registry $ACR_NAME \
  --image m2la-api:latest \
  --file apps/api/Dockerfile \
  apps/api/
```

### 4. Deploy Container App

Use the deployment script after building and pushing the image:

```bash
DEPLOY_NAME="m2la-dev-manual"
RG="rg-m2la-dev"

export RESOURCE_GROUP="$RG"
export ENVIRONMENT_NAME="dev"
export ACR_LOGIN_SERVER=$(az deployment group show \
  --resource-group $RG --name $DEPLOY_NAME \
  --query properties.outputs.acrLoginServer.value -o tsv)
export IMAGE_TAG="latest"
export UAMI_RESOURCE_ID=$(az deployment group show \
  --resource-group $RG --name $DEPLOY_NAME \
  --query properties.outputs.uamiResourceId.value -o tsv)
export UAMI_CLIENT_ID=$(az deployment group show \
  --resource-group $RG --name $DEPLOY_NAME \
  --query properties.outputs.uamiClientId.value -o tsv)
export APP_INSIGHTS_CONN_STRING=$(az deployment group show \
  --resource-group $RG --name $DEPLOY_NAME \
  --query properties.outputs.appInsightsConnectionString.value -o tsv)

./infra/scripts/deploy-container-app.sh
```

---

## CI/CD Setup (GitHub Actions)

### Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| PR Validation | `.github/workflows/pr-validation.yml` | Pull request to main | Lint, test, build, Bicep validate, Docker build |
| Deploy | `.github/workflows/deploy.yml` | Push to main / manual dispatch | Deploy infra + build image + update app |
| Bicep What-If | `.github/workflows/bicep-what-if.yml` | PR with `infra/bicep/**` changes | Show infra diff in PR comment |

### OIDC Federated Identity Setup

The deploy workflows use [OIDC federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation) — no client secrets stored in GitHub.

#### 1. Create Azure AD App Registration

```bash
az ad app create --display-name "m2la-github-actions"
APP_ID=$(az ad app list --display-name "m2la-github-actions" --query "[0].appId" -o tsv)
az ad sp create --id $APP_ID
```

#### 2. Add Federated Credentials

Create federated credentials for each environment and for pull requests:

```bash
# For the 'dev' environment
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-dev",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:YOUR_ORG/mule2logic-cli:environment:dev",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For the 'test' environment
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-test",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:YOUR_ORG/mule2logic-cli:environment:test",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For the 'prod' environment
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-prod",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:YOUR_ORG/mule2logic-cli:environment:prod",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For pull requests (Bicep what-if)
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-pr",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:YOUR_ORG/mule2logic-cli:pull_request",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

#### 3. Grant Azure RBAC to the Service Principal

```bash
SP_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv)

# Contributor on the resource group (for deployments)
az role assignment create \
  --assignee-object-id $SP_ID \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope /subscriptions/YOUR_SUB_ID/resourceGroups/rg-m2la-dev

# User Access Administrator (for RBAC role assignments in Bicep)
az role assignment create \
  --assignee-object-id $SP_ID \
  --assignee-principal-type ServicePrincipal \
  --role "User Access Administrator" \
  --scope /subscriptions/YOUR_SUB_ID/resourceGroups/rg-m2la-dev
```

### GitHub Environments and Variables

Create **three GitHub environments**: `dev`, `test`, `prod`.

For each environment, configure these **environment variables** (not secrets):

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | App registration client ID | `12345678-...` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `87654321-...` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `abcdef01-...` |
| `AZURE_RESOURCE_GROUP_NAME` | Target resource group name | `rg-m2la-dev` |

> **No secrets are required.** OIDC federated identity provides Azure auth using GitHub's built-in token.

For production, consider adding **environment protection rules** (required reviewers, deployment branches).

---

## Troubleshooting

### Bicep deployment fails with "RoleAssignmentExists"

This is expected on redeployments. Role assignments are idempotent but may warn. The deployment will still succeed.

### Container App shows "ImagePullBackOff"

1. Verify the UAMI has `AcrPull` on the ACR: `az role assignment list --scope <acr-resource-id>`
2. Verify the image exists: `az acr repository show-tags --name <acr-name> --repository m2la-api`

### OIDC login fails with "AADSTS700024"

The federated credential subject must exactly match the GitHub Actions context. Verify:
- Repository name is correct (case-sensitive)
- Environment name matches exactly
- For PRs, use `pull_request` subject

### AI Foundry deployment fails

- Verify the region supports the requested model (GPT-4o). Not all regions have all models.
- Check quota: `az cognitiveservices usage list --location <location>`
