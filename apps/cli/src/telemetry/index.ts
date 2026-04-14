/**
 * OpenTelemetry instrumentation for CLI.
 *
 * Provides two modes:
 *
 * 1. **Azure Monitor** — when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set,
 *    uses @azure/monitor-opentelemetry to auto-instrument and export traces,
 *    metrics, and logs to Application Insights.
 *
 * 2. **Local dev** — when the connection string is absent, telemetry is
 *    disabled (no-op) to keep development lightweight.
 *
 * Call `initTelemetry()` once at CLI startup before executing commands.
 */

import { trace, metrics, context, propagation, type Span } from "@opentelemetry/api";

let telemetryInitialized = false;
let telemetryEnabled = false;

/**
 * Bootstrap OpenTelemetry instrumentation.
 *
 * Call this once at CLI startup.
 */
export async function initTelemetry(): Promise<void> {
  if (telemetryInitialized) {
    return;
  }
  telemetryInitialized = true;

  const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;

  if (connectionString) {
    await initAzureMonitor(connectionString);
    telemetryEnabled = true;
  } else {
    // No connection string = no-op telemetry (local dev mode)
    telemetryEnabled = false;
  }
}

/**
 * Configure Azure Monitor OpenTelemetry distro.
 */
async function initAzureMonitor(connectionString: string): Promise<void> {
  try {
    const { useAzureMonitor } = await import("@azure/monitor-opentelemetry");

    // Use environment variables for resource attributes per Azure Monitor docs
    process.env.OTEL_SERVICE_NAME = process.env.OTEL_SERVICE_NAME || "m2la-cli";

    useAzureMonitor({
      azureMonitorExporterOptions: {
        connectionString,
      },
    });

    console.log("[telemetry] Azure Monitor OpenTelemetry configured");

    // Emit a startup span so we know the pipeline is healthy
    const tracer = trace.getTracer("m2la-cli");
    const span = tracer.startSpan("m2la.cli.startup");
    span.end();
  } catch (error) {
    console.warn("[telemetry] Failed to initialize Azure Monitor:", error);
    telemetryEnabled = false;
  }
}

/**
 * Get a tracer instance for creating spans.
 */
export function getTracer() {
  return trace.getTracer("m2la-cli", "0.1.0");
}

/**
 * Get a meter instance for creating metrics.
 */
export function getMeter() {
  return metrics.getMeter("m2la-cli", "0.1.0");
}

/**
 * Check if telemetry is enabled.
 */
export function isTelemetryEnabled(): boolean {
  return telemetryEnabled;
}

/**
 * Create and start a new span.
 *
 * @param name - Span name
 * @param attributes - Optional span attributes
 * @returns Span instance
 */
export function startSpan(name: string, attributes?: Record<string, string | number | boolean>): Span {
  const tracer = getTracer();
  const span = tracer.startSpan(name, {
    attributes,
  });
  return span;
}

/**
 * Run a function within a new span context.
 *
 * @param name - Span name
 * @param fn - Function to run within span context
 * @param attributes - Optional span attributes
 * @returns Function return value
 */
export async function withSpan<T>(
  name: string,
  fn: (span: Span) => Promise<T>,
  attributes?: Record<string, string | number | boolean>,
): Promise<T> {
  const tracer = getTracer();
  return tracer.startActiveSpan(name, { attributes }, async (span) => {
    try {
      const result = await fn(span);
      span.setStatus({ code: 1 }); // OK status
      return result;
    } catch (error) {
      span.setStatus({
        code: 2, // ERROR status
        message: error instanceof Error ? error.message : String(error),
      });
      span.recordException(error as Error);
      throw error;
    } finally {
      span.end();
    }
  });
}

/**
 * Get propagation headers for outbound HTTP requests.
 *
 * This enables distributed tracing by injecting trace context into HTTP headers.
 *
 * @returns Headers object with trace context (traceparent, etc.)
 */
export function getPropagationHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  propagation.inject(context.active(), headers);
  return headers;
}
