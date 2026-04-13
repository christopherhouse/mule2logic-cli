// ---------------------------------------------------------------------------
// Parameter file: prod environment
// ---------------------------------------------------------------------------
using 'main.bicep'

param environmentName = 'prod'
param acrSkuName = 'Standard'
param containerImage = ''
param tags = {
  project: 'mule2logic'
  environment: 'prod'
  managedBy: 'bicep'
}
param aiModelDeployments = [
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
