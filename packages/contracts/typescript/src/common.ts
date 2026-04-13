/**
 * Shared sub-models used across analyze, transform, and validate contracts.
 */

import type { GapCategory, InputMode, Severity } from "./enums.js";

/** A construct or reference that cannot be fully migrated. */
export interface MigrationGap {
  /** Name of the MuleSoft construct. */
  construct_name: string;
  /** Source file and line (e.g., 'flows/main.xml:42'). */
  source_location: string;
  /** Classification of the gap. */
  category: GapCategory;
  /** Impact severity. */
  severity: Severity;
  /** Human-readable description of the gap. */
  message: string;
  /** Optional workaround suggestion. */
  suggested_workaround?: string | null;
}

/** Summary counts of supported, unsupported, and partially supported constructs. */
export interface ConstructCount {
  /** Number of fully supported constructs. */
  supported: number;
  /** Number of unsupported constructs. */
  unsupported: number;
  /** Number of partially supported constructs. */
  partial: number;
  /** Per-construct-type counts (e.g., { 'http_listener': 2 }). */
  details: Record<string, number>;
}

/** A warning emitted during analysis or transformation. */
export interface Warning {
  /** Machine-readable warning code (e.g., 'MISSING_CONNECTOR_CONFIG'). */
  code: string;
  /** Human-readable warning message. */
  message: string;
  /** Warning severity. */
  severity: Severity;
  /** Optional source file and line reference. */
  source_location?: string | null;
}

/** A single output artifact in the generated Logic Apps project. */
export interface ArtifactEntry {
  /** Relative path of the artifact in the output directory. */
  path: string;
  /** Type of artifact (e.g., 'workflow', 'host_json', 'connections_json', 'parameters_json', 'env_file'). */
  artifact_type: string;
  /** File size in bytes, if known. */
  size_bytes?: number | null;
}

/** Manifest of all generated output artifacts. */
export interface ArtifactManifest {
  /** List of generated artifacts. */
  artifacts: ArtifactEntry[];
  /** Root output directory path. */
  output_directory: string;
  /** Input mode that produced these artifacts. */
  mode: InputMode;
}
