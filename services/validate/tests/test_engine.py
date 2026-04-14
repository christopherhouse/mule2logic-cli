"""Tests for the validation engine orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from m2la_contracts.enums import InputMode, Severity
from m2la_ir.enums import FlowKind, ProcessorType, TriggerType
from m2la_ir.models import Flow, IRMetadata, MuleIR, Processor, ProjectMetadata, Trigger

from m2la_validate.engine import validate_all, validate_ir, validate_mule_input, validate_output

WORKFLOW_SCHEMA = (
    "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
)


def _valid_workflow() -> dict[str, Any]:
    """Return a minimal valid workflow JSON."""
    return {
        "definition": {
            "$schema": WORKFLOW_SCHEMA,
            "contentVersion": "1.0.0.0",
            "triggers": {},
            "actions": {},
            "outputs": {},
        },
        "kind": "Stateful",
    }


def _valid_ir(mode: InputMode = InputMode.PROJECT) -> MuleIR:
    """Return a valid IR."""
    return MuleIR(
        ir_metadata=IRMetadata(source_mode=mode, source_path="/test"),
        project_metadata=ProjectMetadata(),
        flows=[
            Flow(
                kind=FlowKind.FLOW,
                name="testFlow",
                trigger=Trigger(type=TriggerType.HTTP_LISTENER),
                steps=[Processor(type=ProcessorType.SET_PAYLOAD, config={"value": "hi"})],
            ),
        ],
    )


def _create_valid_project_dir(root: Path) -> None:
    """Create valid Mule project input."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "pom.xml").write_text("<project/>")
    mule_dir = root / "src" / "main" / "mule"
    mule_dir.mkdir(parents=True)
    (mule_dir / "flow.xml").write_text(
        '<?xml version="1.0"?>\n'
        '<mule xmlns="http://www.mulesoft.org/schema/mule/core">'
        '<flow name="test"><set-payload value="hi"/></flow></mule>'
    )


def _create_valid_output_dir(root: Path) -> None:
    """Create valid Logic Apps output."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "host.json").write_text(
        json.dumps(
            {
                "version": "2.0",
                "extensionBundle": {
                    "id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
                    "version": "[1.*, 2.0.0)",
                },
            }
        )
    )
    (root / "connections.json").write_text(json.dumps({"managedApiConnections": {}, "serviceProviderConnections": {}}))
    (root / "parameters.json").write_text(json.dumps({}))
    (root / ".env").write_text(
        "WORKFLOWS_SUBSCRIPTION_ID=x\nWORKFLOWS_RESOURCE_GROUP=x\nWORKFLOWS_MANAGED_IDENTITY_CLIENT_ID=x\n"
    )
    wf_dir = root / "workflows" / "test"
    wf_dir.mkdir(parents=True)
    (wf_dir / "workflow.json").write_text(json.dumps(_valid_workflow()))


# ── Engine entry point tests ─────────────────────────────────────────────────


class TestValidateMuleInput:
    """Tests for engine.validate_mule_input."""

    def test_valid_project_returns_valid_report(self, tmp_path: Path) -> None:
        _create_valid_project_dir(tmp_path)
        report = validate_mule_input(tmp_path, InputMode.PROJECT)
        assert report.valid is True
        assert report.issues == []
        assert report.artifacts_validated >= 1

    def test_invalid_project_returns_invalid_report(self, tmp_path: Path) -> None:
        report = validate_mule_input(tmp_path, InputMode.PROJECT)
        assert report.valid is False
        assert len(report.issues) > 0

    def test_single_flow_valid(self, tmp_path: Path) -> None:
        xml = tmp_path / "flow.xml"
        xml.write_text(
            '<?xml version="1.0"?>\n'
            '<mule xmlns="http://www.mulesoft.org/schema/mule/core">'
            '<flow name="f"><set-payload value="x"/></flow></mule>'
        )
        report = validate_mule_input(xml, InputMode.SINGLE_FLOW)
        assert report.valid is True


class TestValidateIR:
    """Tests for engine.validate_ir."""

    def test_valid_ir(self) -> None:
        report = validate_ir(_valid_ir())
        assert report.valid is True

    def test_invalid_ir(self) -> None:
        ir = MuleIR(
            ir_metadata=IRMetadata(source_mode=InputMode.PROJECT, source_path="/test"),
            flows=[
                Flow(
                    kind=FlowKind.FLOW,
                    name="noTrigger",
                    steps=[
                        Processor(
                            type=ProcessorType.FLOW_REF,
                            name="missing",
                            config={"name": "missing"},
                        )
                    ],
                ),
            ],
        )
        report = validate_ir(ir)
        assert report.valid is False
        assert len(report.issues) > 0


class TestValidateOutput:
    """Tests for engine.validate_output."""

    def test_valid_project_output(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        _create_valid_output_dir(output_dir)
        report = validate_output(output_dir, InputMode.PROJECT)
        errors = [i for i in report.issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_valid_single_flow_output(self) -> None:
        report = validate_output(_valid_workflow(), InputMode.SINGLE_FLOW)
        assert report.valid is True

    def test_invalid_project_output(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        report = validate_output(output_dir, InputMode.PROJECT)
        assert report.valid is False


# ── validate_all combined tests ──────────────────────────────────────────────


class TestValidateAll:
    """Tests for the combined validate_all function."""

    def test_all_stages_valid(self, tmp_path: Path) -> None:
        """All stages valid should return valid report."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        _create_valid_project_dir(input_dir)
        _create_valid_output_dir(output_dir)
        report = validate_all(
            input_path=input_dir,
            mode=InputMode.PROJECT,
            ir=_valid_ir(),
            output=output_dir,
        )
        assert report.valid is True

    def test_partial_validation(self) -> None:
        """Running only IR validation should work."""
        report = validate_all(mode=InputMode.PROJECT, ir=_valid_ir())
        assert report.valid is True

    def test_combined_issues_aggregated(self, tmp_path: Path) -> None:
        """Issues from all stages should be aggregated."""
        ir = MuleIR(
            ir_metadata=IRMetadata(source_mode=InputMode.PROJECT, source_path="/test"),
            flows=[Flow(kind=FlowKind.FLOW, name="empty")],
        )
        report = validate_all(
            input_path=tmp_path,  # empty dir → project input errors
            mode=InputMode.PROJECT,
            ir=ir,  # empty flow → IR warnings
            output=tmp_path,  # no output files → output errors
        )
        assert report.valid is False
        assert len(report.issues) > 0
        # Should have issues from multiple categories
        categories = {i.category for i in report.issues}
        assert len(categories) >= 2

    def test_report_has_no_telemetry_by_default(self) -> None:
        """Reports from the engine should have telemetry=None by default."""
        report = validate_all(mode=InputMode.PROJECT, ir=_valid_ir())
        assert report.telemetry is None

    def test_single_flow_mode_combined(self, tmp_path: Path) -> None:
        """Single-flow mode combined validation."""
        xml = tmp_path / "flow.xml"
        xml.write_text(
            '<?xml version="1.0"?>\n'
            '<mule xmlns="http://www.mulesoft.org/schema/mule/core">'
            '<flow name="f"><set-payload value="x"/></flow></mule>'
        )
        ir = _valid_ir(InputMode.SINGLE_FLOW)
        report = validate_all(
            input_path=xml,
            mode=InputMode.SINGLE_FLOW,
            ir=ir,
            output=_valid_workflow(),
        )
        assert report.valid is True
