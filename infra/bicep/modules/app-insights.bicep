// ---------------------------------------------------------------------------
// Module: Application Insights
// Uses AVM: avm/res/insights/component
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the Application Insights component.')
param appInsightsName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Resource ID of the linked Log Analytics workspace.')
param workspaceResourceId string

@description('Application type.')
@allowed([
  'web'
  'other'
])
param applicationType string = 'web'

// ---------------------------------------------------------------------------
// AVM: Application Insights
// ---------------------------------------------------------------------------
module appInsights 'br/public:avm/res/insights/component:0.6.0' = {
  name: 'deploy-app-insights'
  params: {
    name: appInsightsName
    location: location
    tags: tags
    workspaceResourceId: workspaceResourceId
    kind: applicationType
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Application Insights component.')
output appInsightsId string = appInsights.outputs.resourceId

@description('Name of the Application Insights component.')
output appInsightsName string = appInsights.outputs.name

@description('Instrumentation key for Application Insights.')
output instrumentationKey string = appInsights.outputs.instrumentationKey

@description('Connection string for Application Insights.')
output connectionString string = appInsights.outputs.connectionString
