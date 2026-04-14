/**
 * Tests for OpenTelemetry instrumentation.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  initTelemetry,
  getTracer,
  getMeter,
  isTelemetryEnabled,
  startSpan,
  withSpan,
  getPropagationHeaders,
} from "../src/telemetry/index.js";
import { trace } from "@opentelemetry/api";

describe("Telemetry", () => {
  const originalEnv = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;

  beforeEach(() => {
    // Reset environment
    delete process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;
  });

  afterEach(() => {
    // Restore original environment
    if (originalEnv) {
      process.env.APPLICATIONINSIGHTS_CONNECTION_STRING = originalEnv;
    } else {
      delete process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;
    }
  });

  describe("initTelemetry", () => {
    it("should initialize without connection string (local dev mode)", async () => {
      await initTelemetry();
      expect(isTelemetryEnabled()).toBe(false);
    });

    it("should not reinitialize on subsequent calls", async () => {
      await initTelemetry();
      const enabled1 = isTelemetryEnabled();
      await initTelemetry();
      const enabled2 = isTelemetryEnabled();
      expect(enabled1).toBe(enabled2);
    });

    it("should handle invalid connection string gracefully", async () => {
      process.env.APPLICATIONINSIGHTS_CONNECTION_STRING = "invalid-connection-string";
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      await initTelemetry();

      // Should fallback to no-op mode
      expect(isTelemetryEnabled()).toBe(false);

      consoleWarnSpy.mockRestore();
    });
  });

  describe("getTracer", () => {
    it("should return a tracer instance", () => {
      const tracer = getTracer();
      expect(tracer).toBeDefined();
      expect(typeof tracer.startSpan).toBe("function");
    });
  });

  describe("getMeter", () => {
    it("should return a meter instance", () => {
      const meter = getMeter();
      expect(meter).toBeDefined();
      expect(typeof meter.createCounter).toBe("function");
      expect(typeof meter.createHistogram).toBe("function");
    });
  });

  describe("startSpan", () => {
    it("should create and return a span", () => {
      const span = startSpan("test.span");
      expect(span).toBeDefined();
      expect(typeof span.end).toBe("function");
      span.end();
    });

    it("should create span with attributes", () => {
      const span = startSpan("test.span.with.attributes", {
        "test.key": "test-value",
        "test.number": 42,
        "test.boolean": true,
      });
      expect(span).toBeDefined();
      span.end();
    });
  });

  describe("withSpan", () => {
    it("should execute function within span context", async () => {
      let spanReceived = false;
      await withSpan("test.span", async (span) => {
        spanReceived = true;
        expect(span).toBeDefined();
        expect(typeof span.setAttribute).toBe("function");
      });
      expect(spanReceived).toBe(true);
    });

    it("should return function result", async () => {
      const result = await withSpan("test.span", async () => {
        return "test-result";
      });
      expect(result).toBe("test-result");
    });

    it("should set OK status on success", async () => {
      const mockSpan = {
        setStatus: vi.fn(),
        end: vi.fn(),
        setAttribute: vi.fn(),
        recordException: vi.fn(),
      };

      const tracerMock = {
        startActiveSpan: vi.fn((name, options, fn) => {
          return fn(mockSpan);
        }),
      };

      vi.spyOn(trace, "getTracer").mockReturnValue(tracerMock as any);

      await withSpan("test.span", async () => {
        return "success";
      });

      expect(mockSpan.setStatus).toHaveBeenCalledWith({ code: 1 });
      expect(mockSpan.end).toHaveBeenCalled();
    });

    it("should set ERROR status and record exception on failure", async () => {
      const testError = new Error("test error");
      const mockSpan = {
        setStatus: vi.fn(),
        end: vi.fn(),
        setAttribute: vi.fn(),
        recordException: vi.fn(),
      };

      const tracerMock = {
        startActiveSpan: vi.fn((name, options, fn) => {
          return fn(mockSpan);
        }),
      };

      vi.spyOn(trace, "getTracer").mockReturnValue(tracerMock as any);

      await expect(
        withSpan("test.span", async () => {
          throw testError;
        }),
      ).rejects.toThrow("test error");

      expect(mockSpan.setStatus).toHaveBeenCalledWith({
        code: 2,
        message: "test error",
      });
      expect(mockSpan.recordException).toHaveBeenCalledWith(testError);
      expect(mockSpan.end).toHaveBeenCalled();
    });

    it("should accept span attributes", async () => {
      await withSpan(
        "test.span",
        async () => {
          return "test";
        },
        {
          "test.attr": "value",
        },
      );
      // No assertion needed - just checking it doesn't throw
    });
  });

  describe("getPropagationHeaders", () => {
    it("should return headers object", () => {
      const headers = getPropagationHeaders();
      expect(headers).toBeDefined();
      expect(typeof headers).toBe("object");
    });

    it("should inject trace context when in active span", async () => {
      await withSpan("test.span", async () => {
        const headers = getPropagationHeaders();
        // In a real span context, we'd expect propagation headers
        // In test mode with no-op tracer, headers may be empty
        expect(headers).toBeDefined();
      });
    });
  });
});

describe("Telemetry Metrics", () => {
  it("should export metrics instruments", async () => {
    const { commandsExecuted, commandDuration, uploadBytes, apiLatency, apiCalls, apiErrors } =
      await import("../src/telemetry/metrics.js");

    expect(commandsExecuted).toBeDefined();
    expect(commandDuration).toBeDefined();
    expect(uploadBytes).toBeDefined();
    expect(apiLatency).toBeDefined();
    expect(apiCalls).toBeDefined();
    expect(apiErrors).toBeDefined();
  });

  it("should allow recording metrics", async () => {
    const { commandsExecuted, commandDuration } = await import("../src/telemetry/metrics.js");

    // These should not throw even in no-op mode
    commandsExecuted.add(1, { command: "test", status: "success" });
    commandDuration.record(100, { command: "test" });
  });
});
