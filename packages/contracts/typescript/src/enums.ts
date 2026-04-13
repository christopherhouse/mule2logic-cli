/**
 * Shared enumerations for the migration platform.
 * Values must match the Python StrEnum values exactly.
 */

/** Discriminator for project vs single-flow input mode. */
export type InputMode = "project" | "single_flow";

/** Severity levels for warnings, gaps, and validation issues. */
export type Severity = "info" | "warning" | "error" | "critical";

/** Categories for migration gaps. */
export type GapCategory =
  | "unsupported_construct"
  | "unresolvable_reference"
  | "partial_support"
  | "connector_mismatch"
  | "dataweave_complexity";

/** Categories for MuleSoft constructs (from spec §7). */
export type ConstructCategory =
  | "trigger"
  | "router"
  | "connector"
  | "error_handler"
  | "transform"
  | "scope"
  | "flow_control";
