// =============================================================================
// AI Foundry — AI Services Account + GPT-4o Model Deployment
// =============================================================================

@description('Name of the AI Services account.')
param name string

@description('Azure region for the resource.')
param location string

@description('Tags to apply to the resource.')
param tags object = {}

@description('SKU name for the GPT-4o model deployment.')
param modelDeploymentSkuName string = 'GlobalStandard'

@description('Capacity (K TPM) for the GPT-4o model deployment.')
param modelDeploymentCapacity int = 30

@description('Principal ID of the User Assigned Managed Identity to grant Cognitive Services OpenAI User role.')
param uamiPrincipalId string = ''

@description('Resource ID of the Log Analytics workspace for diagnostic settings.')
param logAnalyticsWorkspaceId string = ''

// ---------------------------------------------------------------------------
// AI Services Account (Foundry resource)
// ---------------------------------------------------------------------------

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// Model Deployment — GPT-4o
// ---------------------------------------------------------------------------

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServices
  name: 'gpt-4o'
  sku: {
    name: modelDeploymentSkuName
    capacity: modelDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// ---------------------------------------------------------------------------
// Diagnostic Settings
// ---------------------------------------------------------------------------

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: 'allLogsAndMetrics'
  scope: aiServices
  properties: {
    workspaceId: logAnalyticsWorkspaceId
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
// RBAC — Grant UAMI the Cognitive Services OpenAI User role
// ---------------------------------------------------------------------------

resource uamiOpenAiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(uamiPrincipalId)) {
  name: guid(aiServices.id, uamiPrincipalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: aiServices
  properties: {
    principalId: uamiPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('Resource ID of the AI Services account.')
output accountId string = aiServices.id

@description('Endpoint URL of the AI Services account.')
output endpoint string = aiServices.properties.endpoint

@description('Name of the AI Services account.')
output aiServicesName string = aiServices.name

@description('Principal ID of the system-assigned managed identity.')
output principalId string = aiServices.identity.principalId
