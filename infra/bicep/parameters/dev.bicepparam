// ---------------------------------------------------------------------------
// Parameter file: dev environment
// ---------------------------------------------------------------------------
using '../main.bicep'

param environmentName = 'dev'

param resourcePrefix = 'm2l'

param tags = {
  costCenter: 'engineering'
}

param containerRegistrySku = 'Basic'

param logRetentionDays = 30

param containerImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

param containerPort = 8000

param minReplicas = 0

param maxReplicas = 3

param gptModelVersion = '2024-11-20'

param gptModelCapacity = 10
