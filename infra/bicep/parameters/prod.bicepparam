// ---------------------------------------------------------------------------
// Parameter file: prod environment
// ---------------------------------------------------------------------------
using '../main.bicep'

param environmentName = 'prod'

param resourcePrefix = 'm2l'

param tags = {
  costCenter: 'engineering'
}

// Production uses Standard SKU for geo-replication support
param containerRegistrySku = 'Standard'

// Production retains logs for 90 days
param logRetentionDays = 90

param containerImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

param containerPort = 8000

// Production always keeps at least 1 replica warm
param minReplicas = 1

param maxReplicas = 3

param gptModelVersion = '2024-11-20'

// Production has higher TPM capacity
param gptModelCapacity = 30
