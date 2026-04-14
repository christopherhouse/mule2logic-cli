/**
 * Validation request/report contracts.
 *
 * Note: The validate request is sent as multipart/form-data (file upload),
 * not as a JSON body.  The ValidateRequest type below describes the
 * logical fields; the actual upload is handled by the CLI's api-client.
 */

import type { Severity } from "./enums.js";
import type { TelemetryContext } from "./telemetry.js";

/**
 * Logical request to validate generated Logic Apps artifacts.
 *
 * In practice, the output artifacts are uploaded as a zip file via
 * multipart/form-data.  The telemetry is sent as a form field.
 */
export interface ValidateRequest {
  /** Telemetry context for trace propagation. */
  telemetry?: TelemetryContext | null;
}

/** A single validation issue found in the generated artifacts. */
export interface ValidationIssue {
  /** Machine-readable rule identifier (e.g., 'SCHEMA_001'). */
  rule_id: string;
  /** Human-readable description of the issue. */
  message: string;
  /** Issue severity. */
  severity: Severity;
  /** Path to the artifact containing the issue. */
  artifact_path?: string | null;
  /** Location within the artifact (e.g., line number or JSON path). */
  location?: string | null;
}

/** Report from validating generated Logic Apps artifacts. */
export interface ValidationReport {
  /** Whether all artifacts passed validation. */
  valid: boolean;
  /** List of validation issues found. */
  issues: ValidationIssue[];
  /** Number of artifacts that were validated. */
  artifacts_validated: number;
  /** Telemetry context for trace correlation. */
  telemetry: TelemetryContext;
}
