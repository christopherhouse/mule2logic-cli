import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { validateJson, validateWorkflowStructure, validateConversionModel } from '../src/core/validate.js';

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

// --- Conversion Model validation ---

const validModel = JSON.stringify({
  assessmentVersion: '1.0',
  source: {
    rootPath: '/test/project',
    applications: [{
      name: 'test-app',
      files: ['src/main/mule/flow.xml'],
      flows: [{ name: 'main-flow', file: 'flow.xml', triggerType: 'http-listener', operations: [] }],
      dependencies: [],
      transforms: [],
    }],
  },
  target: {
    logicAppsStandardApps: [{
      name: 'test-logic-app',
      workflows: [{
        name: 'MainFlow',
        sourceArtifacts: ['src/main/mule/flow.xml'],
        trigger: { type: 'Request' },
        actionsSummary: ['Compose'],
        recommendedImplementation: 'workflow',
        riskLevel: 'low',
      }],
      connections: [],
    }],
  },
  executionPlan: {
    phases: [{
      phase: 1,
      name: 'Discovery',
      tasks: [{ id: 'P1-T1', title: 'Scan files' }],
    }],
  },
});

describe('validateConversionModel', () => {
  it('parses a valid conversion model', () => {
    const result = validateConversionModel(validModel);
    assert.equal(result.assessmentVersion, '1.0');
    assert.equal(result.source.applications.length, 1);
    assert.equal(result.target.logicAppsStandardApps.length, 1);
    assert.equal(result.executionPlan.phases.length, 1);
  });

  it('throws on empty string', () => {
    assert.throws(() => validateConversionModel(''), {
      message: 'Output is empty or not a string',
    });
  });

  it('throws on non-JSON', () => {
    assert.throws(() => validateConversionModel('not json'), {
      message: 'Output is not valid JSON',
    });
  });

  it('throws when assessmentVersion is missing', () => {
    const bad = JSON.stringify({ source: {}, target: {}, executionPlan: {} });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Missing required "assessmentVersion" property',
    });
  });

  it('throws when source is missing', () => {
    const bad = JSON.stringify({ assessmentVersion: '1.0', target: {}, executionPlan: {} });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Missing required "source" property',
    });
  });

  it('throws when source.applications is empty', () => {
    const bad = JSON.stringify({
      assessmentVersion: '1.0',
      source: { applications: [] },
      target: { logicAppsStandardApps: [{ name: 'x', workflows: [] }] },
      executionPlan: { phases: [{ phase: 1, name: 'x', tasks: [] }] },
    });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Missing or empty "source.applications" array',
    });
  });

  it('throws when target.logicAppsStandardApps is missing', () => {
    const bad = JSON.stringify({
      assessmentVersion: '1.0',
      source: { applications: [{ name: 'x' }] },
      target: {},
      executionPlan: { phases: [{ phase: 1 }] },
    });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Missing or empty "target.logicAppsStandardApps" array',
    });
  });

  it('throws when executionPlan.phases is empty', () => {
    const bad = JSON.stringify({
      assessmentVersion: '1.0',
      source: { applications: [{ name: 'x' }] },
      target: { logicAppsStandardApps: [{ name: 'x', workflows: [] }] },
      executionPlan: { phases: [] },
    });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Missing or empty "executionPlan.phases" array',
    });
  });

  it('throws when a target app has no name', () => {
    const bad = JSON.stringify({
      assessmentVersion: '1.0',
      source: { applications: [{ name: 'x' }] },
      target: { logicAppsStandardApps: [{ workflows: [] }] },
      executionPlan: { phases: [{ phase: 1, name: 'x', tasks: [] }] },
    });
    assert.throws(() => validateConversionModel(bad), {
      message: 'Target app is missing "name" property',
    });
  });

  it('handles JSON wrapped in markdown code fences', () => {
    const wrapped = '```json\n' + validModel + '\n```';
    const result = validateConversionModel(wrapped);
    assert.equal(result.assessmentVersion, '1.0');
  });

  it('extracts JSON from surrounding text', () => {
    const wrapped = 'Here is the model:\n' + validModel + '\nDone.';
    const result = validateConversionModel(wrapped);
    assert.equal(result.assessmentVersion, '1.0');
  });
});
