import { describe, it, mock, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const VALID_RESPONSE = JSON.stringify({
  definition: {
    triggers: {
      manual: { type: 'Request', kind: 'Http', inputs: { method: 'GET', relativePath: '/hello' } }
    },
    actions: {
      Compose: { type: 'Compose', inputs: 'Hello', runAfter: {} }
    }
  }
});

const mockSession = {
  sendAndWait: mock.fn(async () => ({ data: { content: VALID_RESPONSE } })),
  disconnect: mock.fn(async () => {}),
  on: mock.fn(),
};

const mockClient = {
  start: mock.fn(async () => {}),
  stop: mock.fn(async () => []),
  createSession: mock.fn(async () => mockSession),
};

mock.module('@github/copilot-sdk', {
  namedExports: {
    CopilotClient: class { constructor() { return mockClient; } },
    approveAll: () => ({ kind: 'approved' }),
  }
});

const { convertCommand } = await import('../src/tsx/commands/convert.js');

// Capture stdout and stderr
function captureOutput() {
  const logged: string[] = [];
  const errors: string[] = [];
  const origLog = console.log;
  const origErr = console.error;
  console.log = (...args: unknown[]) => logged.push(args.map(String).join(' '));
  console.error = (...args: unknown[]) => errors.push(args.map(String).join(' '));
  return {
    logged,
    errors,
    restore() {
      console.log = origLog;
      console.error = origErr;
    }
  };
}

describe('convertCommand', () => {
  beforeEach(() => {
    mockClient.start.mock.resetCalls();
    mockClient.stop.mock.resetCalls();
    mockClient.createSession.mock.resetCalls();
    mockSession.sendAndWait.mock.resetCalls();
    mockSession.disconnect.mock.resetCalls();
    mockSession.on.mock.resetCalls();
    // Restore default mock behavior
    mockSession.sendAndWait.mock.mockImplementation(
      async () => ({ data: { content: VALID_RESPONSE } })
    );
  });

  it('converts a fixture file and outputs valid JSON to stdout', async () => {
    const out = captureOutput();
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, {});
      assert.equal(out.logged.length, 1);
      const parsed = JSON.parse(out.logged[0]);
      assert.ok(parsed.definition);
      assert.ok(parsed.definition.triggers);
      assert.ok(parsed.definition.actions);
    } finally {
      out.restore();
    }
  });

  it('pretty-prints JSON when --pretty is set', async () => {
    const out = captureOutput();
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, { pretty: true });
      const jsonStr = out.logged[0];
      assert.ok(jsonStr.includes('\n'), 'Pretty output should contain newlines');
      const parsed = JSON.parse(jsonStr);
      assert.ok(parsed.definition);
    } finally {
      out.restore();
    }
  });

  it('wraps output with explanation when --explain is set', async () => {
    const out = captureOutput();
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, { explain: true });
      const parsed = JSON.parse(out.logged[0]);
      assert.ok(parsed.workflow, 'Should have workflow property');
      assert.ok(parsed.explanation, 'Should have explanation property');
      assert.ok(parsed.workflow.definition);
    } finally {
      out.restore();
    }
  });

  it('writes to file when --output is set', async () => {
    const { unlink, readFile } = await import('node:fs/promises');
    const outPath = join(__dirname, 'fixtures', '_test_output.json');
    try {
      await convertCommand(join(__dirname, 'fixtures', 'simple-flow.xml'), { output: outPath });
      const content = await readFile(outPath, 'utf-8');
      const parsed = JSON.parse(content);
      assert.ok(parsed.definition);
    } finally {
      try { await unlink(outPath); } catch {}
    }
  });

  it('logs verbose output to stderr when --verbose is set', async () => {
    const out = captureOutput();
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, { verbose: true });
      const verboseOutput = out.errors.join('\n');
      assert.ok(verboseOutput.includes('[verbose]'), 'Should have verbose debug output');
    } finally {
      out.restore();
    }
  });

  it('retries once on invalid JSON then succeeds', async () => {
    let callCount = 0;
    mockSession.sendAndWait.mock.mockImplementation(async () => {
      callCount++;
      if (callCount === 1) {
        return { data: { content: 'not valid json' } };
      }
      return { data: { content: VALID_RESPONSE } };
    });

    const out = captureOutput();
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, {});
      assert.ok(callCount >= 2, 'Should have called Copilot at least twice (retry + review)');
      const parsed = JSON.parse(out.logged[0]);
      assert.ok(parsed.definition);
    } finally {
      out.restore();
    }
  });

  it('exits with code 1 when file is missing', async () => {
    const out = captureOutput();
    const origExit = process.exit;
    let exitCode: number | undefined;
    process.exit = ((code: number) => { exitCode = code; throw new Error('EXIT'); }) as never;
    try {
      await convertCommand('/no/such/file.xml', {});
    } catch (e) {
      if ((e as Error).message !== 'EXIT') throw e;
    } finally {
      process.exit = origExit;
      out.restore();
    }
    assert.equal(exitCode, 1);
    assert.ok(out.errors.some((e: string) => e.includes('File not found')));
  });

  it('exits with code 1 after retry fails with invalid JSON', async () => {
    mockSession.sendAndWait.mock.mockImplementation(
      async () => ({ data: { content: 'bad json' } })
    );

    const out = captureOutput();
    const origExit = process.exit;
    let exitCode: number | undefined;
    process.exit = ((code: number) => { exitCode = code; throw new Error('EXIT'); }) as never;
    try {
      const fixturePath = join(__dirname, 'fixtures', 'simple-flow.xml');
      await convertCommand(fixturePath, {});
    } catch (e) {
      if ((e as Error).message !== 'EXIT') throw e;
    } finally {
      process.exit = origExit;
      out.restore();
    }
    assert.equal(exitCode, 1);
    assert.ok(out.errors.some((e: string) => e.includes('Invalid JSON output after retry')));
  });
});
