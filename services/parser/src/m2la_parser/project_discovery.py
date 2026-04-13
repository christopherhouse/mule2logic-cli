"""Project mode: discover and parse a full MuleSoft project."""

import xml.etree.ElementTree as StdET
from pathlib import Path

import defusedxml.ElementTree as ET
from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode, Severity

from m2la_parser.models import (
    ConnectorConfig,
    GlobalElement,
    MuleFlow,
    MuleFlowFile,
    MuleSubFlow,
    ProjectInventory,
    PropertyFile,
)
from m2la_parser.pom_parser import parse_pom
from m2la_parser.property_parser import parse_properties_file
from m2la_parser.xml_parser import (
    extract_config_refs,
    extract_flow_refs,
    extract_property_placeholders,
    parse_mule_xml,
)


def discover_project(project_root: str) -> ProjectInventory:
    """Discover and parse a MuleSoft project from a root directory.

    Args:
        project_root: Path to the MuleSoft project root directory.

    Returns:
        A fully populated ProjectInventory.
    """
    root = Path(project_root).resolve()
    warnings: list[Warning] = []

    # Validate project structure
    pom_path = root / "pom.xml"
    mule_dir = root / "src" / "main" / "mule"

    if not pom_path.exists():
        warnings.append(
            Warning(
                code="MISSING_POM",
                message="pom.xml not found in project root — this may not be a valid Mule project",
                severity=Severity.ERROR,
                source_location=str(root),
            )
        )

    if not mule_dir.exists():
        warnings.append(
            Warning(
                code="MISSING_MULE_DIR",
                message="src/main/mule/ directory not found — this may not be a valid Mule project",
                severity=Severity.ERROR,
                source_location=str(root),
            )
        )

    # Parse pom.xml
    metadata, pom_warnings = parse_pom(pom_path)
    warnings.extend(pom_warnings)

    # Discover and parse Mule XML files
    all_flows: list[MuleFlow] = []
    all_subflows: list[MuleSubFlow] = []
    all_global_elements: list[GlobalElement] = []
    all_connector_configs: list[ConnectorConfig] = []
    all_flow_files: list[MuleFlowFile] = []

    if mule_dir.exists():
        xml_files = sorted(mule_dir.rglob("*.xml"))
        for xml_file in xml_files:
            flows, subflows, global_els, conn_configs, flow_file, xml_warnings = parse_mule_xml(
                xml_file, relative_to=root
            )
            all_flows.extend(flows)
            all_subflows.extend(subflows)
            all_global_elements.extend(global_els)
            all_connector_configs.extend(conn_configs)
            all_flow_files.append(flow_file)
            warnings.extend(xml_warnings)

    # Discover and parse property files
    all_property_files: list[PropertyFile] = []
    resources_dir = root / "src" / "main" / "resources"
    if resources_dir.exists():
        prop_files = sorted(resources_dir.glob("*.properties"))
        for prop_file in prop_files:
            pf, pf_warnings = parse_properties_file(prop_file, relative_to=root)
            all_property_files.append(pf)
            warnings.extend(pf_warnings)

    # Cross-reference: check config-refs
    known_config_names = {ge.name for ge in all_global_elements}
    config_refs = extract_config_refs(all_flows, all_subflows)
    for ref in sorted(config_refs):
        if ref not in known_config_names:
            warnings.append(
                Warning(
                    code="MISSING_CONNECTOR_CONFIG",
                    message=f"config-ref '{ref}' not found in any global configuration",
                    severity=Severity.WARNING,
                )
            )

    # Cross-reference: check flow-refs
    known_flow_names = {f.name for f in all_flows} | {sf.name for sf in all_subflows}
    flow_refs = extract_flow_refs(all_flows, all_subflows)
    for ref in sorted(flow_refs):
        if ref not in known_flow_names:
            warnings.append(
                Warning(
                    code="MISSING_FLOW_REF",
                    message=f"flow-ref target '{ref}' not found in any parsed flow or sub-flow",
                    severity=Severity.WARNING,
                )
            )

    # Cross-reference: check property placeholders
    all_properties: dict[str, str] = {}
    for pf in all_property_files:
        all_properties.update(pf.properties)

    all_property_refs: set[str] = set()
    if mule_dir.exists():
        for xml_file in sorted(mule_dir.rglob("*.xml")):
            try:
                tree = ET.parse(xml_file)
                root_el = tree.getroot()
                for prop in extract_property_placeholders(root_el):
                    all_property_refs.add(prop)
            except StdET.ParseError:
                pass  # Already warned about malformed XML

    for prop in sorted(all_property_refs):
        if prop not in all_properties:
            warnings.append(
                Warning(
                    code="UNRESOLVABLE_PROPERTY",
                    message=f"Property placeholder '${{{prop}}}' not found in any properties file",
                    severity=Severity.WARNING,
                )
            )

    return ProjectInventory(
        mode=InputMode.PROJECT,
        project_metadata=metadata,
        mule_xml_files=all_flow_files,
        flows=all_flows,
        subflows=all_subflows,
        global_elements=all_global_elements,
        connector_configs=all_connector_configs,
        property_files=all_property_files,
        warnings=warnings,
    )
