// ---------------------------------------------------------------------------
// Parameter file: test environment
// ---------------------------------------------------------------------------
using 'main.bicep'

param environmentName = 'test'
param acrSkuName = 'Basic'
param containerImage = ''
param tags = {
  project: 'mule2logic'
  environment: 'test'
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
