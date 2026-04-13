"""Parse Mule flow XML files to extract flows, sub-flows, global elements, and connector configs."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from m2la_contracts.common import Warning
from m2la_contracts.enums import Severity

from m2la_parser.models import (
    ConnectorConfig,
    ErrorHandler,
    GlobalElement,
    MuleFlow,
    MuleFlowFile,
    MuleSubFlow,
    ProcessorElement,
)

# Mule core namespace
_MULE_CORE_NS = "http://www.mulesoft.org/schema/mule/core"

# Pattern to match ${property.name} placeholders
_PROPERTY_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Known trigger element local names (first child of a flow acts as a source/trigger)
_TRIGGER_TYPES = frozenset({"listener", "scheduler", "polling-source"})

# Tags that represent global config elements (typically end with '-config')
_CONFIG_SUFFIX = "-config"

# Error handler related tags
_ERROR_HANDLER_TAG = "error-handler"
_ERROR_STRATEGY_TAGS = frozenset({"on-error-propagate", "on-error-continue"})


def parse_mule_xml(
    xml_path: Path, relative_to: Path | None = None
) -> tuple[list[MuleFlow], list[MuleSubFlow], list[GlobalElement], list[ConnectorConfig], MuleFlowFile, list[Warning]]:
    """Parse a single Mule XML file.

    Args:
        xml_path: Absolute path to the Mule XML file.
        relative_to: Base path for computing relative file paths. Defaults to xml_path.parent.

    Returns:
        Tuple of (flows, subflows, global_elements, connector_configs, flow_file_summary, warnings).
    """
    warnings: list[Warning] = []
    base = relative_to or xml_path.parent
    rel_path = str(xml_path.relative_to(base)) if xml_path.is_relative_to(base) else str(xml_path)

    # Parse XML
    try:
        tree = ET.parse(xml_path)  # noqa: S314
    except ET.ParseError as e:
        warnings.append(
            Warning(
                code="MALFORMED_XML",
                message=f"Failed to parse XML file: {e}",
                severity=Severity.ERROR,
                source_location=rel_path,
            )
        )
        empty_file = MuleFlowFile(file_path=rel_path, flow_names=[], sub_flow_names=[])
        return [], [], [], [], empty_file, warnings

    root = tree.getroot()

    # Build namespace map for resolving prefixes
    ns_map = _build_namespace_prefix_map(root)

    flows: list[MuleFlow] = []
    subflows: list[MuleSubFlow] = []
    global_elements: list[GlobalElement] = []
    connector_configs: list[ConnectorConfig] = []

    for child in root:
        tag = child.tag
        local_name = _local_name(tag)
        ns_uri = _namespace_uri(tag)
        ns_prefix = ns_map.get(ns_uri)

        if local_name == "flow":
            flow = _parse_flow(child, rel_path, ns_map)
            flows.append(flow)
        elif local_name == "sub-flow":
            subflow = _parse_subflow(child, rel_path, ns_map)
            subflows.append(subflow)
        elif _is_global_config(local_name):
            name = child.attrib.get("name", "")
            attrs = dict(child.attrib)
            ge = GlobalElement(
                name=name,
                element_type=local_name,
                namespace=ns_prefix,
                attributes=attrs,
            )
            global_elements.append(ge)

            # Also create a ConnectorConfig with property references
            props = _extract_property_refs_from_element(child)
            cc = ConnectorConfig(
                name=name,
                connector_type=local_name,
                namespace=ns_prefix,
                referenced_properties=props,
            )
            connector_configs.append(cc)

    # Build file summary
    flow_file = MuleFlowFile(
        file_path=rel_path,
        flow_names=[f.name for f in flows],
        sub_flow_names=[sf.name for sf in subflows],
    )

    # Warn if no flows or sub-flows found
    if not flows and not subflows and not global_elements:
        warnings.append(
            Warning(
                code="EMPTY_MULE_FILE",
                message="No flows, sub-flows, or global elements found in file",
                severity=Severity.WARNING,
                source_location=rel_path,
            )
        )

    return flows, subflows, global_elements, connector_configs, flow_file, warnings


def extract_property_placeholders(element: ET.Element) -> list[str]:
    """Extract all ${property.name} placeholders from an element and its descendants.

    Args:
        element: The XML element to search.

    Returns:
        List of unique property names found.
    """
    return _extract_property_refs_from_element(element)


def extract_config_refs(flows: list[MuleFlow], subflows: list[MuleSubFlow]) -> set[str]:
    """Collect all config-ref values from flows and sub-flows.

    Args:
        flows: Parsed flow models.
        subflows: Parsed sub-flow models.

    Returns:
        Set of config-ref values.
    """
    refs: set[str] = set()
    for flow in flows:
        if flow.trigger and flow.trigger.config_ref:
            refs.add(flow.trigger.config_ref)
        for proc in flow.processors:
            if proc.config_ref:
                refs.add(proc.config_ref)
    for sf in subflows:
        for proc in sf.processors:
            if proc.config_ref:
                refs.add(proc.config_ref)
    return refs


def extract_flow_refs(flows: list[MuleFlow], subflows: list[MuleSubFlow]) -> set[str]:
    """Collect all flow-ref name values from flows and sub-flows.

    Args:
        flows: Parsed flow models.
        subflows: Parsed sub-flow models.

    Returns:
        Set of flow-ref target names.
    """
    refs: set[str] = set()
    for flow in flows:
        for proc in flow.processors:
            if proc.element_type == "flow-ref" and "name" in proc.attributes:
                refs.add(proc.attributes["name"])
    for sf in subflows:
        for proc in sf.processors:
            if proc.element_type == "flow-ref" and "name" in proc.attributes:
                refs.add(proc.attributes["name"])
    return refs


def _parse_flow(element: ET.Element, source_file: str, ns_map: dict[str, str | None]) -> MuleFlow:
    """Parse a <flow> element into a MuleFlow model."""
    name = element.attrib.get("name", "unnamed")
    trigger: ProcessorElement | None = None
    processors: list[ProcessorElement] = []
    error_handler: ErrorHandler | None = None

    children = list(element)
    for i, child in enumerate(children):
        local = _local_name(child.tag)
        ns_uri = _namespace_uri(child.tag)
        ns_prefix = ns_map.get(ns_uri)

        if local == _ERROR_HANDLER_TAG:
            error_handler = _parse_error_handler(child, ns_map)
        elif i == 0 and _is_trigger(local):
            trigger = _element_to_processor(child, ns_prefix)
        else:
            processors.append(_element_to_processor(child, ns_prefix))

    return MuleFlow(
        name=name,
        source_file=source_file,
        trigger=trigger,
        processors=processors,
        error_handler=error_handler,
    )


def _parse_subflow(element: ET.Element, source_file: str, ns_map: dict[str, str | None]) -> MuleSubFlow:
    """Parse a <sub-flow> element into a MuleSubFlow model."""
    name = element.attrib.get("name", "unnamed")
    processors: list[ProcessorElement] = []

    for child in element:
        ns_uri = _namespace_uri(child.tag)
        ns_prefix = ns_map.get(ns_uri)
        processors.append(_element_to_processor(child, ns_prefix))

    return MuleSubFlow(name=name, source_file=source_file, processors=processors)


def _parse_error_handler(element: ET.Element, ns_map: dict[str, str | None]) -> ErrorHandler:
    """Parse an <error-handler> block."""
    strategies: list[ProcessorElement] = []
    for child in element:
        local = _local_name(child.tag)
        ns_uri = _namespace_uri(child.tag)
        ns_prefix = ns_map.get(ns_uri)
        if local in _ERROR_STRATEGY_TAGS:
            strategies.append(_element_to_processor(child, ns_prefix))
    return ErrorHandler(strategies=strategies)


def _element_to_processor(element: ET.Element, ns_prefix: str | None) -> ProcessorElement:
    """Convert an XML element to a ProcessorElement model."""
    local = _local_name(element.tag)
    config_ref = element.attrib.get("config-ref")
    return ProcessorElement(
        element_type=local,
        namespace=ns_prefix,
        config_ref=config_ref,
        attributes=dict(element.attrib),
    )


def _is_trigger(local_name: str) -> bool:
    """Check if a local element name represents a trigger."""
    return local_name in _TRIGGER_TYPES


def _is_global_config(local_name: str) -> bool:
    """Check if a local element name represents a global config element."""
    return local_name.endswith(_CONFIG_SUFFIX) or local_name == "config"


def _local_name(tag: str) -> str:
    """Extract local name from a potentially namespaced tag like {ns}local."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _namespace_uri(tag: str) -> str:
    """Extract namespace URI from a tag like {ns}local."""
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return ""


