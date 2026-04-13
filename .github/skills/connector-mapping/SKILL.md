---
name: connector-mapping
description: "Connector mapping resolution logic, priority rules (built-in > identity-based > managed), mapping config format. Use when implementing or reviewing connector mappings, adding new connector support, or resolving mapping conflicts."
---

# Connector Mapping Resolution

## When to Use

- Implementing connector mapping resolution logic
- Adding new MuleSoft → Logic Apps connector mappings
- Reviewing mapping priority decisions
- Understanding mapping config file format

## Documentation Lookup

Use **Microsoft Learn MCP** (`microsoft_docs_search`) to verify Logic Apps built-in connector names, available authentication types, and service provider IDs when adding or reviewing mappings.

## Priority Rules

Mappings are resolved in strict priority order:

1. **Built-in Logic Apps connectors** (serviceProviderConnections) — always preferred
2. **Identity-based authentication** — always preferred over key/secret-based
3. **Managed/API connectors** (managedApiConnections) — last resort only

This priority is a hard product requirement. See `docs/mule2logic-cli-spec.md` §6.

## Mapping Config Format

Mappings are externalized in YAML under `packages/mapping-config/`. Never hardcode mappings in transformation logic.

### connector_mappings.yaml

```yaml
connectors:
  http-listener:
    mule_namespace: "http://www.mulesoft.org/schema/mule/http"
    mule_element: "listener"
    logic_apps:
      type: "trigger"
      kind: "Request"
      connector_type: "built-in"
      auth: "managed-identity"

  http-request:
    mule_namespace: "http://www.mulesoft.org/schema/mule/http"
    mule_element: "request"
    logic_apps:
      type: "action"
      kind: "Http"
      connector_type: "built-in"
      auth: "managed-identity"

  scheduler:
    mule_namespace: "http://www.mulesoft.org/schema/mule/core"
    mule_element: "scheduler"
    logic_apps:
      type: "trigger"
      kind: "Recurrence"
      connector_type: "built-in"

  db-select:
    mule_namespace: "http://www.mulesoft.org/schema/mule/db"
    mule_element: "select"
    logic_apps:
      type: "action"
      kind: "SqlServerQuery"
      connector_type: "built-in"
      auth: "managed-identity"

  sftp:
    mule_namespace: "http://www.mulesoft.org/schema/mule/sftp"
    mule_element: "*"
    logic_apps:
      type: "action"
      kind: "Sftp"
      connector_type: "built-in"
      auth: "managed-identity"

  jms:
    mule_namespace: "http://www.mulesoft.org/schema/mule/jms"
    mule_element: "*"
    logic_apps:
      type: "action"
      kind: "ServiceBus"
      connector_type: "built-in"
      auth: "managed-identity"
```

### construct_mappings.yaml

```yaml
constructs:
  choice:
    mule_element: "choice"
    logic_apps_type: "If"  # or "Switch" for multiple branches
    supported: true

  foreach:
    mule_element: "foreach"
    logic_apps_type: "Foreach"
    supported: true

  scatter-gather:
    mule_element: "scatter-gather"
    logic_apps_type: "Parallel"
    supported: true

  flow-ref:
    mule_element: "flow-ref"
    logic_apps_type: "Scope"
    supported: true

  set-payload:
    mule_element: "set-payload"
    logic_apps_type: "Compose"
    supported: true

  set-variable:
    mule_element: "set-variable"
    logic_apps_type: "SetVariable"
    supported: true

  dataweave-transform:
    mule_element: "ee:transform"
    logic_apps_type: "Compose"
    supported: true
    notes: "Basic patterns only; complex DataWeave requires manual review"

  error-handler:
    mule_element: "error-handler"
    logic_apps_type: "Scope+runAfter"
    supported: true
```

## Resolution Logic

1. Look up the Mule element (namespace + local name) in connector_mappings.
2. If found, return the Logic Apps mapping with the highest-priority connector type.
3. If multiple mappings exist, prefer: built-in > managed, identity-based > key-based.
4. If not found, check construct_mappings for control-flow constructs.
5. If neither found, emit an **explicit migration gap** — never silently drop.

## Adding New Mappings

1. Add the entry to the appropriate YAML config file.
2. Set `connector_type` and `auth` following priority rules.
3. Add tests verifying the mapping resolves correctly.
4. If the construct is not fully supported, set `supported: false` or add `notes` explaining limitations.
