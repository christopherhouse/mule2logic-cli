import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { buildAssessPrompt } from '../src/core/assess.js';
import type { ProjectContext } from '../src/core/project.js';

describe('buildAssessPrompt', () => {
  const context: ProjectContext = {
    rootPath: '/test/project',
    tree: ['pom.xml', 'src/main/mule/', 'src/main/mule/flow.xml'],
    files: new Map([
      ['pom.xml', '<project><artifactId>test-app</artifactId></project>'],
      ['src/main/mule/flow.xml', '<mule><flow name="test"/></mule>'],
    ]),
  };

  it('includes the project tree in the prompt', () => {
    const prompt = buildAssessPrompt(context);
    assert.ok(prompt.includes('pom.xml'));
    assert.ok(prompt.includes('src/main/mule/'));
    assert.ok(prompt.includes('src/main/mule/flow.xml'));
  });

  it('includes file contents wrapped in file tags', () => {
    const prompt = buildAssessPrompt(context);
    assert.ok(prompt.includes('<file path="pom.xml">'));
    assert.ok(prompt.includes('<artifactId>test-app</artifactId>'));
    assert.ok(prompt.includes('<file path="src/main/mule/flow.xml">'));
    assert.ok(prompt.includes('<flow name="test"/>'));
  });

  it('includes MCP server consultation instructions', () => {
    const prompt = buildAssessPrompt(context);
    assert.ok(prompt.includes('Microsoft Learn MCP'));
    assert.ok(prompt.includes('Context7 MCP'));
  });

  it('includes the JSON-only reminder', () => {
    const prompt = buildAssessPrompt(context);
    assert.ok(prompt.includes('raw JSON object'));
  });
});
