"""Pydantic models for the MuleSoft project inventory."""

from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode
from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    """Metadata extracted from pom.xml."""

    group_id: str = Field(..., description="Maven groupId")
    artifact_id: str = Field(..., description="Maven artifactId")
    version: str = Field(..., description="Maven project version")
    mule_version: str | None = Field(default=None, description="Mule runtime version from properties or parent POM")
    connector_dependencies: list[str] = Field(
        default_factory=list, description="List of connector artifactIds found in dependencies"
    )


class ProcessorElement(BaseModel):
    """A processor element within a flow or sub-flow."""

    element_type: str = Field(..., description="Local element tag name (e.g., 'set-payload', 'request')")
    namespace: str | None = Field(default=None, description="Namespace prefix (e.g., 'http', 'ee', 'db')")
    config_ref: str | None = Field(default=None, description="config-ref attribute value, if present")
    attributes: dict[str, str] = Field(default_factory=dict, description="All attributes on the element")


class ErrorHandler(BaseModel):
    """An error-handler block within a flow."""

    strategies: list[ProcessorElement] = Field(
        default_factory=list,
        description="List of on-error-propagate / on-error-continue elements",
    )


class MuleFlow(BaseModel):
    """A parsed <flow> element."""

    name: str = Field(..., description="Flow name attribute")
    source_file: str = Field(..., description="Relative path of the XML file containing this flow")
    trigger: ProcessorElement | None = Field(default=None, description="Trigger element (first child if applicable)")
    processors: list[ProcessorElement] = Field(default_factory=list, description="Processor elements in the flow")
    error_handler: ErrorHandler | None = Field(default=None, description="Error handler block, if present")


class MuleSubFlow(BaseModel):
    """A parsed <sub-flow> element."""

    name: str = Field(..., description="Sub-flow name attribute")
    source_file: str = Field(..., description="Relative path of the XML file containing this sub-flow")
    processors: list[ProcessorElement] = Field(default_factory=list, description="Processor elements in the sub-flow")


class GlobalElement(BaseModel):
    """A global configuration element (e.g., <http:listener-config>)."""

    name: str = Field(..., description="Name attribute of the global element")
    element_type: str = Field(..., description="Local tag name (e.g., 'listener-config')")
    namespace: str | None = Field(default=None, description="Namespace prefix (e.g., 'http', 'db')")
    attributes: dict[str, str] = Field(default_factory=dict, description="All attributes on the element")


class ConnectorConfig(BaseModel):
    """A connector configuration element with its referenced properties."""

    name: str = Field(..., description="Name attribute of the connector config")
    connector_type: str = Field(..., description="Local tag name (e.g., 'listener-config', 'request-config')")
    namespace: str | None = Field(default=None, description="Namespace prefix (e.g., 'http', 'db')")
    referenced_properties: list[str] = Field(
        default_factory=list, description="Property placeholders found in this config (e.g., ['http.port'])"
    )


class PropertyFile(BaseModel):
    """A parsed Java .properties file."""

    file_path: str = Field(..., description="Relative path of the properties file")
    properties: dict[str, str] = Field(default_factory=dict, description="Key-value pairs from the properties file")


class MuleFlowFile(BaseModel):
    """Summary of a discovered Mule XML file."""

    file_path: str = Field(..., description="Relative path of the XML file")
    flow_names: list[str] = Field(default_factory=list, description="Names of <flow> elements in this file")
    sub_flow_names: list[str] = Field(default_factory=list, description="Names of <sub-flow> elements in this file")


class ProjectInventory(BaseModel):
    """Top-level normalized model for a parsed MuleSoft project or single flow."""

    mode: InputMode = Field(..., description="Input mode (project or single_flow)")
    project_metadata: ProjectMetadata | None = Field(
        default=None, description="Project metadata from pom.xml (None in single-flow mode)"
    )
    mule_xml_files: list[MuleFlowFile] = Field(default_factory=list, description="Discovered Mule XML files")
    flows: list[MuleFlow] = Field(default_factory=list, description="All parsed flows")
    subflows: list[MuleSubFlow] = Field(default_factory=list, description="All parsed sub-flows")
    global_elements: list[GlobalElement] = Field(default_factory=list, description="All global configuration elements")
    connector_configs: list[ConnectorConfig] = Field(
        default_factory=list, description="Connector configurations extracted from global elements"
    )
    property_files: list[PropertyFile] = Field(default_factory=list, description="Parsed property files")
    warnings: list[Warning] = Field(default_factory=list, description="Structured warnings emitted during parsing")
