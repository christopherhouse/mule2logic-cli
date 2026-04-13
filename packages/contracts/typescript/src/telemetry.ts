/**
 * Telemetry correlation metadata for end-to-end observability (spec §9).
 */

/** Telemetry correlation metadata propagated across CLI, API, and services. */
export interface TelemetryContext {
  /** OpenTelemetry trace ID. */
  trace_id: string;
  /** OpenTelemetry span ID. */
  span_id: string;
  /** Platform correlation ID (UUID). */
  correlation_id: string;
  /** Parent span ID for nested operations. */
  parent_span_id?: string | null;
}
