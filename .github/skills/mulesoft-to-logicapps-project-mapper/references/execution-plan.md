# Execution Plan Reference

The execution plan must be phased, ordered, and actionable. Always include these phases unless clearly not applicable to the source project.

## Required Phases

### Phase 1 — Repository Discovery
**Goal:** Enumerate all files, confirm project boundaries, identify multi-app scenarios.
- Scan directory tree
- Identify `pom.xml`, `mule-artifact.json`, and app boundaries
- List all Mule XML, DWL, config, and test files
- **Outputs:** File inventory, application boundary map

### Phase 2 — Mule Inventory and Classification
**Goal:** Classify every flow, subflow, connector, transform, and config element.
- Parse each Mule XML file for flows and subflows
- Catalog connectors and operations
- Classify transforms by complexity
- Identify error handling patterns
- **Outputs:** Classified inventory per application

### Phase 3 — Target App Partitioning
**Goal:** Decide how many Logic Apps Standard apps to create and why.
- Apply the one-app-per-Mule-app default
- Evaluate whether domain splits are needed
- Assign workflows to apps
- **Outputs:** App-to-workflow assignment with rationale

### Phase 4 — Workflow Skeleton Generation
**Goal:** Define the trigger, actions summary, and structure for each target workflow.
- Map each source flow to a target workflow definition
- Determine trigger type
- Outline action sequence at summary level
- **Outputs:** Workflow skeleton definitions

### Phase 5 — Connection and Parameter Extraction
**Goal:** Map all Mule connection configs and properties to Logic Apps equivalents.
- Extract global element configs → `connections.json` entries
- Extract properties → app settings and parameters
- Identify secrets → Key Vault references
- **Outputs:** Connection map, parameter map, secrets inventory (redacted)

### Phase 6 — Transform Migration
**Goal:** Plan the conversion of each DataWeave/XSLT/map artifact.
- Classify each transform's target (WDL, Liquid, XSLT, Azure Function)
- Identify schema dependencies
- Flag complex procedural transforms for manual review
- **Outputs:** Transform migration plan with target recommendations

### Phase 7 — Error Handling and Resiliency Migration
**Goal:** Map Mule error handling patterns to Logic Apps equivalents.
- Map on-error-propagate/continue → scope + runAfter patterns
- Map retry configs → retry policies
- Map DLQ patterns → Service Bus dead-letter or error workflows
- **Outputs:** Error handling migration map

### Phase 8 — Test Strategy and Validation
**Goal:** Define how to validate the migrated workflows.
- Review existing MUnit tests for reusable test scenarios
- Define integration test approach for Logic Apps
- Plan smoke tests for each workflow
- **Outputs:** Test strategy document, reusable scenario list

### Phase 9 — Packaging and Deployment Preparation
**Goal:** Prepare the Logic Apps Standard project for deployment.
- Define folder structure per Logic Apps Standard conventions
- Plan ARM/Bicep templates or azd configuration
- Define environment-specific parameter files
- **Outputs:** Deployment-ready project scaffold plan

## Task Requirements

For each task within a phase, specify:

| Field | Description |
|-------|-------------|
| `id` | Pattern: `P{phase}-T{task}` |
| `title` | Clear, action-oriented title |
| `sourceArtifacts` | Mule files this task reads |
| `targetArtifacts` | Logic Apps files this task produces |
| `approach` | Brief description of conversion method |
| `dependsOn` | List of task IDs that must complete first |
| `automationLevel` | `automatic` / `semi-automatic` / `manual` |
| `riskLevel` | `low` / `medium` / `high` |
| `acceptanceCriteria` | Verifiable conditions for task completion |

## Automation Levels

- **Automatic:** Can be converted programmatically with high confidence (e.g., simple HTTP trigger mapping)
- **Semi-automatic:** Tool-assisted but needs human review (e.g., moderate DataWeave → WDL)
- **Manual:** Requires human design decisions (e.g., proprietary connector replacement, architectural changes)
