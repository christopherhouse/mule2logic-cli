"""Lazy-loaded system prompts for each migration agent.

Prompts are externalized as Markdown files in the ``prompts/`` directory
adjacent to this module.  Each prompt is loaded **once** on first access
and cached for the lifetime of the process.
"""

from __future__ import annotations

import functools
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@functools.cache
def _load(name: str) -> str:
    """Read and cache a prompt markdown file."""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()


def load_prompt(name: str) -> str:
    """Load a prompt by name (without ``.md`` extension).

    >>> load_prompt("analyzer")  # reads prompts/analyzer.md
    """
    return _load(name)


# Convenience accessors — each reads its ``.md`` file once.

def orchestrator_prompt() -> str:
    return _load("orchestrator")


def analyzer_prompt() -> str:
    return _load("analyzer")


def planner_prompt() -> str:
    return _load("planner")


def transformer_prompt() -> str:
    return _load("transformer")


def validator_prompt() -> str:
    return _load("validator")


def repair_advisor_prompt() -> str:
    return _load("repair_advisor")

