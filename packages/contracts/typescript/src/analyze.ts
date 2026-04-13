/**
 * Analyze request/response contracts (spec §4, §5).
 */

import type { ConstructCount, MigrationGap, Warning } from "./common.js";
import type { InputMode } from "./enums.js";
import type { TelemetryContext } from "./telemetry.js";

/** Request to analyze a MuleSoft project or single flow. */
export interface AnalyzeRequest {
  /** Path to MuleSoft project root directory or single flow XML file. */
  input_path: string;
  /** Input mode; auto-detected from path if not specified. */
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
