/**
 * Analyze request/response contracts (spec §4, §5).
 *
 * Note: The analyze request is sent as multipart/form-data (file upload),
 * not as a JSON body.  The AnalyzeRequest type below describes the
 * logical fields; the actual upload is handled by the CLI's api-client.
 */

import type { ConstructCount, MigrationGap, Warning } from "./common.js";
import type { InputMode } from "./enums.js";
import type { TelemetryContext } from "./telemetry.js";

/**
 * Logical request to analyze a MuleSoft project or single flow.
 *
 * In practice, the project/flow data is uploaded as a file via
 * multipart/form-data.  The `mode` and telemetry are sent as form fields.
 */
export interface AnalyzeRequest {
  /** Input mode; auto-detected from filename if not specified. */
  mode?: InputMode | null;
  /** Telemetry context for trace propagation. */
  telemetry?: TelemetryContext | null;
}

/** Analysis result for a single Mule flow. */
export interface FlowAnalysis {
  /** Name of the Mule flow. */
  flow_name: string;
  /** Source XML file containing the flow. */
  source_file: string;
  /** Construct counts for this flow. */
  constructs: ConstructCount;
  /** Migration gaps found in this flow. */
  gaps: MigrationGap[];
  /** Warnings for this flow. */
  warnings: Warning[];
}

/** Response from analyzing a MuleSoft project or single flow. */
export interface AnalyzeResponse {
  /** Input mode used for analysis. */
  mode: InputMode;
  /** Project name (from pom.xml in project mode, null in single-flow mode). */
  project_name?: string | null;
  /** Per-flow analysis results. */
  flows: FlowAnalysis[];
  /** Aggregate construct counts across all flows. */
  overall_constructs: ConstructCount;
  /** All migration gaps found. */
  gaps: MigrationGap[];
  /** All warnings emitted. */
  warnings: Warning[];
  /** Telemetry context for trace correlation. */
  telemetry: TelemetryContext;
}
