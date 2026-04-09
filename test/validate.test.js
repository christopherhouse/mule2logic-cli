import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { validateJson } from '../src/core/validate.js';

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
