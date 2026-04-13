"""Shared sub-models used across analyze, transform, and validate contracts."""

from pydantic import BaseModel, Field

from m2la_contracts.enums import GapCategory, InputMode, Severity


class MigrationGap(BaseModel):
    """A construct or reference that cannot be fully migrated."""

    construct_name: str = Field(..., description="Name of the MuleSoft construct")
    source_location: str = Field(..., description="Source file and line (e.g., 'flows/main.xml:42')")
    category: GapCategory = Field(..., description="Classification of the gap")
    severity: Severity = Field(..., description="Impact severity")
    message: str = Field(..., description="Human-readable description of the gap")
    suggested_workaround: str | None = Field(default=None, description="Optional workaround suggestion")


class ConstructCount(BaseModel):
    """Summary counts of supported, unsupported, and partially supported constructs."""

    supported: int = Field(default=0, ge=0, description="Number of fully supported constructs")
    unsupported: int = Field(default=0, ge=0, description="Number of unsupported constructs")
    partial: int = Field(default=0, ge=0, description="Number of partially supported constructs")
    details: dict[str, int] = Field(
        default_factory=dict, description="Per-construct-type counts (e.g., {'http_listener': 2})"
    )


class Warning(BaseModel):
    """A warning emitted during analysis or transformation."""

    code: str = Field(..., description="Machine-readable warning code (e.g., 'MISSING_CONNECTOR_CONFIG')")
    message: str = Field(..., description="Human-readable warning message")
    severity: Severity = Field(default=Severity.WARNING, description="Warning severity")
    source_location: str | None = Field(default=None, description="Optional source file and line reference")


class ArtifactEntry(BaseModel):
    """A single output artifact in the generated Logic Apps project."""

    path: str = Field(..., description="Relative path of the artifact in the output directory")
    artifact_type: str = Field(
        ...,
        description="Type of artifact (e.g., 'workflow', 'host_json', 'connections_json', 'parameters_json')",
    )
    size_bytes: int | None = Field(default=None, ge=0, description="File size in bytes, if known")


class ArtifactManifest(BaseModel):
    """Manifest of all generated output artifacts."""

    artifacts: list[ArtifactEntry] = Field(default_factory=list, description="List of generated artifacts")
    output_directory: str = Field(..., description="Root output directory path")
    mode: InputMode = Field(..., description="Input mode that produced these artifacts")
