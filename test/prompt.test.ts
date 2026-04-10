import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { SYSTEM_PROMPT, buildPrompt } from '../src/tsx/core/prompt.js';

describe('SYSTEM_PROMPT', () => {
  it('is a non-empty string', () => {
    assert.equal(typeof SYSTEM_PROMPT, 'string');
    assert.ok(SYSTEM_PROMPT.length > 0);
  });

  it('contains key phrase "Azure"', () => {
    assert.ok(SYSTEM_PROMPT.includes('Azure'));
  });

  it('contains key phrase "JSON"', () => {
    assert.ok(SYSTEM_PROMPT.includes('JSON'));
  });
});

describe('buildPrompt', () => {
  const xml = '<flow name="test"><http:listener path="/hello"/></flow>';

  it('includes the provided XML in the returned string', () => {
    const result = buildPrompt(xml);
    assert.ok(result.includes(xml));
  });

  it('includes an instruction to return only JSON', () => {
    const result = buildPrompt(xml);
    assert.ok(result.includes('ONLY') && result.includes('JSON'));
  });
});
