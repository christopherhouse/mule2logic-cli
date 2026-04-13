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
param aiModelDeploymentSkuName = 'GlobalStandard'
param aiModelDeploymentCapacity = 30
