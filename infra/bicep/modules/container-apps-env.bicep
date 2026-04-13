// ---------------------------------------------------------------------------
// Module: Azure Container Apps Environment
// Uses AVM: avm/res/app/managed-environment
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the Container Apps Environment.')
param environmentName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Log Analytics workspace customer ID (workspace GUID).')
param logAnalyticsCustomerId string

@description('Log Analytics workspace shared key (used at deployment time only).')
@secure()
param logAnalyticsSharedKey string

// ---------------------------------------------------------------------------
// AVM: Container Apps Managed Environment
// The Log Analytics connection uses appLogsConfiguration with a
// log-analytics destination. The shared key is consumed at deployment
// time by the platform and is NOT stored in any app configuration.
// ---------------------------------------------------------------------------
module managedEnv 'br/public:avm/res/app/managed-environment:0.11.1' = {
  name: 'deploy-container-apps-env'
  params: {
    name: environmentName
    location: location
    tags: tags
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    zoneRedundant: false // Single-zone for cost efficiency; override for prod
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Container Apps Environment.')
output environmentId string = managedEnv.outputs.resourceId

@description('Name of the Container Apps Environment.')
output environmentName string = managedEnv.outputs.name
