import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readInput } from '../src/tsx/core/io.js';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

describe('readInput', () => {
  it('reads a valid file and returns its contents', async () => {
    const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
    const content = await readInput(fixturePath);
    assert.ok(content.includes('<flow name="test">'));
    assert.ok(content.includes('<http:listener path="/hello"/>'));
    assert.ok(content.includes('<set-payload value="Hello"/>'));
  });

  it('throws an error for a non-existent file', async () => {
    await assert.rejects(
      () => readInput('/no/such/file.xml'),
      { message: 'File not found: /no/such/file.xml' }
    );
  });

  it('throws an error for empty input', async () => {
    const emptyFixture = join(__dirname, 'fixtures', 'empty.xml');
    const { writeFile, unlink } = await import('node:fs/promises');
    await writeFile(emptyFixture, '   ');
    try {
      await assert.rejects(
        () => readInput(emptyFixture),
        { message: 'Input is empty' }
      );
    } finally {
      await unlink(emptyFixture);
    }
  });
});
