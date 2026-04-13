// ---------------------------------------------------------------------------
// Module: Role Assignments (least-privilege, UAMI-based)
// Raw Bicep — role assignments are simple and don't need AVM.
//
// Assigns the minimum roles required for the platform UAMI to:
//   1. Pull images from ACR  (AcrPull)
//   2. Use OpenAI models     (Cognitive Services OpenAI User)
// ---------------------------------------------------------------------------

@description('Principal ID of the User Assigned Managed Identity.')
param principalId string

@description('Name of the Azure Container Registry (extracted from resource ID).')
param containerRegistryName string

@description('Name of the AI Services account (extracted from resource ID).')
param aiServicesAccountName string

// ---------------------------------------------------------------------------
// Well-known built-in role definition IDs
// See: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
// ---------------------------------------------------------------------------

// AcrPull: Pull artifacts from a container registry
// ID: 7f951dda-4ed3-4680-a7ca-43fe172d538d
var acrPullRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

// Cognitive Services OpenAI User: Read access to view files, models, deployments;
// ability to create completions and embeddings.
// ID: 5e0bd9bd-7b93-4f28-af87-19fc36ad61bd
var cognitiveServicesOpenAIUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)

// ---------------------------------------------------------------------------
// Existing resource references for scoping
// ---------------------------------------------------------------------------
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: containerRegistryName
}

resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiServicesAccountName
}

// ---------------------------------------------------------------------------
// 1. AcrPull on Azure Container Registry
// ---------------------------------------------------------------------------
resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // Deterministic name using a GUID seeded from the principal, registry, and role
  name: guid(containerRegistry.id, principalId, acrPullRoleId)
  scope: containerRegistry
  properties: {
    roleDefinitionId: acrPullRoleId
    principalId: principalId
    principalType: 'ServicePrincipal' // Managed identities use ServicePrincipal type
  }
}

// ---------------------------------------------------------------------------
// 2. Cognitive Services OpenAI User on AI Services account
// ---------------------------------------------------------------------------
resource openAIUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // Deterministic name using a GUID seeded from the principal, AI Services, and role
  name: guid(aiServicesAccount.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: aiServicesAccount
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    principalId: principalId
    principalType: 'ServicePrincipal' // Managed identities use ServicePrincipal type
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Role assignment ID for AcrPull.')
output acrPullAssignmentId string = acrPullAssignment.id

@description('Role assignment ID for Cognitive Services OpenAI User.')
output openAIUserAssignmentId string = openAIUserAssignment.id
