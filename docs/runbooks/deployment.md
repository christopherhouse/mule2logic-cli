# Deployment Guide

This document covers how to deploy the MuleSoft → Logic Apps Standard Migration Platform to Azure, including infrastructure provisioning, CI/CD pipeline setup, and OIDC configuration.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [OIDC Setup (GitHub ↔ Azure)](#oidc-setup-github--azure)
- [GitHub Repository Configuration](#github-repository-configuration)
- [Infrastructure Deployment](#infrastructure-deployment)
- [CI/CD Pipelines](#cicd-pipelines)
- [Manual Deployment](#manual-deployment)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
GitHub Actions (CI/CD)
    │
    ├── PR Validation:  lint → test → build → Bicep validate
    │
    └── Deploy (main):  Bicep deploy → ACR push → Container Apps update
                              │
                              ▼
                    Azure Resource Group
                    ├── Container Registry (ACR)
                    ├── Container Apps Environment
                    │   └── Container App (API)
                    ├── User Assigned Managed Identity
                    ├── Log Analytics + App Insights
                    ├── AI Services + Foundry Hub + Project
                    └── GPT-4o Model Deployment
```

Authentication uses **OIDC federated identity** — no secrets stored in GitHub.

---

## Prerequisites

1. **Azure subscription** with Owner or Contributor + User Access Administrator permissions
2. **Azure CLI** ≥ 2.61 with Bicep CLI ≥ 0.28
3. **GitHub repository** with Actions enabled
4. **Resource providers** registered on the subscription:
   - `Microsoft.OperationalInsights`
   - `Microsoft.Insights`
   - `Microsoft.ManagedIdentity`
   - `Microsoft.ContainerRegistry`
   - `Microsoft.App`
   - `Microsoft.CognitiveServices`
   - `Microsoft.MachineLearningServices`

Register providers if needed:

```bash
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.ManagedIdentity
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.MachineLearningServices
```

---

## OIDC Setup (GitHub ↔ Azure)

GitHub Actions authenticates to Azure using **OpenID Connect (OIDC)** federated credentials — no client secrets are stored in GitHub.

### 1. Create a Microsoft Entra ID App Registration

```bash
# Create the app registration
az ad app create --display-name "mule2logic-github-actions"

# Note the appId from the output
APP_ID=$(az ad app list --display-name "mule2logic-github-actions" --query '[0].appId' -o tsv)

# Create a service principal
az ad sp create --id "$APP_ID"
```

### 2. Add Federated Credentials

Create federated credentials for the `main` branch and for each environment:

```bash
# For pushes to main branch
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For the dev environment
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-env-dev",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:environment:dev",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For the test environment
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-env-test",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:environment:test",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For the prod environment
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-env-prod",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:environment:prod",
  "audiences": ["api://AzureADTokenExchange"]
}'

# For pull requests (needed for Bicep validation on PRs)
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-pull-requests",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:pull_request",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

> Replace `<OWNER>/<REPO>` with your GitHub org and repo name (e.g., `christopherhouse/mule2logic-cli`).

### 3. Assign Azure Roles

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SP_OBJECT_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query '[0].id' -o tsv)

# Contributor on the subscription (or scoped to RG)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"

# User Access Administrator (for role assignments in Bicep)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "User Access Administrator" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

### 4. Create the Resource Group

```bash
az group create \
  --name "rg-mule2logic-dev" \
  --location "eastus2"
```

---

## GitHub Repository Configuration

### Required Variables (per environment)

Set these as **repository variables** or **environment variables** in GitHub Settings → Environments:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | App registration (client) ID | `12345678-abcd-...` |
| `AZURE_TENANT_ID` | Microsoft Entra ID tenant ID | `abcdef01-2345-...` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `fedcba98-7654-...` |
| `AZURE_RESOURCE_GROUP_NAME` | Target resource group name | `rg-mule2logic-dev` |

### GitHub Environments

Create these environments in **Settings → Environments**:

| Environment | Protection Rules |
|-------------|-----------------|
| `dev` | None (auto-deploy on push to main) |
| `test` | Require reviewers |
| `prod` | Require reviewers + wait timer |

Each environment should have its own set of the variables listed above (or share tenant/subscription if appropriate).

### No Secrets Needed

With OIDC, there are **no stored secrets** required. All authentication is handled via federated identity tokens.

---

## Infrastructure Deployment

### Automated (via CI/CD)

Push to `main` → the Deploy workflow runs automatically, deploying to `dev` by default.

For other environments, use the **workflow_dispatch** trigger:

1. Go to **Actions** → **Deploy** workflow
2. Click **Run workflow**
3. Select the target environment
4. Click **Run workflow**

### Manual (via Azure CLI)

```bash
# Set your target environment
ENV=dev

# Deploy
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters "infra/bicep/parameters/${ENV}.bicepparam"
```

### Preview Changes

```bash
az deployment group what-if \
  --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
  --template-file infra/bicep/main.bicep \
  --parameters "infra/bicep/parameters/${ENV}.bicepparam"
```

---

## CI/CD Pipelines

### PR Validation (`pr-validation.yml`)

Runs on every pull request to `main`:

| Job | Steps |
|-----|-------|
| **Python** | Install deps (uv) → ruff check → ruff format → pytest → uv build |
| **TypeScript** | Install deps (npm) → tsc → ESLint → Prettier → vitest → tsc build |
| **Bicep** | Bicep lint → (optional) Azure validate → (optional) What-If |

The Bicep Azure validation steps are **optional** — they only run if OIDC is configured (i.e., `AZURE_CLIENT_ID` is set as a repository variable). This allows the workflow to pass on forks or before Azure setup is complete.

### Deploy (`deploy.yml`)

Runs on push to `main` or manual dispatch:

| Job | Steps |
|-----|-------|
| **infra** | Azure login → Validate Bicep → Deploy Bicep → Output ACR/app names |
| **build-api** | Azure login → ACR login → Build Docker image → Push to ACR |
| **deploy-app** | Azure login → Update Container App → Verify health |
| **build-cli** | npm ci → tsc build → Upload artifact |

### Extending Pipelines

As features land in later PRs, add steps to the existing workflows:

- New Python services → add to the `python` job in `pr-validation.yml`
- New container images → add build jobs in `deploy.yml`
- Integration tests → add a new job after `deploy-app`

---

## Troubleshooting

### OIDC Login Fails

```
Error: AADSTS70021: No matching federated identity record found
```

Verify the federated credential subjects match exactly:
- Branch: `repo:<owner>/<repo>:ref:refs/heads/main`
- Environment: `repo:<owner>/<repo>:environment:<env-name>`
- PR: `repo:<owner>/<repo>:pull_request`

### Bicep Validation Fails on PR

If `AZURE_CLIENT_ID` is not set as a repository variable, the Bicep Azure validation steps are skipped. This is expected. Only the local `bicep build` lint step runs.

### Container App Not Starting

1. Check Container App logs:
   ```bash
   az containerapp logs show \
     --name "ca-api-m2l-dev" \
     --resource-group "$AZURE_RESOURCE_GROUP_NAME" \
     --type system
   ```

2. Verify the image exists in ACR:
   ```bash
   az acr repository show-tags \
     --name "acrm2ldev" \
     --repository m2la-api
   ```

3. Verify UAMI has AcrPull role on the registry.

### Resource Provider Not Registered

```
Error: MissingSubscriptionRegistration
```

Register the required provider:
```bash
az provider register --namespace Microsoft.<ProviderName>
```
