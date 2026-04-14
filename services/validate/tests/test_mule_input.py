"""Tests for Mule input validation rules."""

from __future__ import annotations

from pathlib import Path

from m2la_contracts.enums import InputMode, Severity

from m2la_validate.rules.mule_input import (
    validate_mule_input,
    validate_project_input,
    validate_single_flow_input,
)

# ── Project mode tests ────────────────────────────────────────────────────────


class TestValidateProjectInput:
    """Tests for validate_project_input."""

    def test_valid_project(self, tmp_path: Path) -> None:
        """A complete project structure should produce no issues."""
        _create_valid_project(tmp_path)
        issues = validate_project_input(tmp_path)
        assert issues == []

    def test_missing_pom_xml(self, tmp_path: Path) -> None:
        """Missing pom.xml should produce an error."""
        mule_dir = tmp_path / "src" / "main" / "mule"
        mule_dir.mkdir(parents=True)
        (mule_dir / "flow.xml").write_text(_VALID_FLOW_XML)
        issues = validate_project_input(tmp_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_001" in rule_ids
        assert any(i.severity == Severity.ERROR for i in issues if i.rule_id == "MULE_001")

    def test_missing_mule_dir(self, tmp_path: Path) -> None:
        """Missing src/main/mule/ should produce an error."""
        (tmp_path / "pom.xml").write_text("<project/>")
        issues = validate_project_input(tmp_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_002" in rule_ids

    def test_empty_mule_dir(self, tmp_path: Path) -> None:
        """Empty src/main/mule/ should produce an error."""
        (tmp_path / "pom.xml").write_text("<project/>")
        mule_dir = tmp_path / "src" / "main" / "mule"
        mule_dir.mkdir(parents=True)
        issues = validate_project_input(tmp_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_003" in rule_ids

    def test_xml_without_flows(self, tmp_path: Path) -> None:
        """XML files without flow elements should produce an error."""
        (tmp_path / "pom.xml").write_text("<project/>")
        mule_dir = tmp_path / "src" / "main" / "mule"
        mule_dir.mkdir(parents=True)
        (mule_dir / "config.xml").write_text('<?xml version="1.0"?>\n<mule/>')
        issues = validate_project_input(tmp_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_004" in rule_ids

    def test_all_issues_have_remediation_hints(self, tmp_path: Path) -> None:
        """All project issues should include remediation hints."""
        issues = validate_project_input(tmp_path)  # empty dir — multiple issues
        assert len(issues) > 0
        for issue in issues:
            assert issue.remediation_hint is not None


# ── Single-flow mode tests ────────────────────────────────────────────────────


class TestValidateSingleFlowInput:
    """Tests for validate_single_flow_input."""

    def test_valid_flow(self, tmp_path: Path) -> None:
        """A valid single-flow XML should produce only warnings (for external refs)."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_VALID_FLOW_XML)
        issues = validate_single_flow_input(xml_path)
        # Should have no ERROR issues, only warnings for external refs
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Non-existent file should produce an error."""
        xml_path = tmp_path / "missing.xml"
        issues = validate_single_flow_input(xml_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_010" in rule_ids

    def test_malformed_xml(self, tmp_path: Path) -> None:
        """Malformed XML should produce a parse error."""
        xml_path = tmp_path / "bad.xml"
        xml_path.write_text("<not-valid-xml>")
        issues = validate_single_flow_input(xml_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_012" in rule_ids

    def test_xml_without_flows(self, tmp_path: Path) -> None:
        """XML without flow elements should produce an error."""
        xml_path = tmp_path / "empty.xml"
        xml_path.write_text('<?xml version="1.0"?>\n<mule xmlns="http://www.mulesoft.org/schema/mule/core"></mule>')
        issues = validate_single_flow_input(xml_path)
        rule_ids = [i.rule_id for i in issues]
        assert "MULE_013" in rule_ids

    def test_external_config_ref_warning(self, tmp_path: Path) -> None:
        """External config-ref should produce a warning, not an error."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_FLOW_WITH_EXTERNAL_REFS)
        issues = validate_single_flow_input(xml_path)
        config_warnings = [i for i in issues if i.rule_id == "MULE_020"]
        assert len(config_warnings) >= 1
        for w in config_warnings:
            assert w.severity == Severity.WARNING

    def test_property_reference_warning(self, tmp_path: Path) -> None:
        """Property placeholder ${...} should produce a warning, not an error."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_FLOW_WITH_EXTERNAL_REFS)
        issues = validate_single_flow_input(xml_path)
        prop_warnings = [i for i in issues if i.rule_id == "MULE_021"]
        assert len(prop_warnings) >= 1
        for w in prop_warnings:
            assert w.severity == Severity.WARNING

    def test_no_errors_for_single_flow_external_refs(self, tmp_path: Path) -> None:
        """Single-flow mode: external refs should never be ERROR severity."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_FLOW_WITH_EXTERNAL_REFS)
        issues = validate_single_flow_input(xml_path)
        errors = [i for i in issues if i.severity in (Severity.ERROR, Severity.CRITICAL)]
        assert errors == []

    def test_all_issues_have_remediation_hints(self, tmp_path: Path) -> None:
        """All issues should include remediation hints."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_FLOW_WITH_EXTERNAL_REFS)
        issues = validate_single_flow_input(xml_path)
        assert len(issues) > 0
        for issue in issues:
            assert issue.remediation_hint is not None


# ── Dispatch function tests ───────────────────────────────────────────────────


class TestValidateMuleInputDispatch:
    """Tests for the dispatch function validate_mule_input."""

    def test_project_mode_dispatch(self, tmp_path: Path) -> None:
        """Project mode should dispatch to project validator."""
        _create_valid_project(tmp_path)
        issues = validate_mule_input(tmp_path, InputMode.PROJECT)
        assert issues == []

    def test_single_flow_mode_dispatch(self, tmp_path: Path) -> None:
        """Single-flow mode should dispatch to single-flow validator."""
        xml_path = tmp_path / "flow.xml"
        xml_path.write_text(_VALID_FLOW_XML)
        issues = validate_mule_input(xml_path, InputMode.SINGLE_FLOW)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []


# ── Fixtures ──────────────────────────────────────────────────────────────────


_VALID_FLOW_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http">
    <flow name="testFlow">
        <http:listener path="/test"/>
        <set-payload value="hello"/>
    </flow>
</mule>
"""

_FLOW_WITH_EXTERNAL_REFS = """\
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http">
    <flow name="externalRefFlow">
        <http:listener config-ref="External_Config" path="/api"/>
        <set-variable variableName="key" value="${api.key}"/>
        <http:request method="GET" url="${backend.url}" config-ref="Another_External"/>
    </flow>
</mule>
"""


def _create_valid_project(root: Path) -> None:
    """Create a minimal valid Mule project structure."""
    (root / "pom.xml").write_text("<project/>")
    mule_dir = root / "src" / "main" / "mule"
    mule_dir.mkdir(parents=True)
    (mule_dir / "flow.xml").write_text(_VALID_FLOW_XML)
