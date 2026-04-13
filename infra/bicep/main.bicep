// ---------------------------------------------------------------------------
// main.bicep — MuleSoft → Logic Apps Migration Platform
//
// Orchestrates all Azure infrastructure for the platform.
// Deploys to an existing Resource Group (created out-of-band).
//
// Usage:
//   az deployment group create \
//     --resource-group $AZURE_RESOURCE_GROUP_NAME \
//     --template-file infra/bicep/main.bicep \
//     --parameters infra/bicep/parameters/dev.bicepparam
// ---------------------------------------------------------------------------
targetScope = 'resourceGroup'

// ===========================================================================
// Parameters
// ===========================================================================

@description('Environment name used in resource naming (dev, test, prod).')
@allowed([
  'dev'
  'test'
  'prod'
])
param environmentName string

@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Base prefix for resource naming (e.g., "m2l" for mule2logic).')
@maxLength(10)
param resourcePrefix string = 'm2l'

@description('Tags to apply to all resources.')
param tags object = {}

@description('SKU for the Container Registry.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param containerRegistrySku string = 'Basic'

@description('Log Analytics data retention in days.')
@minValue(30)
@maxValue(730)
param logRetentionDays int = 30

@description('Container image for the backend API. Use placeholder initially.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Target port for the backend API container.')
param containerPort int = 8000

@description('Minimum replicas for the Container App.')
@minValue(0)
param minReplicas int = 0

@description('Maximum replicas for the Container App.')
@minValue(1)
param maxReplicas int = 3

@description('GPT-4o model version to deploy.')
param gptModelVersion string = '2024-11-20'

@description('Capacity (TPM in thousands) for the GPT-4o deployment.')
param gptModelCapacity int = 10

// ===========================================================================
// Variables — Naming Convention
// Follows: {prefix}-{resource}-{environment}
// ACR names must be alphanumeric only, no hyphens.
// ===========================================================================
var nameSuffix = '${resourcePrefix}-${environmentName}'
var logAnalyticsName = 'log-${nameSuffix}'
var appInsightsName = 'appi-${nameSuffix}'
var identityName = 'id-${nameSuffix}'
// ACR names: alphanumeric, 5–50 chars, globally unique
var containerRegistryName = replace('acr${nameSuffix}', '-', '')
var containerAppsEnvName = 'cae-${nameSuffix}'
var containerAppName = 'ca-api-${nameSuffix}'
var aiServicesName = 'ais-${nameSuffix}'
var aiServicesSubDomain = 'ais-${nameSuffix}'
var aiFoundryHubName = 'hub-${nameSuffix}'
var aiFoundryProjectName = 'proj-${nameSuffix}'

// Merge environment tag into user-provided tags
var allTags = union(tags, {
  environment: environmentName
  project: 'mule2logic'
  managedBy: 'bicep'
})

// ===========================================================================
// 1. Log Analytics Workspace
// ===========================================================================
module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'module-log-analytics'
  params: {
    location: location
    workspaceName: logAnalyticsName
    tags: allTags
    retentionInDays: logRetentionDays
  }
}

// ===========================================================================
// 2. Application Insights (connected to Log Analytics)
// ===========================================================================
module appInsights 'modules/app-insights.bicep' = {
  name: 'module-app-insights'
  params: {
    location: location
    appInsightsName: appInsightsName
    tags: allTags
    workspaceResourceId: logAnalytics.outputs.workspaceId
  }
}

// ===========================================================================
// 3. User Assigned Managed Identity
// ===========================================================================
module managedIdentity 'modules/managed-identity.bicep' = {
  name: 'module-managed-identity'
  params: {
    location: location
    identityName: identityName
    tags: allTags
  }
}

// ===========================================================================
// 4. Azure Container Registry
// ===========================================================================
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'module-container-registry'
  params: {
    location: location
    registryName: containerRegistryName
    tags: allTags
    skuName: containerRegistrySku
  }
}

