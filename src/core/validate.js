export function validateJson(output) {
  if (typeof output !== 'string' || output.trim() === '') {
    throw new Error('Output is empty or not a string');
  }

  let cleaned = output.trim();

  // Strip markdown code fences if present
  const fenceMatch = cleaned.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?\s*```$/);
  if (fenceMatch) {
    cleaned = fenceMatch[1].trim();
  }

  let parsed;
  try {
    parsed = JSON.parse(cleaned);
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
export function validateWorkflowStructure(parsed) {
  const issues = [];
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
