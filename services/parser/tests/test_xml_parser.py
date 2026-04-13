"""Tests for ``m2la_parser.xml_parser``."""

from pathlib import Path

from m2la_parser.models import MuleFlow, MuleSubFlow, ProcessorElement
from m2la_parser.xml_parser import (
    extract_config_refs,
    extract_flow_refs,
    parse_mule_xml,
)


# ---------------------------------------------------------------------------
# hello-flow.xml – flows
# ---------------------------------------------------------------------------
class TestParseFlowFile:
    """Verify parsing of hello-flow.xml (flows, triggers, processors, error handlers)."""

    def test_parse_flow_file(self, hello_world_project: Path) -> None:
        """Expect exactly 2 flows: helloFlow and scheduledFlow."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "hello-flow.xml"
        flows, subflows, _ge, _cc, flow_file, warnings = parse_mule_xml(xml_path, relative_to=hello_world_project)

        flow_names = [f.name for f in flows]
        assert "helloFlow" in flow_names
        assert "scheduledFlow" in flow_names
        assert len(flows) == 2
        assert subflows == []
        # Flow file summary
        assert set(flow_file.flow_names) == {"helloFlow", "scheduledFlow"}
        assert flow_file.sub_flow_names == []

    def test_hello_flow_trigger(self, hello_world_project: Path) -> None:
        """helloFlow should have an http:listener trigger."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "hello-flow.xml"
        flows, *_ = parse_mule_xml(xml_path, relative_to=hello_world_project)

        hello_flow = next(f for f in flows if f.name == "helloFlow")
        assert hello_flow.trigger is not None
        assert hello_flow.trigger.element_type == "listener"
        assert hello_flow.trigger.namespace == "http"
        assert hello_flow.trigger.config_ref == "HTTP_Listener_config"

    def test_hello_flow_processors(self, hello_world_project: Path) -> None:
        """helloFlow should contain set-variable, transform, flow-ref, request processors."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "hello-flow.xml"
        flows, *_ = parse_mule_xml(xml_path, relative_to=hello_world_project)

        hello_flow = next(f for f in flows if f.name == "helloFlow")
        proc_types = [p.element_type for p in hello_flow.processors]
        assert "set-variable" in proc_types
        assert "transform" in proc_types
        assert "flow-ref" in proc_types
        assert "request" in proc_types

    def test_hello_flow_error_handler(self, hello_world_project: Path) -> None:
        """helloFlow should have an error handler with 2 strategies."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "hello-flow.xml"
        flows, *_ = parse_mule_xml(xml_path, relative_to=hello_world_project)

        hello_flow = next(f for f in flows if f.name == "helloFlow")
        assert hello_flow.error_handler is not None
        assert len(hello_flow.error_handler.strategies) == 2

        strategy_types = {s.element_type for s in hello_flow.error_handler.strategies}
        assert "on-error-propagate" in strategy_types
        assert "on-error-continue" in strategy_types

    def test_scheduled_flow_trigger(self, hello_world_project: Path) -> None:
        """scheduledFlow should have a scheduler trigger."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "hello-flow.xml"
        flows, *_ = parse_mule_xml(xml_path, relative_to=hello_world_project)

        sched_flow = next(f for f in flows if f.name == "scheduledFlow")
        assert sched_flow.trigger is not None
        assert sched_flow.trigger.element_type == "scheduler"


# ---------------------------------------------------------------------------
# shared-subflow.xml – sub-flows
# ---------------------------------------------------------------------------
class TestParseSubflowFile:
    """Verify parsing of shared-subflow.xml."""

    def test_parse_subflow_file(self, hello_world_project: Path) -> None:
        """Expect 2 sub-flows: sharedLogic and errorHandlingLogic."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "shared-subflow.xml"
        flows, subflows, _ge, _cc, flow_file, warnings = parse_mule_xml(xml_path, relative_to=hello_world_project)

        assert flows == []
        sf_names = [sf.name for sf in subflows]
        assert "sharedLogic" in sf_names
        assert "errorHandlingLogic" in sf_names
        assert len(subflows) == 2
        assert set(flow_file.sub_flow_names) == {"sharedLogic", "errorHandlingLogic"}


