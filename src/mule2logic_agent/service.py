"""High-level conversion service — the public API of the agent package.

This module is the primary entry-point that the CLI (or a future REST API /
container app) calls.  It orchestrates the full pipeline:

  1. Build prompt
  2. Call conversion agent
  3. Validate JSON
  4. (optional) QC review agent
  5. (optional) Migration report agent
"""

from __future__ import annotations

import json

from mule2logic_agent.core.agent import DEFAULT_MODEL, DEFAULT_TIMEOUT, run_agent
from mule2logic_agent.core.prompt import SYSTEM_PROMPT, build_prompt
from mule2logic_agent.core.report import generate_report
from mule2logic_agent.core.review import review_workflow
from mule2logic_agent.core.validate import validate_json, validate_workflow_structure
from mule2logic_agent.models import ConvertRequest, ConvertResult, WorkflowDefinition


async def convert(request: ConvertRequest) -> ConvertResult:
    """Execute the full MuleSoft → Logic Apps conversion pipeline.

    This is the **only** function that external consumers need to call.
    It encapsulates every step and returns a single ``ConvertResult``.
    """
    model = request.model or DEFAULT_MODEL
    timeout = request.timeout or DEFAULT_TIMEOUT
    verbose = request.verbose

    # 1. Build prompt
    prompt = build_prompt(request.xml)

    # 2. Call conversion agent
    raw_response = await run_agent(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        model=model,
        timeout=timeout,
        verbose=verbose,
    )

    # 3. Validate JSON (retry once on failure)
    try:
        parsed = validate_json(raw_response)
    except ValueError:
        raw_response = await run_agent(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            model=model,
            timeout=timeout,
            verbose=verbose,
        )
        parsed = validate_json(raw_response)  # raises on second failure

    # 4. QC review agent (optional)
    review_issues: list[str] = []
    if not request.skip_review:
        try:
            parsed, review_issues = await review_workflow(
                request.xml,
                parsed,
                verbose=verbose,
                model=model,
                timeout=timeout,
            )
        except Exception:
            # Review failure is non-fatal; keep original output
            review_issues = validate_workflow_structure(parsed)

    # 5. Explanation (optional)
    explanation = ""
    if request.include_explanation:
        try:
            explain_prompt = (
                "You are a MuleSoft-to-Azure migration expert.\n\n"
                "Given the original MuleSoft XML and the converted Logic Apps JSON below, "
                "provide a clear, concise explanation of the conversion.  Describe what each "
                "MuleSoft element was mapped to, any assumptions made, and anything the user "
                "should review or adjust.\n\n"
                "## MuleSoft XML\n```xml\n" + request.xml + "\n```\n\n"
                "## Logic Apps JSON\n```json\n" + json.dumps(parsed, indent=2) + "\n```\n\n"
                "Respond with the explanation text only — no JSON, no code fences."
            )
            explanation = await run_agent(
                explain_prompt,
                system_prompt="You are a helpful migration assistant.  "
                "Respond with plain text only.",
                model=model,
                timeout=timeout,
                verbose=verbose,
            )
        except Exception:
            explanation = ""

    # 6. Migration report (optional)
    report = ""
    if request.generate_report:
        try:
            report = await generate_report(
                request.xml,
                parsed,
                verbose=verbose,
                model=model,
                timeout=timeout,
            )
        except Exception:
            report = ""

    return ConvertResult(
        workflow=parsed,
        raw_response=raw_response,
        explanation=explanation,
        review_issues=review_issues,
        report=report,
    )
