// ---------------------------------------------------------------------------
// Module: AI Model Deployment
// Raw Bicep — AVM does not cover model deployments directly.
// Deploys a model (e.g. GPT-4o) via the AI Services account.
// ---------------------------------------------------------------------------

@description('Name of the AI Services account to deploy the model into.')
param aiServicesName string

@description('Name for the model deployment.')
param deploymentName string = 'gpt-4o'

@description('Model name to deploy.')
param modelName string = 'gpt-4o'

@description('Model version to deploy.')
param modelVersion string = '2024-11-20'

@description('Model format (Azure OpenAI uses "OpenAI").')
param modelFormat string = 'OpenAI'

@description('SKU name for the deployment.')
param skuName string = 'GlobalStandard'

@description('Capacity in thousands of tokens per minute (TPM).')
param skuCapacity int = 10

// ---------------------------------------------------------------------------
// Reference the existing AI Services account
// ---------------------------------------------------------------------------
resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiServicesName
}

// ---------------------------------------------------------------------------
// Model Deployment
// ---------------------------------------------------------------------------
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aiServicesAccount
  name: deploymentName
  sku: {
    name: skuName
    capacity: skuCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Name of the model deployment.')
output deploymentName string = modelDeployment.name

@description('Resource ID of the model deployment.')
output deploymentId string = modelDeployment.id
