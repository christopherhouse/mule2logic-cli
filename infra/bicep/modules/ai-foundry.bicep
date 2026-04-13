// ---------------------------------------------------------------------------
// Module: ai-foundry.bicep — AI Services account + project + model deployments
// Raw Bicep (no AVM) — follows the official Microsoft Foundry quickstart pattern.
// See: https://learn.microsoft.com/azure/foundry/how-to/create-resource-template
//
// Why raw Bicep instead of AVM?
// - The AVM resource module (cognitive-services/account) does not manage child
//   project resources. The hybrid AVM-account + raw-project approach caused
//   InternalServerError during deployment because the project child resource
//   used flat naming without a proper parent reference, and the preview API
//   (2025-04-01-preview) was unstable.
// - The AVM pattern module (ai-ml/ai-foundry) provisions an entire landing zone
//   (VMs, VNets, Bastion, Cosmos DB, Key Vault, etc.) — far too heavy for our
//   needs.
// - Raw Bicep with the GA API (2025-06-01) and proper parent syntax is the
//   simplest, most reliable approach.
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

@description('Principal ID of the UAMI to grant Cognitive Services OpenAI User role.')
param uamiPrincipalId string

@description('Resource ID of the UAMI to attach to the AI Services account.')
param uamiResourceId string

@description('Resource ID of the Log Analytics workspace for diagnostic settings.')
param logAnalyticsWorkspaceResourceId string

@description('OpenAI model deployments to provision.')
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
// Naming
// ---------------------------------------------------------------------------
var aiServicesName = 'ais-m2la-${environmentName}'
var projectName = 'proj-m2la-${environmentName}'

// ---------------------------------------------------------------------------
// AI Services Account (kind: AIServices)
// ---------------------------------------------------------------------------
resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uamiResourceId}': {}
    }
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: 'ais-m2la-${environmentName}-${uniqueString(resourceGroup().id)}'
    disableLocalAuth: true // AAD-only, no key-based auth
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// AI Foundry Project (child of AI Services account, using parent syntax)
// ---------------------------------------------------------------------------
resource aiFoundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: aiServicesAccount
  name: projectName
  location: location
  tags: tags
  properties: {
    displayName: 'MuleSoft to Logic Apps - ${environmentName}'
    description: 'AI Foundry project for the MuleSoft to Logic Apps migration platform.'
  }
}

// ---------------------------------------------------------------------------
// Model Deployments
// ---------------------------------------------------------------------------
@batchSize(1) // Deploy models sequentially to avoid RP throttling
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [
  for deployment in aiModelDeployments: {
    parent: aiServicesAccount
    name: deployment.name
    sku: deployment.sku
    properties: {
      model: deployment.model
    }
  }
]

// ---------------------------------------------------------------------------
// RBAC: Cognitive Services OpenAI User for UAMI
// ---------------------------------------------------------------------------
resource openAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiServicesAccount
  name: guid(aiServicesAccount.id, uamiPrincipalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  properties: {
    principalId: uamiPrincipalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    )
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Diagnostic Settings — send all logs and metrics to Log Analytics
// ---------------------------------------------------------------------------
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: aiServicesAccount
  name: 'allLogsAndMetrics'
  properties: {
    workspaceId: logAnalyticsWorkspaceResourceId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Name of the AI Foundry project.')
output projectName string = aiFoundryProject.name

@description('Name of the AI Services account.')
output aiServicesName string = aiServicesAccount.name

@description('AI Services account endpoint.')
output aiServicesEndpoint string = aiServicesAccount.properties.endpoint
