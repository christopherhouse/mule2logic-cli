// ---------------------------------------------------------------------------
// Module: Azure Container Registry
// Uses AVM: avm/res/container-registry/registry
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the Azure Container Registry (must be globally unique, alphanumeric).')
param registryName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('SKU for the Container Registry.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Basic'

@description('Enable admin user (should be false when using UAMI).')
param adminUserEnabled bool = false

// ---------------------------------------------------------------------------
// AVM: Container Registry
// ---------------------------------------------------------------------------
module registry 'br/public:avm/res/container-registry/registry:0.8.0' = {
  name: 'deploy-container-registry'
  params: {
    name: registryName
    location: location
    tags: tags
    acrSku: skuName
    acrAdminUserEnabled: adminUserEnabled
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Container Registry.')
output registryId string = registry.outputs.resourceId

@description('Name of the Container Registry.')
output registryName string = registry.outputs.name

@description('Login server of the Container Registry.')
output loginServer string = registry.outputs.loginServer
