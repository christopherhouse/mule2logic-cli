/**
 * Transform request/response contracts (spec §4, §5).
 */

import type { ArtifactManifest, ConstructCount, MigrationGap, Warning } from "./common.js";
import type { InputMode } from "./enums.js";
import type { TelemetryContext } from "./telemetry.js";

/** Request to transform a MuleSoft project or single flow into Logic Apps artifacts. */
export interface TransformRequest {
  /** Path to MuleSoft project root directory or single flow XML file. */
  input_path: string;
  /** Input mode; auto-detected from path if not specified. */
  mode?: InputMode | null;
  /** Output directory for generated artifacts; defaults to ./output if not specified. */
  output_directory?: string | null;
  /** Telemetry context for trace propagation. */
  telemetry?: TelemetryContext | null;
}

/** Response from transforming a MuleSoft project or single flow. */
export interface TransformResponse {
  /** Input mode used for transformation. */
  mode: InputMode;
  /** Project name (from pom.xml in project mode, null in single-flow mode). */
  project_name?: string | null;
  /** Manifest of generated output artifacts. */
  artifacts: ArtifactManifest;
  /** Migration gaps encountered during transformation. */
  gaps: MigrationGap[];
  /** Warnings emitted during transformation. */
  warnings: Warning[];
  /** Construct counts for the transformation. */
  constructs: ConstructCount;
  /** Telemetry context for trace correlation. */
  telemetry: TelemetryContext;
}
