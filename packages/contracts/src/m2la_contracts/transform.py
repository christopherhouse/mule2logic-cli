"""Transform request/response contracts (spec §4, §5)."""

from pydantic import BaseModel, Field

from m2la_contracts.common import ArtifactManifest, ConstructCount, MigrationGap, Warning
from m2la_contracts.enums import InputMode
from m2la_contracts.telemetry import TelemetryContext


class TransformRequest(BaseModel):
    """Request to transform a MuleSoft project or single flow into Logic Apps artifacts."""

    input_path: str = Field(..., description="Path to MuleSoft project root directory or single flow XML file")
    mode: InputMode | None = Field(default=None, description="Input mode; auto-detected from path if not specified")
    output_directory: str | None = Field(
        default=None, description="Output directory for generated artifacts; defaults to ./output if not specified"
    )
    telemetry: TelemetryContext | None = Field(default=None, description="Telemetry context for trace propagation")


class TransformResponse(BaseModel):
    """Response from transforming a MuleSoft project or single flow."""

    mode: InputMode = Field(..., description="Input mode used for transformation")
    project_name: str | None = Field(
        default=None, description="Project name (from pom.xml in project mode, None in single-flow mode)"
    )
    artifacts: ArtifactManifest = Field(..., description="Manifest of generated output artifacts")
    gaps: list[MigrationGap] = Field(
        default_factory=list, description="Migration gaps encountered during transformation"
    )
    warnings: list[Warning] = Field(default_factory=list, description="Warnings emitted during transformation")
    constructs: ConstructCount = Field(
        default_factory=ConstructCount, description="Construct counts for the transformation"
    )
    telemetry: TelemetryContext = Field(..., description="Telemetry context for trace correlation")
