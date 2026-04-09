import { describe, it, mock, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

const MOCK_JSON = JSON.stringify({
  definition: {
    triggers: {
      manual: { type: 'Request', kind: 'Http' }
    },
    actions: {
      Compose: { type: 'Compose', inputs: 'Hello' }
    }
  }
});

// Mock session and client objects
const mockSession = {
  sendAndWait: mock.fn(async () => ({
    data: { content: MOCK_JSON }
  })),
  disconnect: mock.fn(async () => {}),
};

const mockClient = {
  start: mock.fn(async () => {}),
  stop: mock.fn(async () => []),
  createSession: mock.fn(async () => mockSession),
};

// Mock the SDK module before importing copilot.js
mock.module('@github/copilot-sdk', {
  namedExports: {
    CopilotClient: class {
      constructor() { return mockClient; }
    },
    approveAll: () => ({ kind: 'approved' }),
  }
});

const { runCopilot } = await import('../src/core/copilot.js');

describe('runCopilot', () => {
  beforeEach(() => {
    mockClient.start.mock.resetCalls();
    mockClient.stop.mock.resetCalls();
    mockClient.createSession.mock.resetCalls();
    mockSession.sendAndWait.mock.resetCalls();
    mockSession.disconnect.mock.resetCalls();
  });

  it('returns the assistant response content', async () => {
    const result = await runCopilot('Convert MuleSoft XML to Logic Apps JSON');
    assert.equal(result, MOCK_JSON);
  });

  it('starts and stops the client', async () => {
    await runCopilot('test prompt');
    assert.equal(mockClient.start.mock.callCount(), 1);
    assert.equal(mockClient.stop.mock.callCount(), 1);
  });

  it('creates a session with system message and permission handler', async () => {
    await runCopilot('test prompt');
    assert.equal(mockClient.createSession.mock.callCount(), 1);
    const config = mockClient.createSession.mock.calls[0].arguments[0];
    assert.equal(config.systemMessage.mode, 'replace');
    assert.ok(config.systemMessage.content.includes('Azure'));
    assert.ok(typeof config.onPermissionRequest === 'function');
  });

  it('configures the Microsoft Learn MCP server', async () => {
    await runCopilot('test prompt');
    const config = mockClient.createSession.mock.calls[0].arguments[0];
    assert.ok(config.mcpServers?.learn, 'Should have a learn MCP server');
    assert.equal(config.mcpServers.learn.type, 'http');
    assert.equal(config.mcpServers.learn.url, 'https://learn.microsoft.com/api/mcp');
    assert.deepEqual(config.mcpServers.learn.tools, ['*']);
  });

  it('sends the prompt via sendAndWait', async () => {
    const prompt = 'Convert this XML please';
    await runCopilot(prompt);
    assert.equal(mockSession.sendAndWait.mock.callCount(), 1);
    assert.deepEqual(mockSession.sendAndWait.mock.calls[0].arguments[0], { prompt });
  });

  it('disconnects the session after getting a response', async () => {
    await runCopilot('test');
    assert.equal(mockSession.disconnect.mock.callCount(), 1);
  });

  it('returns empty string when response is undefined', async () => {
    mockSession.sendAndWait.mock.mockImplementation(async () => undefined);
    const result = await runCopilot('test');
    assert.equal(result, '');
    // restore
    mockSession.sendAndWait.mock.mockImplementation(async () => ({
      data: { content: MOCK_JSON }
    }));
  });

  it('stops the client even if session throws', async () => {
    mockClient.createSession.mock.mockImplementation(async () => {
      throw new Error('session failed');
    });
    await assert.rejects(() => runCopilot('test'), { message: 'session failed' });
    assert.equal(mockClient.stop.mock.callCount(), 1);
    // restore
    mockClient.createSession.mock.mockImplementation(async () => mockSession);
  });
});
