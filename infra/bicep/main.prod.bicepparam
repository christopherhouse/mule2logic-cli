// ---------------------------------------------------------------------------
// Parameter file: prod environment
// ---------------------------------------------------------------------------
using 'main.bicep'

param environmentName = 'prod'
param acrSkuName = 'Standard'
param tags = {
  project: 'mule2logic'
  environment: 'prod'
  managedBy: 'bicep'
}
param aiModelDeploymentSkuName = 'GlobalStandard'
param aiModelDeploymentCapacity = 50
