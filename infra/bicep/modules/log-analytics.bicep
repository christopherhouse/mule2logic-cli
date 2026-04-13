// ---------------------------------------------------------------------------
// Module: Log Analytics Workspace
// Uses AVM: avm/res/operational-insights/workspace
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the Log Analytics workspace.')
param workspaceName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Log Analytics SKU.')
@allowed([
  'Free'
  'PerGB2018'
  'PerNode'
  'Premium'
  'Standalone'
  'Standard'
])
param skuName string = 'PerGB2018'

@description('Data retention in days (30–730).')
@minValue(30)
@maxValue(730)
param retentionInDays int = 30

// ---------------------------------------------------------------------------
// AVM: Log Analytics workspace
// ---------------------------------------------------------------------------
module workspace 'br/public:avm/res/operational-insights/workspace:0.11.1' = {
  name: 'deploy-log-analytics'
  params: {
    name: workspaceName
    location: location
    tags: tags
    skuName: skuName
    dataRetention: retentionInDays
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Log Analytics workspace.')
output workspaceId string = workspace.outputs.resourceId

@description('Name of the Log Analytics workspace.')
output workspaceName string = workspace.outputs.name

@description('Log Analytics workspace customer ID (workspace GUID, used by Container Apps Environment).')
output workspaceCustomerId string = workspace.outputs.logAnalyticsWorkspaceId
