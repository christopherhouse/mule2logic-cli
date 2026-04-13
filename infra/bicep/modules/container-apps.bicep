// ---------------------------------------------------------------------------
// Module: container-apps.bicep — Container Apps Environment + App (AVM)
// ---------------------------------------------------------------------------

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for the resources.')
param location string = resourceGroup().location

@description('Resource tags.')
param tags object = {}

@description('Resource ID of the User Assigned Managed Identity.')
param uamiResourceId string

@description('Client ID of the User Assigned Managed Identity.')
param uamiClientId string

@description('ACR login server (e.g., acrm2ladev.azurecr.io).')
param acrLoginServer string

@description('Resource ID of the Log Analytics workspace for Container Apps Environment.')
param logAnalyticsWorkspaceResourceId string

@description('Application Insights connection string for the container app.')
param appInsightsConnectionString string

@description('Full container image reference. If empty, uses placeholder.')
param containerImage string = ''

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var envName = 'cae-m2la-${environmentName}'
var appName = 'ca-m2la-api-${environmentName}'
var effectiveImage = !empty(containerImage) ? containerImage : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

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
// AVM: Container App — API Backend
// ---------------------------------------------------------------------------
module apiApp 'br/public:avm/res/app/container-app:0.12.0' = {
  name: 'ca-${uniqueString(appName)}'
  params: {
    name: appName
    location: location
    tags: tags
    environmentResourceId: containerEnv.outputs.resourceId
    managedIdentities: {
      userAssignedResourceIds: [
        uamiResourceId
      ]
    }
    registries: [
      {
        server: acrLoginServer
        identity: uamiResourceId
      }
    ]
    containers: [
      {
        name: 'api'
        image: effectiveImage
        resources: {
          cpu: '0.5'
          memory: '1Gi'
        }
        env: [
          {
            name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
            value: appInsightsConnectionString
          }
          {
            name: 'AZURE_CLIENT_ID'
            value: uamiClientId
          }
          {
            name: 'ENVIRONMENT'
            value: environmentName
          }
        ]
      }
    ]
    ingressExternal: true
    ingressTargetPort: !empty(containerImage) ? 8000 : 80
    ingressTransport: 'auto'
    scaleMinReplicas: 0
    scaleMaxReplicas: 10
    scaleRules: [
      {
        name: 'http-scaling'
        http: {
          metadata: {
            concurrentRequests: '50'
          }
        }
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('FQDN of the Container App.')
output fqdn string = apiApp.outputs.fqdn

@description('Name of the Container App.')
output appName string = apiApp.outputs.name

@description('Resource ID of the Container App.')
output appResourceId string = apiApp.outputs.resourceId

@description('Name of the Container Apps Environment.')
output environmentName string = containerEnv.outputs.name

@description('Resource ID of the Container Apps Environment.')
output environmentResourceId string = containerEnv.outputs.resourceId
