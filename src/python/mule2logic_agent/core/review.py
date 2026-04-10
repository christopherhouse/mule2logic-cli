"""QC review agent — validates and optionally corrects a converted workflow."""

from __future__ import annotations

import json
import sys

from mule2logic_agent.core.agent import run_agent
from mule2logic_agent.core.prompt import REVIEW_PROMPT
from mule2logic_agent.core.validate import validate_json, validate_workflow_structure
from mule2logic_agent.models import WorkflowDefinition


async def review_workflow(
    xml: str,
    parsed: WorkflowDefinition,
    *,
    verbose: bool = False,
    model: str | None = None,
    timeout: float | None = None,
) -> tuple[WorkflowDefinition, list[str]]:
    """Run the review agent on an already-converted workflow.

    Returns ``(reviewed_workflow, remaining_issues)``.
    """
    from mule2logic_agent.core.agent import DEFAULT_MODEL, DEFAULT_TIMEOUT

    model = model or DEFAULT_MODEL
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

    structural_issues = validate_workflow_structure(parsed)

    if verbose:
        if structural_issues:
            print("[review] Structural issues found:", file=sys.stderr)
            for issue in structural_issues:
                print(f"[review]   - {issue}", file=sys.stderr)
        else:
            print(
                "[review] Structural validation passed, running AI review...",
                file=sys.stderr,
            )

    review_prompt = _build_review_prompt(xml, parsed, structural_issues)

    response = await run_agent(
        review_prompt,
        system_prompt=REVIEW_PROMPT,
        model=model,
        timeout=timeout,
        verbose=verbose,
    )

    reviewed = validate_json(response)
    post_review_issues = validate_workflow_structure(reviewed)

    if verbose and post_review_issues:
        print("[review] Post-review issues remain:", file=sys.stderr)
        for issue in post_review_issues:
            print(f"[review]   - {issue}", file=sys.stderr)

    return reviewed, post_review_issues


def _build_review_prompt(
    xml: str,
    parsed: WorkflowDefinition,
    issues: list[str],
) -> str:
    prompt = (
        "Review and validate this Azure Logic Apps workflow that was "
        "converted from MuleSoft XML.\n\n"
        "<original-mulesoft-xml>\n"
        f"{xml}\n"
        "</original-mulesoft-xml>\n\n"
        "<converted-workflow-json>\n"
        f"{json.dumps(parsed, indent=2)}\n"
        "</converted-workflow-json>"
    )

    if issues:
        issue_text = "\n".join(f"- {i}" for i in issues)
        prompt += (
            "\n\n<structural-issues-detected>\n"
            f"{issue_text}\n"
            "</structural-issues-detected>\n\n"
            "Fix the structural issues listed above and return the "
            "corrected workflow JSON."
        )
    else:
        prompt += (
            "\n\nVerify this workflow is correct and complete. If it is "
            "valid, return it as-is. If you find any issues, return the "
            "corrected version."
        )

    prompt += (
        "\n\nRespond with ONLY the raw JSON object. No markdown, no "
        "code fences, no explanation."
    )

    return prompt
