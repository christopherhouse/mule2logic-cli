import { CopilotClient, approveAll } from '@github/copilot-sdk';
import { SYSTEM_PROMPT } from './prompt.js';

export async function runCopilot(prompt) {
  const client = new CopilotClient();

  try {
    await client.start();

    const session = await client.createSession({
      onPermissionRequest: approveAll,
      systemMessage: {
        mode: 'replace',
        content: SYSTEM_PROMPT,
      },
      mcpServers: {
        learn: {
          type: 'http',
          url: 'https://learn.microsoft.com/api/mcp',
          tools: ['*'],
        },
      },
    });

    const response = await session.sendAndWait({ prompt });

    await session.disconnect();

    return response?.data?.content ?? '';
  } finally {
    await client.stop();
  }
}
