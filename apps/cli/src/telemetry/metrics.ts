/**
 * Custom OpenTelemetry metrics for the CLI.
 *
 * This module exposes shared metric instruments created from a shared meter.
 * Metrics are no-op when telemetry is not initialized or Azure Monitor is not configured.
 */

import { getMeter } from "./index.js";

const meter = getMeter();

// ---------------------------------------------------------------------------
// Command Metrics
// ---------------------------------------------------------------------------

/**
 * Total CLI commands executed.
 */
export const commandsExecuted = meter.createCounter("m2la.cli.commands", {
  description: "Total CLI commands executed",
  unit: "1",
});

/**
 * CLI command execution duration in milliseconds.
 */
export const commandDuration = meter.createHistogram("m2la.cli.command.duration_ms", {
  description: "CLI command execution duration in milliseconds",
  unit: "ms",
});

// ---------------------------------------------------------------------------
// Upload Metrics
// ---------------------------------------------------------------------------

/**
 * Total bytes uploaded to backend (file sizes).
 */
export const uploadBytes = meter.createCounter("m2la.cli.upload.bytes", {
  description: "Total bytes uploaded to backend",
  unit: "byte",
});

// ---------------------------------------------------------------------------
// API Client Metrics
// ---------------------------------------------------------------------------

/**
 * Backend API call latency in milliseconds.
 */
export const apiLatency = meter.createHistogram("m2la.cli.api.latency_ms", {
  description: "Backend API call latency in milliseconds",
  unit: "ms",
});

/**
 * Total API calls made to backend.
 */
export const apiCalls = meter.createCounter("m2la.cli.api.calls", {
  description: "Total API calls made to backend",
  unit: "1",
});

/**
 * API call errors (non-2xx responses or network failures).
 */
export const apiErrors = meter.createCounter("m2la.cli.api.errors", {
  description: "API call errors",
  unit: "1",
});
