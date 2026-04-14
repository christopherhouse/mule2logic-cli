"""Error types for grounding operations."""

from __future__ import annotations


class GroundingError(Exception):
    """Base error for grounding operations."""


class GroundingTimeoutError(GroundingError):
    """Timeout when calling a grounding provider."""


class GroundingConnectionError(GroundingError):
    """Connection error when calling a grounding provider."""
