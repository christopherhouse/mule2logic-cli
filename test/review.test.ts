import { describe, it, mock, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

const VALID_WORKFLOW = {
  definition: {
    triggers: {
      manual: { type: 'Request', kind: 'Http' }
    },
    actions: {
      Compose: { type: 'Compose', inputs: 'Hello' }
    }
  }
};

const VALID_JSON = JSON.stringify(VALID_WORKFLOW);

// Mock session and client
const mockSession = {
  sendAndWait: mock.fn(async () => ({
    data: { content: VALID_JSON }
  })),
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
    CopilotClient: class {
      constructor() { return mockClient; }
    },
    approveAll: () => ({ kind: 'approved' }),
  }
});

const { reviewWorkflow } = await import('../src/core/review.js');

describe('reviewWorkflow', () => {
  beforeEach(() => {
    mockClient.start.mock.resetCalls();
    mockClient.stop.mock.resetCalls();
    mockClient.createSession.mock.resetCalls();
    mockSession.sendAndWait.mock.resetCalls();
    mockSession.disconnect.mock.resetCalls();
  });

  it('returns the reviewed workflow', async () => {
    const xml = '<flow name="test"><http:listener path="/hello"/><set-payload value="Hello"/></flow>';
    const { workflow, issues } = await reviewWorkflow(xml, VALID_WORKFLOW);
    assert.ok(workflow.definition);
    assert.ok(workflow.definition.actions);
  });

  it('uses the review system prompt, not the default', async () => {
    const xml = '<flow name="test"><set-payload value="Hello"/></flow>';
    await reviewWorkflow(xml, VALID_WORKFLOW);
    const sessionConfig = mockClient.createSession.mock.calls[0].arguments[0];
    assert.ok(sessionConfig.systemMessage.content.includes('validator'));
  });

  it('reports structural issues found after review', async () => {
    const badWorkflow = JSON.stringify({
      definition: {
        triggers: {},
        actions: { Bad: { inputs: 'x' } }
      }
    });
    mockSession.sendAndWait.mock.mockImplementationOnce(async () => ({
      data: { content: badWorkflow }
    }));

    const xml = '<flow name="test"><set-payload value="x"/></flow>';
    const { issues } = await reviewWorkflow(xml, VALID_WORKFLOW);
    assert.ok(issues.length > 0);
  });

  it('sends the original XML and workflow JSON in the prompt', async () => {
    const xml = '<flow name="myFlow"><set-payload value="Test"/></flow>';
    await reviewWorkflow(xml, VALID_WORKFLOW);
    const prompt = mockSession.sendAndWait.mock.calls[0].arguments[0].prompt;
    assert.ok(prompt.includes('myFlow'));
    assert.ok(prompt.includes('Compose'));
  });
});