# ---------------------------------------------------------------------------
# global-config.xml – global elements / connector configs
# ---------------------------------------------------------------------------
class TestParseGlobalConfig:
    """Verify parsing of global-config.xml."""

    def test_parse_global_config(self, hello_world_project: Path) -> None:
        """Expect 3 global elements: HTTP_Listener_config, HTTP_Request_config, Database_Config.

        ``db:config`` has local name ``config`` which is also detected as a global
        config element.
        """
        xml_path = hello_world_project / "src" / "main" / "mule" / "global-config.xml"
        _flows, _subflows, global_elements, connector_configs, _ff, warnings = parse_mule_xml(
            xml_path, relative_to=hello_world_project
        )

        ge_names = {ge.name for ge in global_elements}
        assert ge_names == {"HTTP_Listener_config", "HTTP_Request_config", "Database_Config"}
        assert len(global_elements) == 3

    def test_connector_config_properties(self, hello_world_project: Path) -> None:
        """Connector configs should have referenced_properties extracted."""
        xml_path = hello_world_project / "src" / "main" / "mule" / "global-config.xml"
        _flows, _subflows, _ge, connector_configs, _ff, _warnings = parse_mule_xml(
            xml_path, relative_to=hello_world_project
        )

        cc_by_name = {cc.name: cc for cc in connector_configs}

        listener = cc_by_name["HTTP_Listener_config"]
        assert "http.port" in listener.referenced_properties

        request = cc_by_name["HTTP_Request_config"]
        assert "api.host" in request.referenced_properties
        assert "api.port" in request.referenced_properties

        db = cc_by_name["Database_Config"]
        assert "db.host" in db.referenced_properties
        assert "db.port" in db.referenced_properties
        assert "db.user" in db.referenced_properties
        assert "db.password" in db.referenced_properties
        assert "db.name" in db.referenced_properties


# ---------------------------------------------------------------------------
# Malformed / empty XML
# ---------------------------------------------------------------------------
class TestMalformedXml:
    """Verify graceful handling of malformed XML."""

    def test_malformed_xml(self, malformed_flow_xml: Path) -> None:
        flows, subflows, global_elements, _cc, flow_file, warnings = parse_mule_xml(malformed_flow_xml)

        assert flows == []
        assert subflows == []
        assert global_elements == []
        assert any(w.code == "MALFORMED_XML" for w in warnings)


class TestEmptyMuleFile:
    """Verify warning for an XML file with no flows/sub-flows/global elements."""

    def test_empty_mule_file(self, empty_flow_xml: Path) -> None:
        flows, subflows, global_elements, _cc, _ff, warnings = parse_mule_xml(empty_flow_xml)

        assert flows == []
        assert subflows == []
        assert global_elements == []
        assert any(w.code == "EMPTY_MULE_FILE" for w in warnings)


# ---------------------------------------------------------------------------
# Helper functions: extract_config_refs, extract_flow_refs
# ---------------------------------------------------------------------------
class TestExtractConfigRefs:
    """Verify ``extract_config_refs`` collects all config-ref attribute values."""

    def test_extract_config_refs(self) -> None:
        trigger = ProcessorElement(
            element_type="listener",
            namespace="http",
            config_ref="MyListenerConfig",
            attributes={"config-ref": "MyListenerConfig", "path": "/api"},
        )
        proc = ProcessorElement(
            element_type="request",
            namespace="http",
            config_ref="MyRequestConfig",
            attributes={"config-ref": "MyRequestConfig"},
        )
        flow = MuleFlow(
            name="testFlow",
            source_file="test.xml",
            trigger=trigger,
            processors=[proc],
        )

        refs = extract_config_refs([flow], [])
        assert refs == {"MyListenerConfig", "MyRequestConfig"}


class TestExtractFlowRefs:
    """Verify ``extract_flow_refs`` collects all flow-ref target names."""

    def test_extract_flow_refs(self) -> None:
        proc1 = ProcessorElement(
            element_type="flow-ref",
            namespace=None,
            attributes={"name": "subflowA"},
        )
        proc2 = ProcessorElement(
            element_type="flow-ref",
            namespace=None,
            attributes={"name": "subflowB"},
        )
        flow = MuleFlow(
            name="testFlow",
            source_file="test.xml",
            processors=[proc1, proc2],
        )
        subflow = MuleSubFlow(
            name="parentSub",
            source_file="test.xml",
            processors=[
                ProcessorElement(
                    element_type="flow-ref",
                    namespace=None,
                    attributes={"name": "subflowC"},
                )
            ],
        )

        refs = extract_flow_refs([flow], [subflow])
        assert refs == {"subflowA", "subflowB", "subflowC"}
