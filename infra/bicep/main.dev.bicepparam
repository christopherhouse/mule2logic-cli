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
param aiModelDeploymentSkuName = 'GlobalStandard'
param aiModelDeploymentCapacity = 30
