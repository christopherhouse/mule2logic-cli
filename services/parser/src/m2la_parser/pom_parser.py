"""Parse pom.xml to extract project metadata and connector dependencies."""

import xml.etree.ElementTree as StdET
from pathlib import Path

import defusedxml.ElementTree as ET
from m2la_contracts.common import Warning
from m2la_contracts.enums import Severity

from m2la_parser.models import ProjectMetadata

# Maven POM namespace
_POM_NS = "{http://maven.apache.org/POM/4.0.0}"

# Known Mule connector groupIds
_CONNECTOR_GROUP_IDS = frozenset(
    {
        "org.mule.connectors",
        "org.mule.modules",
        "com.mulesoft.connectors",
        "com.mulesoft.modules",
        "org.mule.tooling.shadowed",
    }
)


def parse_pom(pom_path: Path) -> tuple[ProjectMetadata | None, list[Warning]]:
    """Parse a pom.xml file and extract project metadata.

    Args:
        pom_path: Path to the pom.xml file.

    Returns:
        A tuple of (ProjectMetadata or None, list of warnings).
    """
    warnings: list[Warning] = []

    if not pom_path.exists():
        warnings.append(
            Warning(
                code="MISSING_POM",
                message=f"pom.xml not found at {pom_path}",
                severity=Severity.ERROR,
                source_location=str(pom_path),
            )
        )
        return None, warnings

    try:
        tree = ET.parse(pom_path)
    except StdET.ParseError as e:
        warnings.append(
            Warning(
                code="MALFORMED_POM",
                message=f"Failed to parse pom.xml: {e}",
                severity=Severity.ERROR,
                source_location=str(pom_path),
            )
        )
        return None, warnings

    root = tree.getroot()

    # Extract coordinates — try with and without namespace
    group_id = _get_text(root, f"{_POM_NS}groupId") or _get_text(root, "groupId") or "unknown"
    artifact_id = _get_text(root, f"{_POM_NS}artifactId") or _get_text(root, "artifactId") or "unknown"
    version = _get_text(root, f"{_POM_NS}version") or _get_text(root, "version") or "0.0.0"

    # Extract Mule version from properties
    mule_version = _extract_mule_version(root)

    # Extract connector dependencies
    connectors = _extract_connector_deps(root)

    metadata = ProjectMetadata(
        group_id=group_id,
        artifact_id=artifact_id,
        version=version,
        mule_version=mule_version,
        connector_dependencies=connectors,
    )

    return metadata, warnings


def _get_text(element: StdET.Element, tag: str) -> str | None:
    """Get text content of a child element, or None if not found."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _extract_mule_version(root: StdET.Element) -> str | None:
    """Extract Mule version from POM properties."""
    # Look in <properties>
    for props_tag in [f"{_POM_NS}properties", "properties"]:
        props = root.find(props_tag)
        if props is not None:
            for version_tag in ["mule.version", "app.runtime"]:
                for ns in [_POM_NS, ""]:
                    version = _get_text(props, f"{ns}{version_tag}")
                    if version:
                        return version
    return None


def _extract_connector_deps(root: StdET.Element) -> list[str]:
    """Extract Mule connector dependency artifactIds from POM."""
    connectors: list[str] = []

    for deps_tag in [f"{_POM_NS}dependencies", "dependencies"]:
        deps_el = root.find(deps_tag)
        if deps_el is None:
            continue

        for dep_tag in [f"{_POM_NS}dependency", "dependency"]:
            for dep in deps_el.findall(dep_tag):
                group = _get_text(dep, f"{_POM_NS}groupId") or _get_text(dep, "groupId")
                artifact = _get_text(dep, f"{_POM_NS}artifactId") or _get_text(dep, "artifactId")

                if group in _CONNECTOR_GROUP_IDS and artifact:
                    connectors.append(artifact)

    return connectors
