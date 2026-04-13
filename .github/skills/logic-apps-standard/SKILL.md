---
name: logic-apps-standard
description: "Logic Apps Standard project structure, workflow.json schema, host.json, connections.json, parameters.json conventions. Use when generating, validating, or reviewing Logic Apps output artifacts."
---

# Logic Apps Standard Project Structure

## When to Use

- Generating Logic Apps project output from IR
- Validating generated Logic Apps artifacts
- Understanding workflow.json action/trigger schema
- Reviewing connections.json or host.json configuration

## Documentation Lookup

Use **Microsoft Learn MCP** (`microsoft_docs_search` / `microsoft_docs_fetch`) to validate Logic Apps Standard schema details, connector configurations, and workflow definition syntax. Search for "Logic Apps Standard workflow definition" or specific action/trigger types.

## Project Layout

A valid Logic Apps Standard project has this structure:

```
<project-root>/
├── host.json
├── connections.json
├── parameters.json
├── .env
└── workflows/
    └── <workflow-name>/
        └── workflow.json
```

### host.json

Configures the Logic Apps runtime. Minimal example:

```json
{
  "version": "2.0",
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
    "version": "[1.*, 2.0.0)"
  }
}
```

### connections.json

Defines connector connections. For built-in connectors with managed identity:

```json
{
  "managedApiConnections": {},
  "serviceProviderConnections": {
    "<connection-name>": {
      "parameterValues": {
        "authProvider": {
          "Type": "ManagedServiceIdentity"
        }
      },
      "serviceProvider": {
        "id": "/serviceProviders/<provider>"
      },
      "displayName": "<display>"
    }
  }
}
```

### parameters.json

Externalized parameters referenced in workflows:

```json
{
  "<param-name>": {
    "type": "String",
    "value": "<value-or-appsetting-reference>"
  }
}
```

### .env

Environment variables for local development. **Must contain only placeholders/mock values — no real secrets.**

```
WORKFLOWS_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000
WORKFLOWS_RESOURCE_GROUP=rg-placeholder
WORKFLOWS_MANAGED_IDENTITY_CLIENT_ID=00000000-0000-0000-0000-000000000000
```

## workflow.json Schema

Each workflow is a stateful or stateless Logic Apps definition:

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "triggers": {
      "<trigger-name>": { ... }
    },
    "actions": {
      "<action-name>": {
        "type": "<action-type>",
        "inputs": { ... },
        "runAfter": {}
      }
    },
    "outputs": {}
  },
  "kind": "Stateful"
}
```

### Common Trigger Types

| Trigger | Type | Use Case |
|---------|------|----------|
| Request | `Request` | HTTP listener (maps from Mule HTTP Listener) |
| Recurrence | `Recurrence` | Scheduled execution (maps from Mule Scheduler) |

### Common Action Types

| Action | Type | Use Case |
|--------|------|----------|
| HTTP | `Http` | Outbound HTTP calls |
| Condition | `If` | Choice router |
| Switch | `Switch` | Multi-branch choice |
| Foreach | `Foreach` | Loop over array |
| Scope | `Scope` | Group actions (maps from subflows) |
| Compose | `Compose` | Set variable / transform data |
| SetVariable | `SetVariable` | Mutate workflow variable |
| InitializeVariable | `InitializeVariable` | Declare variable |

### runAfter

Controls execution order. Each action declares which actions must complete before it runs:

```json
"runAfter": {
  "Previous_Action": ["Succeeded"]
}
```

Valid statuses: `Succeeded`, `Failed`, `Skipped`, `TimedOut`. Used for error handling (maps from Mule error handlers).

## Identity

- Always use **User Assigned Managed Identity**.
- Reference via `ManagedServiceIdentity` auth type in connections.
- No connection strings or secrets in any artifact.

## Connector Priority

1. **Built-in connectors** (serviceProviderConnections) — preferred
2. **Identity-based auth** — always preferred over key-based
3. **Managed/API connectors** (managedApiConnections) — last resort