// ===========================================================================
// 5. Container Apps Environment
// The Log Analytics shared key is retrieved at deployment time via listKeys().
// It is consumed by the Container Apps platform — NOT stored in any app config.
// ===========================================================================
// Reference the Log Analytics workspace to retrieve its shared key
resource logAnalyticsRef 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'module-container-apps-env'
  params: {
    location: location
    environmentName: containerAppsEnvName
    tags: allTags
    logAnalyticsCustomerId: logAnalytics.outputs.workspaceCustomerId
    logAnalyticsSharedKey: logAnalyticsRef.listKeys().primarySharedKey
  }
}

// ===========================================================================
// 6. Container App (backend API)
// ===========================================================================
module containerApp 'modules/container-app.bicep' = {
  name: 'module-container-app'
  params: {
    location: location
    containerAppName: containerAppName
    tags: allTags
    environmentResourceId: containerAppsEnv.outputs.environmentId
    identityResourceId: managedIdentity.outputs.identityId
    containerImage: containerImage
    targetPort: containerPort
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    acrLoginServer: containerRegistry.outputs.loginServer
    appInsightsConnectionString: appInsights.outputs.connectionString
  }
}

// ===========================================================================
// 7. AI Services (Cognitive Services) Account
// ===========================================================================
module aiServices 'modules/ai-services.bicep' = {
  name: 'module-ai-services'
  params: {
    location: location
    aiServicesName: aiServicesName
    tags: allTags
    customSubDomainName: aiServicesSubDomain
  }
}

// ===========================================================================
// 8. Azure AI Foundry Hub + Project
// ===========================================================================
module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'module-ai-foundry'
  params: {
    location: location
    hubName: aiFoundryHubName
    projectName: aiFoundryProjectName
    tags: allTags
    aiServicesId: aiServices.outputs.aiServicesId
    aiServicesName: aiServices.outputs.aiServicesName
    appInsightsId: appInsights.outputs.appInsightsId
  }
}

// ===========================================================================
// 9. Model Deployment (GPT-4o)
// ===========================================================================
module modelDeployment 'modules/model-deployment.bicep' = {
  name: 'module-model-deployment'
  params: {
    aiServicesName: aiServices.outputs.aiServicesName
    deploymentName: 'gpt-4o'
    modelName: 'gpt-4o'
    modelVersion: gptModelVersion
    skuCapacity: gptModelCapacity
  }
}

// ===========================================================================
// 10. Role Assignments (least-privilege for UAMI)
// ===========================================================================
module roleAssignments 'modules/role-assignments.bicep' = {
  name: 'module-role-assignments'
  params: {
    principalId: managedIdentity.outputs.principalId
    containerRegistryName: containerRegistry.outputs.registryName
    aiServicesAccountName: aiServices.outputs.aiServicesName
  }
}

// ===========================================================================
// Outputs
// ===========================================================================
@description('Name of the Container App.')
output containerAppName string = containerApp.outputs.containerAppName

@description('FQDN of the Container App.')
output containerAppFqdn string = containerApp.outputs.fqdn

@description('Container Registry login server.')
output acrLoginServer string = containerRegistry.outputs.loginServer

@description('Client ID of the User Assigned Managed Identity.')
output identityClientId string = managedIdentity.outputs.clientId

@description('Principal ID of the User Assigned Managed Identity.')
output identityPrincipalId string = managedIdentity.outputs.principalId

@description('Application Insights instrumentation key.')
output appInsightsInstrumentationKey string = appInsights.outputs.instrumentationKey

@description('Application Insights connection string.')
output appInsightsConnectionString string = appInsights.outputs.connectionString

@description('AI Services endpoint.')
output aiServicesEndpoint string = aiServices.outputs.endpoint

@description('AI Foundry hub name.')
output aiFoundryHubName string = aiFoundry.outputs.hubName

@description('AI Foundry project name.')
output aiFoundryProjectName string = aiFoundry.outputs.projectName

@description('GPT-4o model deployment name.')
output modelDeploymentName string = modelDeployment.outputs.deploymentName
