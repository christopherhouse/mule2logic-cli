"""RepairAdvisorAgent — suggests fixes for migration gaps and failures.

This agent is deterministic: it maps known validation rule IDs and
migration gap categories to predefined repair strategies. No LLM
calls are made.

Future extensions may add LLM-backed suggestions for complex or
novel issues via the ``tools`` list on :class:`BaseAgent`.
"""

from __future__ import annotations

import time

from m2la_contracts.enums import GapCategory, Severity
from m2la_contracts.validate import ValidationIssue, ValidationReport
from pydantic import BaseModel, Field

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus


class RepairSuggestion(BaseModel):
    """A single repair suggestion for a validation issue or migration gap."""

    issue_ref: str = Field(..., description="Reference to the issue (rule_id or gap construct name)")
    suggestion: str = Field(..., description="Human-readable repair suggestion")
    confidence: str = Field(default="medium", description="Confidence level: high | medium | low")
    auto_fixable: bool = Field(default=False, description="Whether this can be automatically fixed")


# ---------------------------------------------------------------------------
# Known repair strategies keyed by rule_id prefix or gap category
# ---------------------------------------------------------------------------

_RULE_REPAIRS: dict[str, tuple[str, str, bool]] = {
    # (suggestion, confidence, auto_fixable)
    "MULE_": (
        "Review the MuleSoft input for structural issues; ensure valid XML and proper namespaces.",
        "high",
        False,
    ),
    "IR_": ("Check IR construction — ensure all flows have valid triggers and steps.", "medium", False),
    "OUT_": ("Verify generated workflow.json schema and action references.", "medium", False),
}

_GAP_REPAIRS: dict[GapCategory, tuple[str, str, bool]] = {
    GapCategory.UNSUPPORTED_CONSTRUCT: (
        "This construct has no Logic Apps equivalent. Consider implementing as a custom Azure Function.",
        "high",
        False,
    ),
    GapCategory.UNRESOLVABLE_REFERENCE: (
        "The referenced element could not be resolved. Ensure all config-refs and flow-refs are defined.",
        "high",
        False,
    ),
    GapCategory.PARTIAL_SUPPORT: (
        "This construct is partially supported. Review the generated output and add manual adjustments.",
        "medium",
        False,
    ),
    GapCategory.CONNECTOR_MISMATCH: (
        "The connector mapping may not be exact. Verify authentication and connection settings.",
        "medium",
        False,
    ),
    GapCategory.DATAWEAVE_COMPLEXITY: (
        "Complex DataWeave expressions require manual conversion. Consider using Liquid templates or inline code.",
        "low",
        False,
    ),
}


class RepairAdvisorAgent(BaseAgent):
    """Suggests fixes for validation issues and migration gaps.

    This agent examines the validation report and migration gaps
    from prior pipeline steps and produces structured repair
    suggestions. All logic is deterministic — no LLM calls.

    The agent deposits the following keys into ``context.accumulated_data``:

    - ``"repair_suggestions"`` — list of :class:`RepairSuggestion`.
    """

    def __init__(self) -> None:
        super().__init__(name="RepairAdvisorAgent")

    def execute(self, context: AgentContext) -> AgentResult:
        """Analyze issues and produce repair suggestions.

        Reads from ``context.accumulated_data``:
        - ``"output_validation"`` — :class:`ValidationReport` (optional)
        - ``"migration_gaps"``    — list of :class:`MigrationGap` (optional)

        Args:
            context: Pipeline context with accumulated results.

        Returns:
            AgentResult with repair suggestions as output.
        """
        start = time.monotonic()
        warnings: list[str] = []
        suggestions: list[RepairSuggestion] = []

        try:
            # 1. Process validation issues
            report: ValidationReport | None = context.accumulated_data.get("output_validation")
            if report is not None:
                for issue in report.issues:
                    suggestion = self._suggest_for_issue(issue)
                    if suggestion is not None:
                        suggestions.append(suggestion)

            # Also check input validation
            input_report: ValidationReport | None = context.accumulated_data.get("input_validation")
            if input_report is not None:
                for issue in input_report.issues:
                    if issue.severity in (Severity.ERROR, Severity.CRITICAL):
                        suggestion = self._suggest_for_issue(issue)
                        if suggestion is not None:
                            suggestions.append(suggestion)

            # 2. Process migration gaps
            gaps = context.accumulated_data.get("migration_gaps", [])
            for gap in gaps:
                suggestion = self._suggest_for_gap(gap)
                if suggestion is not None:
                    suggestions.append(suggestion)

            context.accumulated_data["repair_suggestions"] = suggestions

            # 3. Build reasoning summary
            if not suggestions:
                summary = "No repairs needed — all validations passed with no gaps"
                status = AgentStatus.SUCCESS
            else:
                auto_count = sum(1 for s in suggestions if s.auto_fixable)
                summary = f"Produced {len(suggestions)} repair suggestion(s) ({auto_count} auto-fixable)"
                status = AgentStatus.SUCCESS

            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=status,
                output=suggestions,
                reasoning_summary=summary,
                duration_ms=elapsed_ms,
                warnings=warnings,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILURE,
                reasoning_summary=f"Repair analysis failed: {exc}",
                duration_ms=elapsed_ms,
                warnings=warnings,
                error_message=str(exc),
            )

    def _suggest_for_issue(self, issue: ValidationIssue) -> RepairSuggestion | None:
        """Map a validation issue to a repair suggestion using rule_id prefix matching."""
        for prefix, (suggestion_text, confidence, auto_fixable) in _RULE_REPAIRS.items():
            if issue.rule_id.startswith(prefix):
                return RepairSuggestion(
                    issue_ref=issue.rule_id,
                    suggestion=issue.remediation_hint or suggestion_text,
                    confidence=confidence,
                    auto_fixable=auto_fixable,
                )

        # Fallback for unknown rules
        if issue.severity in (Severity.ERROR, Severity.CRITICAL):
            return RepairSuggestion(
                issue_ref=issue.rule_id,
                suggestion=issue.remediation_hint or f"Review issue: {issue.message}",
                confidence="low",
                auto_fixable=False,
            )

        return None

    @staticmethod
    def _suggest_for_gap(gap: object) -> RepairSuggestion | None:
        """Map a migration gap to a repair suggestion using its category."""
        # MigrationGap from contracts
        if not hasattr(gap, "category") or not hasattr(gap, "construct_name"):
            return None

        category = gap.category  # type: ignore[union-attr]
        construct_name = gap.construct_name  # type: ignore[union-attr]

        repair = _GAP_REPAIRS.get(category)
        if repair is not None:
            suggestion_text, confidence, auto_fixable = repair
            return RepairSuggestion(
                issue_ref=construct_name,
                suggestion=suggestion_text,
                confidence=confidence,
                auto_fixable=auto_fixable,
            )

        return RepairSuggestion(
            issue_ref=construct_name,
            suggestion=f"Migration gap for '{construct_name}': review and apply manual fix.",
            confidence="low",
            auto_fixable=False,
        )
