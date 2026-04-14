"""Mule input validation rules.

Validates completeness and validity of Mule project or single-flow XML input.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from m2la_contracts.enums import InputMode, Severity, ValidationCategory
from m2la_contracts.validate import ValidationIssue


def validate_project_input(project_path: Path) -> list[ValidationIssue]:
    """Validate a Mule project directory for completeness.

    Checks:
    - pom.xml exists
    - src/main/mule/ directory exists and contains at least one .xml file
    - At least one flow XML contains a <flow> or <sub-flow> element
    """
    issues: list[ValidationIssue] = []

    # Check pom.xml
    pom_path = project_path / "pom.xml"
    if not pom_path.is_file():
        issues.append(
            ValidationIssue(
                rule_id="MULE_001",
                message="Missing pom.xml in project root",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(project_path),
                remediation_hint="Add a valid pom.xml to the project root directory.",
            )
        )

    # Check src/main/mule/ directory
    mule_dir = project_path / "src" / "main" / "mule"
    if not mule_dir.is_dir():
        issues.append(
            ValidationIssue(
                rule_id="MULE_002",
                message="Missing src/main/mule/ directory",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(project_path),
                remediation_hint="Create the src/main/mule/ directory with at least one Mule flow XML file.",
            )
        )
    else:
        xml_files = list(mule_dir.glob("*.xml"))
        if not xml_files:
            issues.append(
                ValidationIssue(
                    rule_id="MULE_003",
                    message="No XML files found in src/main/mule/",
                    severity=Severity.ERROR,
                    category=ValidationCategory.MULE_INPUT,
                    artifact_path=str(mule_dir),
                    remediation_hint="Add at least one Mule flow XML file to src/main/mule/.",
                )
            )
        else:
            # Check that at least one XML has a <flow> or <sub-flow>
            has_flow = False
            for xml_file in xml_files:
                try:
                    content = xml_file.read_text(encoding="utf-8")
                    if "<flow " in content or "<flow>" in content or "<sub-flow " in content or "<sub-flow>" in content:
                        has_flow = True
                        break
                except OSError:
                    pass
            if not has_flow:
                issues.append(
                    ValidationIssue(
                        rule_id="MULE_004",
                        message="No XML files in src/main/mule/ contain a <flow> or <sub-flow> element",
                        severity=Severity.ERROR,
                        category=ValidationCategory.MULE_INPUT,
                        artifact_path=str(mule_dir),
                        remediation_hint="Ensure at least one XML file contains a <flow> or <sub-flow> element.",
                    )
                )

    return issues


def validate_single_flow_input(xml_path: Path) -> list[ValidationIssue]:
    """Validate a single Mule flow XML file.

    Checks:
    - File exists and is readable
    - File is valid XML
    - Contains at least one <flow> or <sub-flow> element
    - External config-ref references produce warnings (not errors)
    - External property references produce warnings (not errors)
    """
    issues: list[ValidationIssue] = []

    if not xml_path.is_file():
        issues.append(
            ValidationIssue(
                rule_id="MULE_010",
                message=f"File does not exist: {xml_path}",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(xml_path),
                remediation_hint="Provide a valid path to a Mule flow XML file.",
            )
        )
        return issues

    try:
        content = xml_path.read_text(encoding="utf-8")
    except OSError as e:
        issues.append(
            ValidationIssue(
                rule_id="MULE_011",
                message=f"Cannot read file: {e}",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(xml_path),
                remediation_hint="Ensure the file is readable and not corrupted.",
            )
        )
        return issues

    # Check valid XML
    try:
        root = ET.fromstring(content)  # noqa: S314
    except ET.ParseError as e:
        issues.append(
            ValidationIssue(
                rule_id="MULE_012",
                message=f"Invalid XML: {e}",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(xml_path),
                remediation_hint="Fix the XML syntax errors in the file.",
            )
        )
        return issues

    # Check for flow/sub-flow elements
    ns = {"mule": "http://www.mulesoft.org/schema/mule/core"}
    flows = root.findall("mule:flow", ns) + root.findall("mule:sub-flow", ns)
    # Also check without namespace for flexibility
    flows += root.findall("flow") + root.findall("sub-flow")
    if not flows:
        issues.append(
            ValidationIssue(
                rule_id="MULE_013",
                message="No <flow> or <sub-flow> elements found in the XML file",
                severity=Severity.ERROR,
                category=ValidationCategory.MULE_INPUT,
                artifact_path=str(xml_path),
                remediation_hint="Ensure the XML file contains at least one <flow> or <sub-flow> element.",
            )
        )

    # Warn about external config-ref references (single-flow mode)
    _check_external_references(root, xml_path, issues)

    return issues


def _check_external_references(root: ET.Element, xml_path: Path, issues: list[ValidationIssue]) -> None:
    """Detect external config-ref and property references and emit warnings."""
    # Collect all config element names defined in this file
    defined_configs: set[str] = set()
    for elem in root.iter():
        tag = _local_name(elem.tag)
        if tag.endswith("-config") or tag == "configuration":
            name = elem.get("name")
            if name:
                defined_configs.add(name)

    # Find all config-ref attributes and check if they reference defined configs
    for elem in root.iter():
        config_ref = elem.get("config-ref")
        if config_ref and config_ref not in defined_configs:
            issues.append(
                ValidationIssue(
                    rule_id="MULE_020",
                    message=f"External config-ref '{config_ref}' not defined in this file",
                    severity=Severity.WARNING,
                    category=ValidationCategory.MULE_INPUT,
                    artifact_path=str(xml_path),
                    location=_local_name(elem.tag),
                    remediation_hint=(
                        f"Config '{config_ref}' is defined externally. "
                        "In single-flow mode, connector configuration will use defaults."
                    ),
                )
            )

    # Find property placeholder references ${...}
    _scan_property_refs(root, xml_path, issues)


def _scan_property_refs(root: ET.Element, xml_path: Path, issues: list[ValidationIssue]) -> None:
    """Scan for ${property} references and emit warnings."""
    prop_pattern = re.compile(r"\$\{([^}]+)\}")
    seen_props: set[str] = set()

    def _scan_text(text: str | None, element_tag: str) -> None:
        if not text:
            return
        for match in prop_pattern.finditer(text):
            prop_name = match.group(1)
            if prop_name not in seen_props:
                seen_props.add(prop_name)
                issues.append(
                    ValidationIssue(
                        rule_id="MULE_021",
                        message=(
                            f"External property reference '${{{prop_name}}}' cannot be resolved in single-flow mode"
                        ),
                        severity=Severity.WARNING,
                        category=ValidationCategory.MULE_INPUT,
                        artifact_path=str(xml_path),
                        location=_local_name(element_tag),
                        remediation_hint=(
                            f"Property '{prop_name}' is defined in external property files. "
                            "Review the generated output and supply the correct value."
                        ),
                    )
                )

    for elem in root.iter():
        # Check attributes
        for attr_val in elem.attrib.values():
            _scan_text(attr_val, elem.tag)
        # Check text content
        _scan_text(elem.text, elem.tag)
        _scan_text(elem.tail, elem.tag)


def _local_name(tag: str) -> str:
    """Strip namespace from an XML tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def validate_mule_input(input_path: Path, mode: InputMode) -> list[ValidationIssue]:
    """Dispatch to the appropriate Mule input validator based on mode."""
    if mode == InputMode.PROJECT:
        return validate_project_input(input_path)
    return validate_single_flow_input(input_path)
