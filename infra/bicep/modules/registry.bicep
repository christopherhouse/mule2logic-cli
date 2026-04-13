// ---------------------------------------------------------------------------
// Module: registry.bicep — Azure Container Registry (AVM)
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

@description('Principal ID of the UAMI to grant AcrPull.')
param uamiPrincipalId string

@description('ACR SKU. Use Basic for dev, Standard for prod.')
@allowed(['Basic', 'Standard', 'Premium'])
param skuName string = 'Basic'

// ---------------------------------------------------------------------------
// Naming — ACR names must be globally unique, alphanumeric only
// ---------------------------------------------------------------------------
var acrName = 'acrm2la${environmentName}${uniqueString(resourceGroup().id)}'

// ---------------------------------------------------------------------------
// AVM: Azure Container Registry
// ---------------------------------------------------------------------------
module acr 'br/public:avm/res/container-registry/registry:0.6.0' = {
  name: 'acr-${uniqueString(acrName)}'
  params: {
    name: acrName
    location: location
    tags: tags
    acrSku: skuName
    // Grant UAMI the AcrPull role for Container Apps image pulling
    roleAssignments: [
      {
        principalId: uamiPrincipalId
        roleDefinitionIdOrName: '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
        principalType: 'ServicePrincipal'
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('ACR login server (e.g., acrm2ladev.azurecr.io).')
output loginServer string = acr.outputs.loginServer

@description('ACR resource name.')
output name string = acr.outputs.name

@description('ACR resource ID.')
output resourceId string = acr.outputs.resourceId
