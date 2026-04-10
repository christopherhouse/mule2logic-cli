# Output Contract Reference

The JSON conversion model must conform to the structure below. All fields are required unless marked optional.

## Top-level Structure

```json
{
  "assessmentVersion": "1.0",
  "source": { ... },
  "target": { ... },
  "executionPlan": { ... }
}
```

## Source Model

```json
{
  "source": {
    "rootPath": "<absolute path to MuleSoft project>",
    "applications": [
      {
        "name": "string",
        "packaging": "mule4-application",
        "files": ["string"],
        "businessCapabilities": ["string"],
        "entryPoints": ["string"],
        "flows": [
          {
            "name": "string",
            "file": "string",
            "triggerType": "http-listener|scheduler|vm-listener|jms|none|...",
            "operations": ["string"],
            "errorHandling": "string (summary)",
            "transactionality": "none|local|xa"
          }
        ],
        "subflows": ["string"],
        "dependencies": [
          {
            "name": "string",
            "category": "http|soap|database|messaging|file|saas|custom",
            "connector": "string (Mule connector name)",
            "operations": ["string"],
            "logicAppsEquivalent": "string",
            "migrationNotes": "string"
          }
        ],
        "transforms": [
          {
            "name": "string",
            "file": "string (optional, for external .dwl)",
            "classification": "simple-mapping|reshape|aggregation|enrichment|conditional|complex-procedural|unsupported",
            "inputs": ["string"],
            "outputs": ["string"],
            "recommendedTarget": "wdl|liquid|xslt|azure-function|manual"
          }
        ],
        "config": {
          "propertyFiles": ["string"],
          "secureProperties": ["string (redacted key names)"],
          "connectionConfigs": ["string"]
        },
        "tests": [
          {
            "name": "string",
            "file": "string",
            "type": "munit|integration"
          }
        ],
        "observability": {
          "loggingConfig": "string (optional)",
          "correlationIds": true,
          "errorNotifications": "string (optional)"
        },
        "risks": [
          {
            "description": "string",
            "severity": "low|medium|high",
            "mitigation": "string"
          }
        ]
      }
    ]
  }
}
```

## Target Model

```json
{
  "target": {
    "logicAppsStandardApps": [
      {
        "name": "string",
        "rationale": "string (why this app boundary)",
        "workflows": [
          {
            "name": "string",
            "sourceArtifacts": ["string (file paths)"],
            "trigger": {
              "type": "string",
              "sourceElement": "string"
            },
            "actionsSummary": ["string (high-level action descriptions)"],
            "childWorkflow": false,
            "recommendedImplementation": "workflow|child-workflow|azure-function|custom-connector|manual-redesign",
            "dependencies": ["string"],
            "parameters": ["string"],
            "maps": ["string"],
            "riskLevel": "low|medium|high"
          }
        ],
        "connections": [
          {
            "name": "string",
            "type": "built-in|managed|custom",
            "sourceConfigs": ["string (Mule global element names)"],
            "authenticationModel": "string",
            "notes": "string"
          }
        ],
        "appSettings": ["string (key names, no values)"],
        "artifacts": {
          "schemas": ["string"],
          "maps": ["string"],
          "assemblies": ["string"]
        }
      }
    ]
  }
}
```

## Execution Plan Model

```json
{
  "executionPlan": {
    "phases": [
      {
        "phase": 1,
        "name": "string",
        "goal": "string",
        "inputs": ["string"],
        "outputs": ["string"],
        "tasks": [
          {
            "id": "P1-T1",
            "title": "string",
            "sourceArtifacts": ["string"],
            "targetArtifacts": ["string"],
            "approach": "string",
            "dependsOn": ["string (task IDs)"],
            "automationLevel": "automatic|semi-automatic|manual",
            "riskLevel": "low|medium|high",
            "acceptanceCriteria": ["string"]
          }
        ]
      }
    ]
  }
}
```

## Notes

- Redact all secret values. Only include key names for secure properties.
- Use exact file paths from the source project — do not invent paths.
- Every `riskLevel` should have a corresponding entry in the source `risks` array when medium or high.
- Task IDs follow the pattern `P{phase}-T{task}` (e.g., `P1-T1`, `P3-T2`).
