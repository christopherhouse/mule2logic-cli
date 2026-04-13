"""Analyze request/response contracts (spec §4, §5)."""

from pydantic import BaseModel, Field

from m2la_contracts.common import ConstructCount, MigrationGap, Warning
from m2la_contracts.enums import InputMode
from m2la_contracts.telemetry import TelemetryContext


class AnalyzeRequest(BaseModel):
    """Request to analyze a MuleSoft project or single flow."""

    input_path: str = Field(..., description="Path to MuleSoft project root directory or single flow XML file")
    mode: InputMode | None = Field(default=None, description="Input mode; auto-detected from path if not specified")
    telemetry: TelemetryContext | None = Field(default=None, description="Telemetry context for trace propagation")


class FlowAnalysis(BaseModel):
    """Analysis result for a single Mule flow."""

    flow_name: str = Field(..., description="Name of the Mule flow")
    source_file: str = Field(..., description="Source XML file containing the flow")
    constructs: ConstructCount = Field(default_factory=ConstructCount, description="Construct counts for this flow")
    gaps: list[MigrationGap] = Field(default_factory=list, description="Migration gaps found in this flow")
    warnings: list[Warning] = Field(default_factory=list, description="Warnings for this flow")


class AnalyzeResponse(BaseModel):
    """Response from analyzing a MuleSoft project or single flow."""

    mode: InputMode = Field(..., description="Input mode used for analysis")
    project_name: str | None = Field(
        default=None, description="Project name (from pom.xml in project mode, None in single-flow mode)"
    )
    flows: list[FlowAnalysis] = Field(default_factory=list, description="Per-flow analysis results")
    overall_constructs: ConstructCount = Field(
        default_factory=ConstructCount, description="Aggregate construct counts across all flows"
    )
    gaps: list[MigrationGap] = Field(default_factory=list, description="All migration gaps found")
    warnings: list[Warning] = Field(default_factory=list, description="All warnings emitted")
    telemetry: TelemetryContext = Field(..., description="Telemetry context for trace correlation")
