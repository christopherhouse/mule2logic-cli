// ---------------------------------------------------------------------------
// Module: Azure AI Services (Cognitive Services) Account
// Uses AVM: avm/res/cognitive-services/account
// Required by Azure AI Foundry hub as the backing AI Services resource.
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the AI Services account.')
param aiServicesName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('SKU for the AI Services account.')
param skuName string = 'S0'

@description('Kind of Cognitive Services account.')
@allowed([
  'AIServices'
  'OpenAI'
  'CognitiveServices'
])
param kind string = 'AIServices'

@description('Whether to allow public network access.')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('Custom subdomain name for the Cognitive Services account (must be globally unique).')
param customSubDomainName string

// ---------------------------------------------------------------------------
// AVM: Cognitive Services Account
// ---------------------------------------------------------------------------
module aiServices 'br/public:avm/res/cognitive-services/account:0.11.0' = {
  name: 'deploy-ai-services'
  params: {
    name: aiServicesName
    location: location
    tags: tags
    sku: skuName
    kind: kind
    publicNetworkAccess: publicNetworkAccess
    customSubDomainName: customSubDomainName
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the AI Services account.')
output aiServicesId string = aiServices.outputs.resourceId

@description('Name of the AI Services account.')
output aiServicesName string = aiServices.outputs.name

@description('Endpoint of the AI Services account.')
output endpoint string = aiServices.outputs.endpoint
