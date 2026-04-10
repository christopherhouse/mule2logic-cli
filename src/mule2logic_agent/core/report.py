"""Report agent — generates a migration-analysis Markdown report."""

from __future__ import annotations

import json

from mule2logic_agent.core.agent import run_agent
from mule2logic_agent.core.prompt import REPORT_SYSTEM_PROMPT, build_report_prompt
from mule2logic_agent.models import WorkflowDefinition


async def generate_report(
    xml: str,
    workflow_json: WorkflowDefinition,
    *,
    verbose: bool = False,
    model: str | None = None,
    timeout: float | None = None,
) -> str:
    """Generate a migration-analysis Markdown report.

    Returns the report as a Markdown string.
    """
    from mule2logic_agent.core.agent import DEFAULT_MODEL, DEFAULT_TIMEOUT

    model = model or DEFAULT_MODEL
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

    prompt = build_report_prompt(xml, json.dumps(workflow_json, indent=2))

    response = await run_agent(
        prompt,
        system_prompt=REPORT_SYSTEM_PROMPT,
        model=model,
        timeout=timeout,
        verbose=verbose,
    )

    return response
