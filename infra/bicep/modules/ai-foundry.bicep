// ---------------------------------------------------------------------------
// Module: Azure AI Foundry Hub + Project
// Uses AVM: avm/res/machine-learning-services/workspace (kind = 'Hub' / 'Project')
//
// An AI Foundry "hub" is an Azure ML workspace with kind=Hub.
// An AI Foundry "project" is an Azure ML workspace with kind=Project linked
// to the hub.
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the AI Foundry hub.')
param hubName string

@description('Name of the AI Foundry project.')
param projectName string

@description('Tags to apply to the resources.')
param tags object = {}

@description('Resource ID of the AI Services account to connect to the hub.')
param aiServicesId string

@description('Name of the AI Services account (used in the connection).')
param aiServicesName string

@description('Resource ID of the Application Insights for the hub.')
param appInsightsId string

// ---------------------------------------------------------------------------
// Storage Account for AI Foundry Hub (required dependency)
// Raw Bicep — simple storage account, no AVM needed for a private dependency.
// ---------------------------------------------------------------------------
resource hubStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  // Storage account names: 3–24 chars, alphanumeric only, globally unique.
  // The take() + replace() ensures we meet the min-length constraint.
  name: take('st${replace(replace(hubName, '-', ''), '_', '')}sa', 24)
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// ---------------------------------------------------------------------------
// Key Vault for AI Foundry Hub (required dependency)
// Raw Bicep — simple Key Vault, required by the ML workspace.
// ---------------------------------------------------------------------------
resource hubKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take('kv-${hubName}', 24)
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// ---------------------------------------------------------------------------
// AVM: AI Foundry Hub (Azure ML workspace kind=Hub)
// ---------------------------------------------------------------------------
module hub 'br/public:avm/res/machine-learning-services/workspace:0.11.1' = {
  name: 'deploy-ai-foundry-hub'
  params: {
    name: hubName
    location: location
    tags: tags
    kind: 'Hub'
    sku: 'Basic'
    associatedStorageAccountResourceId: hubStorage.id
    associatedKeyVaultResourceId: hubKeyVault.id
    associatedApplicationInsightsResourceId: appInsightsId
    connections: [
      {
        name: '${hubName}-ai-services'
        category: 'AIServices'
        target: 'https://${aiServicesName}.cognitiveservices.azure.com/'
        connectionProperties: {
          authType: 'AAD'
          // No secrets — uses Entra ID (AAD) authentication
        }
        metadata: {
          ApiType: 'Azure'
          ResourceId: aiServicesId
        }
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// AVM: AI Foundry Project (Azure ML workspace kind=Project)
// ---------------------------------------------------------------------------
module project 'br/public:avm/res/machine-learning-services/workspace:0.11.1' = {
  name: 'deploy-ai-foundry-project'
  params: {
    name: projectName
    location: location
    tags: tags
    kind: 'Project'
    sku: 'Basic'
    hubResourceId: hub.outputs.resourceId
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the AI Foundry hub.')
output hubId string = hub.outputs.resourceId

@description('Name of the AI Foundry hub.')
output hubName string = hub.outputs.name

@description('Resource ID of the AI Foundry project.')
output projectId string = project.outputs.resourceId

@description('Name of the AI Foundry project.')
output projectName string = project.outputs.name

@description('Resource ID of the hub storage account.')
output storageAccountId string = hubStorage.id

@description('Resource ID of the hub Key Vault.')
output keyVaultId string = hubKeyVault.id
