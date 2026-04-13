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

@description('Full container image reference. Leave empty to use placeholder.')
param containerImage string = ''

@description('ACR SKU. Use Basic for dev, Standard/Premium for prod.')
@allowed(['Basic', 'Standard', 'Premium'])
param acrSkuName string = 'Basic'

@description('OpenAI model deployments for AI Foundry.')
param aiModelDeployments array = [
  {
    name: 'gpt-4o'
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
    sku: {
      name: 'GlobalStandard'
      capacity: 50
    }
  }
]

// ---------------------------------------------------------------------------
// Computed values
// ---------------------------------------------------------------------------
var defaultTags = union(tags, {
  project: 'mule2logic'
  environment: environmentName
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
  }
}

// ---------------------------------------------------------------------------
// Module: Container Apps (Environment + API App)
// ---------------------------------------------------------------------------
module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
    uamiResourceId: identity.outputs.resourceId
    uamiClientId: identity.outputs.clientId
    acrLoginServer: registry.outputs.loginServer
    containerImage: containerImage
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// ---------------------------------------------------------------------------
// Module: AI Foundry (hub + project + model deployments)
// ---------------------------------------------------------------------------
module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  params: {
    environmentName: environmentName
    location: location
    tags: defaultTags
    uamiPrincipalId: identity.outputs.principalId
    aiModelDeployments: aiModelDeployments
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
@description('API Container App FQDN.')
output apiAppFqdn string = containerApps.outputs.fqdn

@description('API Container App name.')
output apiAppName string = containerApps.outputs.appName

@description('Container Apps Environment name.')
output containerAppsEnvironmentName string = containerApps.outputs.environmentName

// AI Foundry
@description('AI Foundry project name.')
output aiProjectName string = aiFoundry.outputs.projectName

@description('AI Services account name.')
output aiServicesName string = aiFoundry.outputs.aiServicesName

@description('AI Services endpoint.')
output aiServicesEndpoint string = aiFoundry.outputs.aiServicesEndpoint
