import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { validateJson, validateWorkflowStructure } from '../src/tsx/core/validate.js';

const validJson = JSON.stringify({
  definition: {
    triggers: {
      manual: { type: 'Request', kind: 'Http' }
    },
    actions: {
      Compose: { type: 'Compose', inputs: 'Hello' }
    }
  }
});

describe('validateJson', () => {
  it('parses valid Logic Apps JSON and returns the object', () => {
    const result = validateJson(validJson);
    assert.equal(result.definition.actions.Compose.type, 'Compose');
    assert.equal(result.definition.triggers.manual.kind, 'Http');
  });

  it('throws on non-JSON string', () => {
    assert.throws(() => validateJson('not json at all'), {
      message: 'Output is not valid JSON'
    });
  });

  it('throws when definition key is missing', () => {
    assert.throws(() => validateJson('{ "foo": "bar" }'), {
      message: 'Missing required "definition" property'
    });
  });

  it('throws when definition.actions is missing', () => {
    assert.throws(() => validateJson('{ "definition": {} }'), {
      message: 'Missing required "definition.actions" property'
    });
  });

  it('handles JSON wrapped in markdown code fences', () => {
    const wrapped = '```json\n' + validJson + '\n```';
    const result = validateJson(wrapped);
    assert.equal(result.definition.actions.Compose.type, 'Compose');
  });

  it('handles code fences without language tag', () => {
    const wrapped = '```\n' + validJson + '\n```';
    const result = validateJson(wrapped);
    assert.equal(result.definition.actions.Compose.inputs, 'Hello');
  });
});

describe('validateWorkflowStructure', () => {
  it('returns empty array for a valid workflow', () => {
    const parsed = JSON.parse(validJson);
    const issues = validateWorkflowStructure(parsed);
    assert.deepEqual(issues, []);
  });

  it('detects action missing type field', () => {
    const parsed = {
      definition: {
        triggers: {},
        actions: {
          BadAction: { inputs: 'test' }
        }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('BadAction') && i.includes('type')));
  });

  it('detects trigger missing type field', () => {
    const parsed = {
      definition: {
        triggers: { badTrigger: { kind: 'Http' } },
        actions: { A: { type: 'Compose' } }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('badTrigger') && i.includes('type')));
  });

  it('detects invalid runAfter references', () => {
    const parsed = {
      definition: {
        triggers: {},
        actions: {
          Step1: { type: 'Compose', inputs: 'x' },
          Step2: { type: 'Compose', inputs: 'y', runAfter: { NonExistent: ['Succeeded'] } }
        }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('NonExistent') && i.includes('runAfter')));
  });

  it('detects Condition action missing expression', () => {
    const parsed = {
      definition: {
        triggers: {},
        actions: {
          MyCondition: { type: 'If', actions: {} }
        }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('MyCondition') && i.includes('expression')));
  });

  it('detects Foreach action missing foreach input', () => {
    const parsed = {
      definition: {
        triggers: {},
        actions: {
          MyLoop: { type: 'Foreach', actions: {} }
        }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('MyLoop') && i.includes('foreach')));
  });

  it('detects Foreach action missing nested actions', () => {
    const parsed = {
      definition: {
        triggers: {},
        actions: {
          MyLoop: { type: 'Foreach', foreach: '@triggerBody()' }
        }
      }
    };
    const issues = validateWorkflowStructure(parsed as any);
    assert.ok(issues.some((i: string) => i.includes('MyLoop') && i.includes('actions')));
  });
});
