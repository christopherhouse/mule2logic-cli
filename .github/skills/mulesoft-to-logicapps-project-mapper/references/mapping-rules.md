# Mapping Rules Reference

## Flow Mapping

| MuleSoft Pattern | Logic Apps Target | When to Use |
|------------------|-------------------|-------------|
| Flow with trigger/source | Workflow | Distinct trigger, independently callable, separate scaling |
| Subflow (reused by multiple parents) | Child workflow | Clear input/output semantics, orchestration-heavy |
| Subflow (single caller, simple) | Inline action scope | Logic is local and doesn't need independent lifecycle |
| Subflow (complex logic, libraries) | Azure Function | Custom Java, unsupported constructs, library dependencies |
| Flow with no good analogue | Manual redesign | Proprietary connectors, non-preservable transactions |

## Connector Mapping

Use this preference order:

1. **Built-in / in-app Logic Apps Standard connectors** — ALWAYS prefer these. They run in-process, have lower latency, and do not require a separate API connection.
2. **Azure Functions / custom code** — for logic that has no built-in connector equivalent.
3. **Managed / API connectors** — LAST RESORT only. Use only when no built-in connector exists and an Azure Function wrapper is impractical. Managed connectors run out-of-process and incur additional cost and latency.
4. **Custom connectors** — only when the target system has no native option and HTTP abstraction is stable.

> **Key rule:** If a built-in (in-app) connector exists for a given system, you MUST use it instead of the managed (API) connector, even if both are available.

Common connector mappings:

| MuleSoft Connector | Logic Apps Equivalent | Notes |
|--------------------|----------------------|-------|
| HTTP Listener | Request trigger (HTTP) | Built-in |
| HTTP Request | HTTP action | Built-in |
| Salesforce | Salesforce managed connector | |
| Database (JDBC) | SQL / specific DB connector | Depends on DB type |
| File / FTP / SFTP | File System / FTP / SFTP connector | |
| JMS / IBM MQ | IBM MQ connector or Service Bus | May need custom connector |
| Kafka | Kafka connector or Event Hubs | Consider Event Hubs for Azure-native |
| Azure Service Bus | Service Bus Built-in connector | |
| SAP | SAP managed connector | Requires on-prem gateway for some scenarios |
| SOAP/WSDL | HTTP + XML parsing or custom connector | |
| Email (SMTP/IMAP) | Office 365 / Outlook connector | Or SMTP built-in |
| Object Store | Azure Blob / Table Storage | Or workflow state |
| VM queues | Child workflow calls or Service Bus | Pattern-dependent |
| Scheduler / Poll | Recurrence trigger | Built-in |

## Transformation Mapping

| Classification | Recommended Target | Rationale |
|---------------|-------------------|-----------|
| Simple field mapping | WDL expressions | Native, no extra components |
| Structural reshape | Liquid template or WDL | Maintainable for moderate complexity |
| XSLT source | XSLT map in Logic Apps | Direct support via integration account |
| Aggregation / join | Azure Function | WDL lacks native aggregation |
| Enrichment (API calls) | Workflow actions + WDL | Use HTTP actions to fetch, WDL to merge |
| Conditional mapping | WDL with `if()` expressions | Native support |
| Complex procedural DataWeave | Azure Function | Too complex for WDL, needs code |
| Custom Java module | Azure Function (.NET/Java) | Rewrite or wrap existing logic |

## Error Handling Mapping

| MuleSoft Pattern | Logic Apps Equivalent |
|------------------|----------------------|
| On Error Propagate | `runAfter` with `Failed` status on parent scope |
| On Error Continue | Scope with `runAfter: Failed` that does not terminate |
| Try scope | Scope action (acts as try block) |
| Retry | Retry policy on action (fixed / exponential) |
| DLQ / error queue | Service Bus dead-letter or error-handling workflow |
| Global error handler | Top-level scope wrapping all actions |
| Raise error | Terminate action with `Failed` status |

## Authentication Mapping

Use this preference order for connection authentication:

1. **Managed Identity** — ALWAYS prefer system-assigned or user-assigned managed identity where the target connector supports it. This eliminates credential management and is the most secure option.
2. **Key Vault references** — for secrets that cannot use managed identity (e.g., third-party API keys, on-prem credentials).
3. **Connection strings / raw credentials** — LAST RESORT. Only when managed identity and Key Vault are not supported.

> **Key rule:** When mapping a Mule connection config to Logic Apps, default the `authenticationModel` to `ManagedIdentity` unless there is a clear reason the target connector does not support it.

## Configuration Mapping

| MuleSoft Source | Logic Apps Target |
|----------------|-------------------|
| `application.properties` values | App settings |
| `application-{env}.properties` | Deployment-time parameterization |
| Secure properties | Key Vault references or secure parameters |
| Connection configs (global elements) | `connections.json` entries |
| Endpoint URLs | App settings or parameters |
| Credentials | Managed Identity where supported, otherwise Key Vault references |
| Feature toggles | App settings with parameter references |

## Decision Heuristics

### Create separate workflows when:
- A Mule flow has a distinct trigger
- A flow is independently callable
- A flow represents a durable business process
- A flow has separate operational ownership or scaling needs

### Prefer child workflows when:
- Logic is reused by multiple parent flows
- The logic is orchestration-heavy but not a system boundary
- The source subflow has clear input/output contract

### Prefer Azure Functions when:
- DataWeave logic is complex or procedural
- Custom Java modules are involved
- The logic requires libraries not native to Logic Apps
- Transformation quality would be poor in WDL alone

### Mark as manual redesign when:
- The Mule pattern has no good Logic Apps analogue
- The repo depends on unsupported proprietary connectors
- Transactional semantics cannot be preserved directly
- The architecture should shift to Azure-native eventing patterns
