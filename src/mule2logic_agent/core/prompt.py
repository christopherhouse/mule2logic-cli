"""Prompt builder — loads markdown templates and injects XML."""

from __future__ import annotations

from importlib import resources as pkg_resources


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the ``prompts`` package-data directory."""
    ref = pkg_resources.files("mule2logic_agent") / "prompts" / filename
    return ref.read_text(encoding="utf-8").strip()


# Eagerly-loaded prompt constants
SYSTEM_PROMPT: str = _load_prompt("system.prompt.md")
REVIEW_PROMPT: str = _load_prompt("review.prompt.md")
REPORT_SYSTEM_PROMPT: str = _load_prompt("report.prompt.md")

_user_template: str = _load_prompt("user.prompt.md")
_report_user_template: str = _load_prompt("report.user.prompt.md")


def build_prompt(xml: str) -> str:
    """Build the user prompt for the conversion agent."""
    return _user_template.replace("{{xml}}", xml)


def build_report_prompt(xml: str, workflow_json: str) -> str:
    """Build the user prompt for the report agent."""
    return (
        _report_user_template
        .replace("{{xml}}", xml)
        .replace("{{workflowJson}}", workflow_json)
    )
