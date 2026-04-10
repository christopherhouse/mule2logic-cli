import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { discoverProject } from '../src/core/project.js';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const fixturePath = join(__dirname, 'fixtures', 'mule-project');

describe('discoverProject', () => {
  it('discovers files in a valid MuleSoft project', async () => {
    const ctx = await discoverProject(fixturePath);
    assert.equal(ctx.rootPath, fixturePath);
    assert.ok(ctx.tree.length > 0, 'Should discover at least one file');
    assert.ok(ctx.files.size > 0, 'Should read at least one file');
  });

  it('finds pom.xml at project root', async () => {
    const ctx = await discoverProject(fixturePath);
    assert.ok(ctx.files.has('pom.xml'), 'Should find pom.xml');
    assert.ok(ctx.files.get('pom.xml')!.includes('hello-mule-app'));
  });

  it('finds mule-artifact.json at project root', async () => {
    const ctx = await discoverProject(fixturePath);
    assert.ok(ctx.files.has('mule-artifact.json'), 'Should find mule-artifact.json');
  });

  it('finds Mule XML flows in src/main/mule', async () => {
    const ctx = await discoverProject(fixturePath);
    assert.ok(ctx.files.has('src/main/mule/main-flow.xml'), 'Should find main-flow.xml');
    assert.ok(ctx.files.get('src/main/mule/main-flow.xml')!.includes('hello-flow'));
  });

  it('finds application.properties in src/main/resources', async () => {
    const ctx = await discoverProject(fixturePath);
    assert.ok(
      ctx.files.has('src/main/resources/application.properties'),
      'Should find application.properties',
    );
  });

  it('returns sorted tree listing', async () => {
    const ctx = await discoverProject(fixturePath);
    const sorted = [...ctx.tree].sort();
    assert.deepEqual(ctx.tree, sorted, 'Tree should be sorted');
  });

  it('throws for non-existent path', async () => {
    await assert.rejects(
      () => discoverProject('/no/such/path'),
      { message: 'Project path not found: /no/such/path' },
    );
  });

  it('throws for a file path instead of directory', async () => {
    const filePath = join(fixturePath, 'pom.xml');
    await assert.rejects(
      () => discoverProject(filePath),
      (err: Error) => err.message.includes('not a directory'),
    );
  });

  it('throws when no MuleSoft artifacts are found', async () => {
    const { mkdtemp, rm } = await import('node:fs/promises');
    const { tmpdir } = await import('node:os');
    const emptyDir = await mkdtemp(join(tmpdir(), 'mule2logic-test-'));
    try {
      await assert.rejects(
        () => discoverProject(emptyDir),
        (err: Error) => err.message.includes('No MuleSoft artifacts found'),
      );
    } finally {
      await rm(emptyDir, { recursive: true });
    }
  });
});
