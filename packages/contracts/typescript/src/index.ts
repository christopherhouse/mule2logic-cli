/**
 * Shared contracts for the MuleSoft to Logic Apps migration platform.
 *
 * This package provides TypeScript type definitions that mirror the Python
 * Pydantic models used by the backend API.
 */

// Enums
export type { InputMode, Severity, GapCategory, ConstructCategory } from "./enums.js";

// Telemetry
export type { TelemetryContext } from "./telemetry.js";

// Common models
export type { MigrationGap, ConstructCount, Warning, ArtifactEntry, ArtifactManifest } from "./common.js";

// Analyze
export type { AnalyzeRequest, FlowAnalysis, AnalyzeResponse } from "./analyze.js";

// Transform
export type { TransformRequest, TransformResponse } from "./transform.js";

// Validate
export type { ValidationIssue, ValidationReport } from "./validate.js";
