// ---------------------------------------------------------------------------
// Parameter file: dev environment
// ---------------------------------------------------------------------------
using 'main.bicep'

param environmentName = 'dev'
param acrSkuName = 'Basic'
param containerImage = ''
param tags = {
  project: 'mule2logic'
  environment: 'dev'
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
