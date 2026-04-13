"""Tests for ``m2la_parser.single_flow.parse_single_flow``."""

from pathlib import Path

from m2la_contracts.enums import InputMode

from m2la_parser.single_flow import parse_single_flow


class TestSingleFlowParse:
    """Verify basic parsing of standalone-flow.xml."""

    def test_single_flow_parse(self, standalone_flow_xml: Path) -> None:
        inventory = parse_single_flow(str(standalone_flow_xml))

        assert inventory.mode == InputMode.SINGLE_FLOW
        assert inventory.project_metadata is None

        # Flows
        flow_names = {f.name for f in inventory.flows}
        assert "standaloneApiFlow" in flow_names
        assert len(inventory.flows) == 1

        # Sub-flows
        sf_names = {sf.name for sf in inventory.subflows}
        assert "localHelper" in sf_names
        assert len(inventory.subflows) == 1

        # No property files in single-flow mode
        assert inventory.property_files == []


class TestSingleFlowMissingConfigWarnings:
    """Verify MISSING_CONNECTOR_CONFIG warnings for external configs."""

    def test_single_flow_missing_config_warnings(self, standalone_flow_xml: Path) -> None:
        inventory = parse_single_flow(str(standalone_flow_xml))

        missing_configs = [w for w in inventory.warnings if w.code == "MISSING_CONNECTOR_CONFIG"]
        missing_names = {w.message for w in missing_configs}

        assert any("External_HTTP_Config" in m for m in missing_names)
        assert any("External_Request_Config" in m for m in missing_names)


class TestSingleFlowMissingFlowRefWarnings:
    """Verify MISSING_FLOW_REF warning for external flow reference."""

    def test_single_flow_missing_flow_ref_warnings(self, standalone_flow_xml: Path) -> None:
        inventory = parse_single_flow(str(standalone_flow_xml))

        missing_refs = [w for w in inventory.warnings if w.code == "MISSING_FLOW_REF"]
        assert any("externalProcessingFlow" in w.message for w in missing_refs)


class TestSingleFlowPropertyWarnings:
    """Verify UNRESOLVABLE_PROPERTY warnings for all property placeholders."""

    def test_single_flow_property_warnings(self, standalone_flow_xml: Path) -> None:
        inventory = parse_single_flow(str(standalone_flow_xml))

        prop_warnings = [w for w in inventory.warnings if w.code == "UNRESOLVABLE_PROPERTY"]
        prop_messages = " ".join(w.message for w in prop_warnings)

        assert "api.key" in prop_messages
        assert "backend.url" in prop_messages


class TestSingleFlowFileNotFound:
    """Verify FILE_NOT_FOUND warning for a non-existent path."""

    def test_single_flow_file_not_found(self, tmp_path: Path) -> None:
        inventory = parse_single_flow(str(tmp_path / "nonexistent.xml"))

        assert any(w.code == "FILE_NOT_FOUND" for w in inventory.warnings)
        assert inventory.flows == []
        assert inventory.subflows == []


class TestSingleFlowMalformedXml:
    """Verify graceful handling of malformed XML in single-flow mode."""

    def test_single_flow_malformed_xml(self, malformed_flow_xml: Path) -> None:
        inventory = parse_single_flow(str(malformed_flow_xml))

        assert any(w.code == "MALFORMED_XML" for w in inventory.warnings)
        # Should not crash; inventory is returned with empty results
        assert inventory.mode == InputMode.SINGLE_FLOW
