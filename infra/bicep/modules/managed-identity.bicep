// ---------------------------------------------------------------------------
// Module: User Assigned Managed Identity
// Uses AVM: avm/res/managed-identity/user-assigned-identity
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the User Assigned Managed Identity.')
param identityName string

@description('Tags to apply to the resource.')
param tags object = {}

// ---------------------------------------------------------------------------
// AVM: User Assigned Managed Identity
// ---------------------------------------------------------------------------
module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.5.0' = {
  name: 'deploy-managed-identity'
  params: {
    name: identityName
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the managed identity.')
output identityId string = identity.outputs.resourceId

@description('Client ID of the managed identity.')
output clientId string = identity.outputs.clientId

@description('Principal ID of the managed identity.')
output principalId string = identity.outputs.principalId

@description('Name of the managed identity.')
output identityName string = identity.outputs.name
