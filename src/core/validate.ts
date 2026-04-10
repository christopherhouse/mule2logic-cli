export interface WorkflowDefinition {
  definition: {
    $schema?: string;
    contentVersion?: string;
    triggers: Record<string, TriggerAction>;
    actions: Record<string, WorkflowAction>;
    parameters?: Record<string, unknown>;
    staticResults?: Record<string, unknown>;
  };
}

export interface TriggerAction {
  type?: string;
  kind?: string;
  inputs?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface WorkflowAction {
  type?: string;
  inputs?: unknown;
  runAfter?: Record<string, string[]>;
  expression?: unknown;
  actions?: Record<string, WorkflowAction>;
  else?: { actions: Record<string, WorkflowAction> };
  foreach?: string;
  [key: string]: unknown;
}

export function validateJson(output: string): WorkflowDefinition {
  if (typeof output !== 'string' || output.trim() === '') {
    throw new Error('Output is empty or not a string');
  }

  const cleaned = cleanJsonOutput(output);

  let parsed: WorkflowDefinition;
  try {
    parsed = JSON.parse(cleaned) as WorkflowDefinition;
  } catch {
    throw new Error('Output is not valid JSON');
  }

  if (!parsed.definition || typeof parsed.definition !== 'object') {
    throw new Error('Missing required "definition" property');
  }

  if (!parsed.definition.actions || typeof parsed.definition.actions !== 'object') {
    throw new Error('Missing required "definition.actions" property');
  }

  return parsed;
}

/**
 * Deep structural validation of a Logic Apps workflow definition.
 * Returns an array of warning/error strings. Empty array means valid.
 */
export function validateWorkflowStructure(parsed: WorkflowDefinition): string[] {
  const issues: string[] = [];
  const def = parsed.definition;

  // Check triggers
  if (def.triggers && typeof def.triggers === 'object') {
    for (const [name, trigger] of Object.entries(def.triggers)) {
      if (!trigger.type || typeof trigger.type !== 'string') {
        issues.push(`Trigger "${name}" is missing a "type" field`);
      }
    }
  }

  // Check actions
  const actionNames = new Set(Object.keys(def.actions));

  for (const [name, action] of Object.entries(def.actions)) {
    if (!action.type || typeof action.type !== 'string') {
      issues.push(`Action "${name}" is missing a "type" field`);
    }

    // Validate runAfter references point to existing actions
    if (action.runAfter && typeof action.runAfter === 'object') {
      for (const dep of Object.keys(action.runAfter)) {
        if (!actionNames.has(dep)) {
          issues.push(`Action "${name}" has runAfter reference to non-existent action "${dep}"`);
        }
      }
    }

    // Condition actions must have If/Else structure
    if (action.type === 'If') {
      if (!action.expression) {
        issues.push(`Condition action "${name}" is missing "expression"`);
      }
      if (!action.actions && !action.else) {
        issues.push(`Condition action "${name}" has no "actions" or "else" branches`);
      }
    }

    // Foreach must have forEach and actions
    if (action.type === 'Foreach') {
      if (!action.foreach) {
        issues.push(`Foreach action "${name}" is missing "foreach" input`);
      }
      if (!action.actions || typeof action.actions !== 'object') {
        issues.push(`Foreach action "${name}" is missing nested "actions"`);
      }
    }
  }

  return issues;
}

// --- Conversion Model types (project mode) ---

export interface ConversionModelFlow {
  name: string;
  file: string;
  triggerType: string;
  operations: string[];
  errorHandling?: string;
  transactionality?: string;
}

export interface ConversionModelDependency {
  name: string;
  category: string;
  connector: string;
  operations: string[];
  logicAppsEquivalent: string;
  migrationNotes?: string;
}

export interface ConversionModelTransform {
  name: string;
  file?: string;
  classification: string;
  inputs: string[];
  outputs: string[];
  recommendedTarget: string;
}

export interface ConversionModelApp {
  name: string;
  packaging?: string;
  files: string[];
  businessCapabilities?: string[];
  entryPoints?: string[];
  flows: ConversionModelFlow[];
  subflows?: string[];
  dependencies: ConversionModelDependency[];
  transforms: ConversionModelTransform[];
  config?: Record<string, unknown>;
  tests?: unknown[];
  observability?: Record<string, unknown>;
  risks?: Array<{ description: string; severity: string; mitigation: string }>;
}

export interface ConversionModelWorkflow {
  name: string;
  sourceArtifacts: string[];
  trigger: { type: string; sourceElement?: string };
  actionsSummary: string[];
  childWorkflow?: boolean;
  recommendedImplementation: string;
  dependencies?: string[];
  parameters?: string[];
  maps?: string[];
  riskLevel: string;
}

export interface ConversionModelConnection {
  name: string;
  type: string;
  sourceConfigs: string[];
  authenticationModel?: string;
  notes?: string;
}

export interface ConversionModelTargetApp {
  name: string;
  rationale?: string;
  workflows: ConversionModelWorkflow[];
  connections: ConversionModelConnection[];
  appSettings?: string[];
  artifacts?: { schemas?: string[]; maps?: string[]; assemblies?: string[] };
}

export interface ConversionModelTask {
  id: string;
  title: string;
  sourceArtifacts?: string[];
  targetArtifacts?: string[];
  approach?: string;
  dependsOn?: string[];
  automationLevel?: string;
  riskLevel?: string;
  acceptanceCriteria?: string[];
}

export interface ConversionModelPhase {
  phase: number;
  name: string;
  goal?: string;
  inputs?: string[];
  outputs?: string[];
  tasks: ConversionModelTask[];
}

export interface ConversionModel {
  assessmentVersion: string;
  source: {
    rootPath: string;
    applications: ConversionModelApp[];
  };
  target: {
    logicAppsStandardApps: ConversionModelTargetApp[];
  };
  executionPlan: {
    phases: ConversionModelPhase[];
  };
}

function cleanJsonOutput(output: string): string {
  let cleaned = output.trim();

  const fenceMatch = cleaned.match(/```(?:json)?\s*\n?([\s\S]*?)\n?\s*```/);
  if (fenceMatch) {
    cleaned = fenceMatch[1].trim();
  }

  if (!cleaned.startsWith('{')) {
    const startIdx = cleaned.indexOf('{');
    const endIdx = cleaned.lastIndexOf('}');
    if (startIdx !== -1 && endIdx > startIdx) {
      cleaned = cleaned.slice(startIdx, endIdx + 1);
    }
  }

  return cleaned;
}

export function validateConversionModel(output: string): ConversionModel {
  if (typeof output !== 'string' || output.trim() === '') {
    throw new Error('Output is empty or not a string');
  }

  const cleaned = cleanJsonOutput(output);

  let parsed: ConversionModel;
  try {
    parsed = JSON.parse(cleaned) as ConversionModel;
  } catch {
    throw new Error('Output is not valid JSON');
  }

  if (!parsed.assessmentVersion || typeof parsed.assessmentVersion !== 'string') {
    throw new Error('Missing required "assessmentVersion" property');
  }

  if (!parsed.source || typeof parsed.source !== 'object') {
    throw new Error('Missing required "source" property');
  }

  if (!Array.isArray(parsed.source.applications) || parsed.source.applications.length === 0) {
    throw new Error('Missing or empty "source.applications" array');
  }

  if (!parsed.target || typeof parsed.target !== 'object') {
    throw new Error('Missing required "target" property');
  }

  if (!Array.isArray(parsed.target.logicAppsStandardApps) || parsed.target.logicAppsStandardApps.length === 0) {
    throw new Error('Missing or empty "target.logicAppsStandardApps" array');
  }

  if (!parsed.executionPlan || typeof parsed.executionPlan !== 'object') {
    throw new Error('Missing required "executionPlan" property');
  }

  if (!Array.isArray(parsed.executionPlan.phases) || parsed.executionPlan.phases.length === 0) {
    throw new Error('Missing or empty "executionPlan.phases" array');
  }

  // Validate each target app has workflows
  for (const app of parsed.target.logicAppsStandardApps) {
    if (!app.name || typeof app.name !== 'string') {
      throw new Error('Target app is missing "name" property');
    }
    if (!Array.isArray(app.workflows)) {
      throw new Error(`Target app "${app.name}" is missing "workflows" array`);
    }
  }

  return parsed;
}
