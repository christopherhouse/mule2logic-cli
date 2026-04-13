// ---------------------------------------------------------------------------
// Module: monitoring.bicep — Log Analytics + Application Insights (AVM)
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var logAnalyticsName = 'law-m2la-${environmentName}'
var appInsightsName = 'ai-m2la-${environmentName}'

// ---------------------------------------------------------------------------
// AVM: Log Analytics Workspace
// ---------------------------------------------------------------------------
module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.9.1' = {
  name: 'law-${uniqueString(logAnalyticsName)}'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
  }
}

// ---------------------------------------------------------------------------
// AVM: Application Insights
// ---------------------------------------------------------------------------
module appInsights 'br/public:avm/res/insights/component:0.4.2' = {
  name: 'ai-${uniqueString(appInsightsName)}'
  params: {
    name: appInsightsName
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.resourceId
    kind: 'web'
    applicationType: 'web'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Log Analytics workspace.')
output logAnalyticsWorkspaceResourceId string = logAnalytics.outputs.resourceId

@description('Name of the Log Analytics workspace.')
output logAnalyticsWorkspaceName string = logAnalytics.outputs.name

@description('Resource ID of the Application Insights instance.')
output appInsightsResourceId string = appInsights.outputs.resourceId

@description('Application Insights connection string.')
output appInsightsConnectionString string = appInsights.outputs.connectionString

@description('Application Insights instrumentation key.')
output appInsightsInstrumentationKey string = appInsights.outputs.instrumentationKey

@description('Name of the Application Insights instance.')
output appInsightsName string = appInsights.outputs.name
