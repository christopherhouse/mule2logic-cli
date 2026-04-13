// ---------------------------------------------------------------------------
// Module: ai-foundry.bicep — AI Services account + project + model deployments
// Uses AVM for Cognitive Services account; raw Bicep for project (no AVM exists)
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

@description('Principal ID of the UAMI to grant Cognitive Services OpenAI User role.')
param uamiPrincipalId string

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
// AVM: Cognitive Services Account (kind: AIServices)
// Provisions the AI Services account with model deployments and UAMI role assignments
// ---------------------------------------------------------------------------
module aiServices 'br/public:avm/res/cognitive-services/account:0.14.2' = {
  name: 'ais-${uniqueString(aiServicesName)}'
  params: {
    name: aiServicesName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    customSubDomainName: 'ais-m2la-${environmentName}-${uniqueString(resourceGroup().id)}'
    disableLocalAuth: true // AAD-only, no key-based auth
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true // Required for AI Foundry project creation
    deployments: aiModelDeployments
    roleAssignments: [
      {
        principalId: uamiPrincipalId
        roleDefinitionIdOrName: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Raw Bicep: AI Foundry Project (no AVM resource module exists for projects)
// ---------------------------------------------------------------------------
resource aiFoundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: '${aiServicesName}/${projectName}'
  location: location
  tags: tags
  properties: {
    displayName: 'MuleSoft to Logic Apps - ${environmentName}'
    description: 'AI Foundry project for the MuleSoft to Logic Apps migration platform.'
  }
  dependsOn: [
    aiServices
  ]
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Name of the AI Foundry project.')
output projectName string = projectName

@description('Name of the AI Services account.')
output aiServicesName string = aiServices.outputs.name

@description('AI Services account endpoint.')
output aiServicesEndpoint string = aiServices.outputs.endpoint
