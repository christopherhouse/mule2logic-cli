"""Pydantic models for grounding provider responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class GroundingResult(BaseModel):
    """A single documentation result from a grounding provider."""

    title: str
    url: str
    content: str
    source: str
    relevance_score: float = 0.0
    metadata: dict[str, Any] = {}


class GroundingResponse(BaseModel):
    """Normalized response from a grounding provider."""

    query: str
    provider: str
    results: list[GroundingResult] = []
    duration_ms: float = 0.0
    error: str | None = None
    warnings: list[str] = []
