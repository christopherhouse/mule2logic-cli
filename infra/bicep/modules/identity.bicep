// ---------------------------------------------------------------------------
// Module: identity.bicep — User Assigned Managed Identity (AVM)
// ---------------------------------------------------------------------------

@description('Name of the User Assigned Managed Identity.')
param name string

@description('Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

// ---------------------------------------------------------------------------
// AVM: User Assigned Managed Identity
// ---------------------------------------------------------------------------
module uami 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.0' = {
  name: 'uami-${uniqueString(name)}'
  params: {
    name: name
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Principal (object) ID of the UAMI.')
output principalId string = uami.outputs.principalId

@description('Client ID of the UAMI.')
output clientId string = uami.outputs.clientId

@description('Full resource ID of the UAMI.')
output resourceId string = uami.outputs.resourceId

@description('Name of the UAMI.')
output name string = uami.outputs.name
