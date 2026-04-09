import { CopilotClient, approveAll } from '@github/copilot-sdk';
import { SYSTEM_PROMPT } from './prompt.js';

export const DEFAULT_MODEL = 'claude-opus-4.6';

export async function runCopilot(prompt, { verbose = false, systemPrompt = SYSTEM_PROMPT, model = DEFAULT_MODEL } = {}) {
  const client = new CopilotClient();

  try {
    await client.start();

    const session = await client.createSession({
      onPermissionRequest: approveAll,
      model,
      systemMessage: {
        mode: 'replace',
        content: systemPrompt,
      },
      mcpServers: {
        learn: {
          type: 'http',
          url: 'https://learn.microsoft.com/api/mcp',
          tools: ['*'],
        },
      },
    });

    if (verbose) {
      session.on((event) => {
        if (event.type === 'tool.execution_start') {
          const { toolName, mcpServerName, mcpToolName, arguments: args } = event.data;
          const server = mcpServerName ? ` [MCP: ${mcpServerName}/${mcpToolName}]` : '';
          console.error(`[verbose] Tool call: ${toolName}${server}`);
          if (args) {
            console.error(`[verbose]   args: ${JSON.stringify(args)}`);
          }
        } else if (event.type === 'tool.execution_complete') {
          const { toolCallId, success } = event.data;
          console.error(`[verbose] Tool complete: ${toolCallId} success=${success}`);
        }
      });
    }

    const response = await session.sendAndWait({ prompt });

    await session.disconnect();

    return response?.data?.content ?? '';
  } finally {
    await client.stop();
  }
}
