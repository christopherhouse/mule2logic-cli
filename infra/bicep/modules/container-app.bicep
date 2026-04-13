// ---------------------------------------------------------------------------
// Module: Azure Container App (backend API)
// Uses AVM: avm/res/app/container-app
// ---------------------------------------------------------------------------

@description('Azure region for the resource.')
param location string

@description('Name of the Container App.')
param containerAppName string

@description('Tags to apply to the resource.')
param tags object = {}

@description('Resource ID of the Container Apps Environment.')
param environmentResourceId string

@description('Resource ID of the User Assigned Managed Identity.')
param identityResourceId string

@description('Container image to deploy (use placeholder initially).')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Target port for the container (FastAPI default).')
param targetPort int = 8000

@description('Enable external ingress.')
param externalIngress bool = true

@description('Minimum number of replicas.')
@minValue(0)
@maxValue(30)
param minReplicas int = 0

@description('Maximum number of replicas.')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

@description('Login server of the Azure Container Registry.')
param acrLoginServer string

@description('Application Insights connection string for telemetry.')
param appInsightsConnectionString string = ''

// ---------------------------------------------------------------------------
// AVM: Container App
// ---------------------------------------------------------------------------
module containerApp 'br/public:avm/res/app/container-app:0.14.0' = {
  name: 'deploy-container-app'
  params: {
    name: containerAppName
    location: location
    tags: tags
    environmentResourceId: environmentResourceId
    managedIdentities: {
      userAssignedResourceIds: [
        identityResourceId
      ]
    }
    registries: [
      {
        server: acrLoginServer
        identity: identityResourceId
      }
    ]
    containers: [
      {
        name: 'api'
        image: containerImage
        resources: {
          cpu: '0.5'
          memory: '1Gi'
        }
        env: concat(
          [
            {
              name: 'PORT'
              value: string(targetPort)
            }
          ],
          // Only include App Insights connection string if provided
          !empty(appInsightsConnectionString)
            ? [
                {
                  name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
                  value: appInsightsConnectionString
                }
              ]
            : []
        )
      }
    ]
    ingressExternal: externalIngress
    ingressTargetPort: targetPort
    ingressTransport: 'auto'
    scaleSettings: {
      minReplicas: minReplicas
      maxReplicas: maxReplicas
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
@description('Resource ID of the Container App.')
output containerAppId string = containerApp.outputs.resourceId

@description('Name of the Container App.')
output containerAppName string = containerApp.outputs.name

@description('FQDN of the Container App.')
output fqdn string = containerApp.outputs.fqdn