def _build_namespace_prefix_map(root: ET.Element) -> dict[str, str | None]:
    """Build a mapping from namespace URI to prefix by inspecting the root element.

    Note: ElementTree doesn't preserve namespace prefixes natively.
    We use the registered namespaces and known Mule namespace conventions.
    """
    # Well-known Mule namespace prefix mappings
    known_prefixes: dict[str, str] = {
        "http://www.mulesoft.org/schema/mule/core": "core",
        "http://www.mulesoft.org/schema/mule/http": "http",
        "http://www.mulesoft.org/schema/mule/db": "db",
        "http://www.mulesoft.org/schema/mule/ee/core": "ee",
        "http://www.mulesoft.org/schema/mule/jms": "jms",
        "http://www.mulesoft.org/schema/mule/file": "file",
        "http://www.mulesoft.org/schema/mule/ftp": "ftp",
        "http://www.mulesoft.org/schema/mule/sftp": "sftp",
        "http://www.mulesoft.org/schema/mule/vm": "vm",
        "http://www.mulesoft.org/schema/mule/os": "os",
        "http://www.mulesoft.org/schema/mule/scripting": "scripting",
        "http://www.mulesoft.org/schema/mule/apikit": "apikit",
    }

    # Namespace URI -> prefix (or None for core/unknown)
    ns_map: dict[str, str | None] = {}

    # Add known prefixes
    for uri, prefix in known_prefixes.items():
        ns_map[uri] = prefix if prefix != "core" else None

    # Also try to discover from tag prefixes in the document (best-effort)
    # ElementTree doesn't give us xmlns declarations, but we can infer from tags
    for elem in root.iter():
        ns_uri = _namespace_uri(elem.tag)
        if ns_uri and ns_uri not in ns_map:
            # Try to extract a short name from the URI
            # e.g., "http://www.mulesoft.org/schema/mule/http" -> "http"
            parts = ns_uri.rstrip("/").split("/")
            if parts:
                ns_map[ns_uri] = parts[-1]

    return ns_map


def _extract_property_refs_from_element(element: ET.Element) -> list[str]:
    """Extract all ${property.name} references from an element and its descendants."""
    props: set[str] = set()

    # Check attributes
    for value in element.attrib.values():
        for match in _PROPERTY_PATTERN.finditer(value):
            props.add(match.group(1))

    # Check text content
    if element.text:
        for match in _PROPERTY_PATTERN.finditer(element.text):
            props.add(match.group(1))

    # Recurse into children
    for child in element:
        child_props = _extract_property_refs_from_element(child)
        props.update(child_props)

    return sorted(props)
