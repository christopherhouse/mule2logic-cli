"""Tests for ``m2la_parser.project_discovery.discover_project``."""

from pathlib import Path

from m2la_contracts.enums import InputMode

from m2la_parser.project_discovery import discover_project


class TestDiscoverProjectMode:
    """Verify full project discovery against the hello-world-project sample."""

    def test_discover_project_mode(self, hello_world_project: Path) -> None:
        inventory = discover_project(str(hello_world_project))

        # Mode
        assert inventory.mode == InputMode.PROJECT

        # Project metadata from pom.xml
        assert inventory.project_metadata is not None
        assert inventory.project_metadata.group_id == "com.example"
        assert inventory.project_metadata.artifact_id == "hello-world-app"
        assert inventory.project_metadata.version == "1.0.0"
        assert inventory.project_metadata.mule_version == "4.4.0"

        # Mule XML files – 3 files in src/main/mule/
        xml_file_paths = {mf.file_path for mf in inventory.mule_xml_files}
        assert len(inventory.mule_xml_files) == 3
        # Paths should be relative to project root
        for fp in xml_file_paths:
            assert "hello-flow.xml" in fp or "shared-subflow.xml" in fp or "global-config.xml" in fp

        # Flows – helloFlow and scheduledFlow
        flow_names = {f.name for f in inventory.flows}
        assert flow_names == {"helloFlow", "scheduledFlow"}
        assert len(inventory.flows) == 2

        # Sub-flows – sharedLogic and errorHandlingLogic
        sf_names = {sf.name for sf in inventory.subflows}
        assert sf_names == {"sharedLogic", "errorHandlingLogic"}
        assert len(inventory.subflows) == 2

        # Global elements – includes db:config (local name "config") in addition to *-config tags
        ge_names = {ge.name for ge in inventory.global_elements}
        assert ge_names == {"HTTP_Listener_config", "HTTP_Request_config", "Database_Config"}
        assert len(inventory.global_elements) == 3

        # Connector configs – one per detected global element
        cc_names = {cc.name for cc in inventory.connector_configs}
        assert cc_names == {"HTTP_Listener_config", "HTTP_Request_config", "Database_Config"}
        assert len(inventory.connector_configs) == 3

        # Property files – 2 files
        pf_paths = [pf.file_path for pf in inventory.property_files]
        assert len(inventory.property_files) == 2
        assert any("application.properties" in p for p in pf_paths)
        assert any("application-dev.properties" in p for p in pf_paths)


class TestProjectCrossRefWarnings:
    """Verify cross-reference validation within the hello-world-project."""

    def test_no_missing_connector_config_warnings(self, hello_world_project: Path) -> None:
        """All config-refs in hello-flow.xml are defined in global-config.xml, so no
        MISSING_CONNECTOR_CONFIG warnings should be emitted."""
        inventory = discover_project(str(hello_world_project))

        missing_config_warnings = [w for w in inventory.warnings if w.code == "MISSING_CONNECTOR_CONFIG"]
        assert missing_config_warnings == [], f"Unexpected MISSING_CONNECTOR_CONFIG warnings: {missing_config_warnings}"

    def test_no_missing_flow_ref_warnings(self, hello_world_project: Path) -> None:
        """flow-ref to 'sharedLogic' is defined in shared-subflow.xml."""
        inventory = discover_project(str(hello_world_project))

        missing_flow_warnings = [w for w in inventory.warnings if w.code == "MISSING_FLOW_REF"]
        assert missing_flow_warnings == [], f"Unexpected MISSING_FLOW_REF warnings: {missing_flow_warnings}"


class TestProjectInvalidDir:
    """Verify warnings when given an empty directory (no Mule project structure)."""

    def test_project_invalid_dir(self, tmp_path: Path) -> None:
        inventory = discover_project(str(tmp_path))

        warning_codes = {w.code for w in inventory.warnings}
        assert "MISSING_POM" in warning_codes
        assert "MISSING_MULE_DIR" in warning_codes
