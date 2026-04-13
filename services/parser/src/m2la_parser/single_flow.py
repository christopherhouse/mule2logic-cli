"""Single-flow mode: parse a standalone Mule XML file."""

import xml.etree.ElementTree as StdET
from pathlib import Path

import defusedxml.ElementTree as ET
from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode, Severity

from m2la_parser.models import ProjectInventory
from m2la_parser.xml_parser import (
    extract_config_refs,
    extract_flow_refs,
    extract_property_placeholders,
    parse_mule_xml,
)


def parse_single_flow(xml_path: str) -> ProjectInventory:
    """Parse a standalone Mule XML file in single-flow mode.

    Emits structured warnings for unresolvable external references
    (connector configs, property placeholders, flow-refs) rather than failing.

    Args:
        xml_path: Path to the standalone Mule XML file.

    Returns:
        A ProjectInventory with mode=SINGLE_FLOW, no project metadata or property files.
    """
    path = Path(xml_path).resolve()
    warnings: list[Warning] = []

    if not path.exists():
        warnings.append(
            Warning(
                code="FILE_NOT_FOUND",
                message=f"Input file not found: {xml_path}",
                severity=Severity.ERROR,
                source_location=str(path),
            )
        )
        return ProjectInventory(mode=InputMode.SINGLE_FLOW, warnings=warnings)

    # Parse the XML file
    flows, subflows, global_elements, connector_configs, flow_file, xml_warnings = parse_mule_xml(path)
    warnings.extend(xml_warnings)

    # Warn if no flows or sub-flows
    if not flows and not subflows:
        warnings.append(
            Warning(
                code="NO_FLOWS_FOUND",
                message="No <flow> or <sub-flow> elements found in the file",
                severity=Severity.ERROR,
                source_location=str(path),
            )
        )

    # Check config-refs — any not defined in this file are unresolvable
    known_config_names = {ge.name for ge in global_elements}
    config_refs = extract_config_refs(flows, subflows)
    for ref in sorted(config_refs):
        if ref not in known_config_names:
            warnings.append(
                Warning(
                    code="MISSING_CONNECTOR_CONFIG",
                    message=f"config-ref '{ref}' references an external connector config not defined in this file",
                    severity=Severity.WARNING,
                    source_location=str(path),
                )
            )

    # Check flow-refs — any not defined in this file are unresolvable
    known_flow_names = {f.name for f in flows} | {sf.name for sf in subflows}
    flow_ref_targets = extract_flow_refs(flows, subflows)
    for ref in sorted(flow_ref_targets):
        if ref not in known_flow_names:
            warnings.append(
                Warning(
                    code="MISSING_FLOW_REF",
                    message=f"flow-ref target '{ref}' not found in this file — may be defined externally",
                    severity=Severity.WARNING,
                    source_location=str(path),
                )
            )

    # Check property placeholders — all are unresolvable in single-flow mode
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        property_refs = extract_property_placeholders(root)
        for prop in property_refs:
            warnings.append(
                Warning(
                    code="UNRESOLVABLE_PROPERTY",
                    message=f"Property placeholder '${{{prop}}}' cannot be resolved in single-flow mode",
                    severity=Severity.WARNING,
                    source_location=str(path),
                )
            )
    except StdET.ParseError:
        pass  # Already warned about malformed XML

    return ProjectInventory(
        mode=InputMode.SINGLE_FLOW,
        project_metadata=None,
        mule_xml_files=[flow_file],
        flows=flows,
        subflows=subflows,
        global_elements=global_elements,
        connector_configs=connector_configs,
        property_files=[],
        warnings=warnings,
    )
