// ---------------------------------------------------------------------------
// Module: container-apps.bicep — Container Apps Managed Environment (AVM)
// ---------------------------------------------------------------------------
// Deploys ONLY the Container Apps Environment. The Container App itself is
// deployed via the infra/scripts/deploy-container-app.sh script after the
// container image is pushed to ACR. This separation avoids Bicep deployment
// failures when the container image or app configuration changes.
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

@description('Resource ID of the Log Analytics workspace for Container Apps Environment.')
param logAnalyticsWorkspaceResourceId string

@description('Application Insights connection string for environment-level telemetry.')
param appInsightsConnectionString string

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var envName = 'cae-m2la-${environmentName}'

// ---------------------------------------------------------------------------
// AVM: Container Apps Managed Environment
// ---------------------------------------------------------------------------
module containerEnv 'br/public:avm/res/app/managed-environment:0.8.1' = {
  name: 'cae-${uniqueString(envName)}'
  params: {
    name: envName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspaceResourceId
    appInsightsConnectionString: appInsightsConnectionString
    zoneRedundant: false
    // Enable workload profiles mode with Consumption profile
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Name of the Container Apps Environment.')
output environmentName string = containerEnv.outputs.name

@description('Resource ID of the Container Apps Environment.')
output environmentResourceId string = containerEnv.outputs.resourceId
