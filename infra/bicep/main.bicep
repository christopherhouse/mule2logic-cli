// ---------------------------------------------------------------------------
// main.bicep — Orchestrator for MuleSoft → Logic Apps platform infrastructure
// ---------------------------------------------------------------------------
// Deploys all platform resources using Azure Verified Modules (AVM).
// Resource Group is assumed to exist (created out-of-band).
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

@description('Environment name. Controls naming and configuration.')
@allowed(['dev', 'test', 'prod'])
param environmentName string

@description('Azure region for all resources. Defaults to resource group location.')
param location string = resourceGroup().location

@description('Resource tags applied to all resources.')
param tags object = {}

@description('ACR SKU. Use Basic for dev, Standard/Premium for prod.')
@allowed(['Basic', 'Standard', 'Premium'])
param acrSkuName string = 'Basic'

@description('SKU name for the GPT-4o model deployment.')
param aiModelDeploymentSkuName string = 'GlobalStandard'

@description('Capacity (K TPM) for the GPT-4o model deployment.')
param aiModelDeploymentCapacity int = 30

@description('Container image for the API app. Defaults to a placeholder; overridden by deploy script.')
param containerImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// ---------------------------------------------------------------------------
// Computed values
// ---------------------------------------------------------------------------
var defaultTags = union(tags, {
  project: 'mule2logic'
  environment: environmentName
  SecurityControl: 'Ignore'
})

var uamiName = 'id-m2la-${environmentName}'

// ---------------------------------------------------------------------------
// Module: Identity (UAMI)
// ---------------------------------------------------------------------------
module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    name: uamiName
    location: location
    tags: defaultTags
  }
}

// ---------------------------------------------------------------------------
// Module: Monitoring (Log Analytics + App Insights)
// ---------------------------------------------------------------------------
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
  }
}

// ---------------------------------------------------------------------------
// Module: Container Registry
// ---------------------------------------------------------------------------
module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
    uamiPrincipalId: identity.outputs.principalId
    skuName: acrSkuName
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
  }
}

// ---------------------------------------------------------------------------
// Module: Container Apps (Environment + API Container App)
// ---------------------------------------------------------------------------
module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    uamiResourceId: identity.outputs.resourceId
    uamiClientId: identity.outputs.clientId
    acrLoginServer: registry.outputs.loginServer
    containerImage: containerImage
  }
}

// ---------------------------------------------------------------------------
// Module: AI Foundry (AI Services account + GPT-4o deployment)
// ---------------------------------------------------------------------------
module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  params: {
    name: 'ais-m2la-${environmentName}'
    location: location
    tags: defaultTags
    modelDeploymentSkuName: aiModelDeploymentSkuName
    modelDeploymentCapacity: aiModelDeploymentCapacity
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

// Identity
@description('UAMI principal (object) ID.')
output uamiPrincipalId string = identity.outputs.principalId

@description('UAMI client ID.')
output uamiClientId string = identity.outputs.clientId

@description('UAMI resource ID.')
output uamiResourceId string = identity.outputs.resourceId

// Monitoring
@description('Application Insights connection string.')
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

@description('Log Analytics workspace resource ID.')
output logAnalyticsWorkspaceResourceId string = monitoring.outputs.logAnalyticsWorkspaceResourceId

// Registry
@description('ACR login server.')
output acrLoginServer string = registry.outputs.loginServer

@description('ACR name.')
output acrName string = registry.outputs.name

// Container Apps
@description('Container Apps Environment name.')
output containerAppsEnvironmentName string = containerApps.outputs.environmentName

@description('Container App name.')
output containerAppName string = containerApps.outputs.appName

@description('Container App FQDN.')
output containerAppFqdn string = containerApps.outputs.appFqdn

// AI Foundry
@description('AI Services account name.')
output aiServicesName string = aiFoundry.outputs.aiServicesName

@description('AI Services endpoint.')
output aiServicesEndpoint string = aiFoundry.outputs.endpoint

@description('AI Services system-assigned identity principal ID.')
output aiServicesPrincipalId string = aiFoundry.outputs.principalId
