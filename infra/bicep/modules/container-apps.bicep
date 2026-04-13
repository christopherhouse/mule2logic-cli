// ---------------------------------------------------------------------------
// Module: container-apps.bicep — Container Apps Environment + API Container App
// ---------------------------------------------------------------------------
// Deploys the Container Apps Managed Environment (AVM) and the API Container
// App with UAMI identity attached and ACR identity-based image pull configured.
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

@description('Resource ID of the User Assigned Managed Identity.')
param uamiResourceId string

@description('Client ID of the User Assigned Managed Identity.')
param uamiClientId string

@description('ACR login server (e.g. acrm2ladev.azurecr.io).')
param acrLoginServer string

@description('Container image for the API app. Defaults to a placeholder; overridden by deploy script.')
param containerImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------
var envName = 'cae-m2la-${environmentName}'
var appName = 'ca-m2la-api-${environmentName}'

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
// AVM: Container App — API
// ---------------------------------------------------------------------------
// Uses UAMI for identity and ACR image pull (no admin credentials).
// The environmentResourceId reference ensures the environment is created first.
// ---------------------------------------------------------------------------
module containerApp 'br/public:avm/res/app/container-app:0.12.0' = {
  name: 'ca-${uniqueString(appName)}'
  params: {
    name: appName
    environmentResourceId: containerEnv.outputs.resourceId
    location: location
    tags: tags

    // Attach UAMI — used for ACR pull and Azure SDK DefaultAzureCredential
    managedIdentities: {
      userAssignedResourceIds: [
        uamiResourceId
      ]
    }

    // Identity-based ACR image pull (no admin credentials / passwords)
    registries: [
      {
        server: acrLoginServer
        identity: uamiResourceId
      }
    ]

    containers: [
      {
        name: 'm2la-api'
        image: containerImage
        // 0.5 vCPU / 1 GiB fits the Consumption profile minimum; sufficient for
        // the FastAPI-based translation API under moderate load.
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

    // Ingress — external HTTP on port 8000
    ingressExternal: true
    ingressTargetPort: 8000
    ingressTransport: 'auto'

    // Scaling — scale to zero, burst to 10 replicas on HTTP load
    scaleSettings: {
      minReplicas: 0
      maxReplicas: 10
      rules: [
        {
          name: 'http-scaling'
          http: {
            metadata: {
              concurrentRequests: '50' // scale out when a replica handles ≥ 50 concurrent requests
            }
          }
        }
      ]
    }

    // Run on the Consumption workload profile defined in the environment
    workloadProfileName: 'Consumption'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Name of the Container Apps Environment.')
output environmentName string = containerEnv.outputs.name

@description('Resource ID of the Container Apps Environment.')
output environmentResourceId string = containerEnv.outputs.resourceId

@description('Name of the Container App.')
output appName string = containerApp.outputs.name

@description('FQDN of the Container App.')
output appFqdn string = containerApp.outputs.fqdn
