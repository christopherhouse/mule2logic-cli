"""Agent Framework client — replaces the GHCP SDK copilot.ts module.

This module owns the ``FoundryChatClient`` + ``Agent`` lifecycle and
exposes a single ``run_agent()`` coroutine that the rest of the codebase
calls.  All Foundry / MCP wiring is encapsulated here so that swapping
to a different provider later requires changes in this file only.

Environment variables
---------------------
FOUNDRY_PROJECT_ENDPOINT
    Azure AI Foundry project endpoint URL (required).
FOUNDRY_MODEL
    Deployed model name.  Overridden by the ``model`` parameter at
    call-time.  Defaults to ``gpt-4o``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from agent_framework import ChatAgent
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential


DEFAULT_MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4o")
DEFAULT_TIMEOUT = 300.0  # seconds


async def run_agent(
    prompt: str,
    *,
    system_prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
    verbose: bool = False,
) -> str:
    """Run a single agent invocation and return the text response.

    Parameters
    ----------
    prompt
        The user-facing prompt text (conversion request, review request, etc.).
    system_prompt
        The system / instructions prompt that controls agent behaviour.
    model
        Foundry model deployment name.
    timeout
        Maximum seconds to wait for the agent to respond.
    verbose
        When ``True``, emit debug information to stderr.
    """
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
    if not endpoint:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT environment variable is required.  "
            "Set it to your Azure AI Foundry project endpoint URL."
        )

    async with AzureCliCredential() as credential:
        client = FoundryChatClient(
            project_endpoint=endpoint,
            model=model,
            credential=credential,
        )

        # Wire up the two MCP tool servers
        learn_mcp = client.get_mcp_tool(
            name="Microsoft Learn MCP",
            url="https://learn.microsoft.com/api/mcp",
            approval_mode="never_require",
        )
        context7_mcp = client.get_mcp_tool(
            name="Context7 MCP",
            url="https://mcp.context7.com/mcp",
            approval_mode="never_require",
        )

        if verbose:
            print(f"[verbose] Agent endpoint: {endpoint}", file=sys.stderr)
            print(f"[verbose] Agent model:    {model}", file=sys.stderr)

        async with ChatAgent(
            client=client,
            name="MuleSoftConverter",
            instructions=system_prompt,
            tools=[learn_mcp, context7_mcp],
        ) as agent:
            result = await asyncio.wait_for(
                agent.run(prompt),
                timeout=timeout,
            )
            return result.text if hasattr(result, "text") else str(result)
