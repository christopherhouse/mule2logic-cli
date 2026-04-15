/**
 * Backend API client.
 * Communicates with the migration platform backend via HTTP.
 * Uses multipart/form-data to upload project zips and single-flow XML files.
 */
import type { AnalyzeResponse, TransformResponse, ValidationReport } from "@m2la/contracts";
import { CliError } from "../ui/errors.js";
import type { PackageResult } from "./project-packager.js";
import { withSpan, getPropagationHeaders } from "../telemetry/index.js";
import { apiLatency, apiCalls, apiErrors } from "../telemetry/metrics.js";

/** Streaming event from the backend. */
export interface StreamingEvent {
  event_type: string;
  timestamp: string;
  correlation_id: string;
  agent_name: string | null;
  message: string | null;
  data: Record<string, unknown>;
}

/** API client for the migration backend. */
export class ApiClient {
  private readonly baseUrl: string;
  private readonly apiToken?: string;

  constructor(backendUrl: string, apiToken?: string) {
    // Ensure no trailing slash
    this.baseUrl = backendUrl.replace(/\/+$/, "");
    this.apiToken = apiToken;
  }

  /**
   * Send an analyze request with an uploaded project or flow file.
   */
  async analyze(pkg: PackageResult, mode?: string): Promise<AnalyzeResponse> {
    const formData = this.buildFormData(pkg);
    if (mode) {
      formData.append("mode", mode);
    }
    return this.postMultipart<AnalyzeResponse>("/analyze", formData);
  }

  /**
   * Send a transform request with an uploaded project or flow file.
   */
  async transform(
    pkg: PackageResult,
    mode?: string,
    outputDirectory?: string,
  ): Promise<TransformResponse> {
    const formData = this.buildFormData(pkg);
    if (mode) {
      formData.append("mode", mode);
    }
    if (outputDirectory) {
      formData.append("output_directory", outputDirectory);
    }
    return this.postMultipart<TransformResponse>("/transform", formData);
  }

  /**
   * Send a streaming transform request with HTTP chunked transfer encoding.
   * Returns an async generator that yields events as they arrive.
   */
  async *transformStreaming(
    pkg: PackageResult,
    mode?: string,
    outputDirectory?: string,
  ): AsyncGenerator<StreamingEvent, void, unknown> {
    const formData = this.buildFormData(pkg);
    if (mode) {
      formData.append("mode", mode);
    }
    if (outputDirectory) {
      formData.append("output_directory", outputDirectory);
    }

    const path = "/transform/stream";
    const url = `${this.baseUrl}${path}`;

    // Build headers with API token and distributed tracing propagation
    const headers: Record<string, string> = {};
    if (this.apiToken) {
      headers["x-api-token"] = this.apiToken;
    }
    Object.assign(headers, getPropagationHeaders());

    // Fetch the streaming response, recording telemetry the same way as postMultipart
    const response = await withSpan(
      "m2la.cli.api.request",
      async (span) => {
        span.setAttribute("http.method", "POST");
        span.setAttribute("http.url", url);
        span.setAttribute("http.target", path);

        const startTime = Date.now();
        let res: Response;

        try {
          apiCalls.add(1, { endpoint: path, method: "POST" });
          res = await fetch(url, {
            method: "POST",
            headers,
            body: formData,
          });
        } catch (error) {
          const duration = Date.now() - startTime;
          apiLatency.record(duration, { endpoint: path, status: "error" });
          apiErrors.add(1, { endpoint: path, error_type: "connection_failed" });

          const message = error instanceof Error ? error.message : "Connection failed";
          throw new CliError(
            "BACKEND_UNREACHABLE",
            `Cannot connect to backend at ${this.baseUrl}: ${message}`,
            `Ensure the backend is running at ${this.baseUrl}.`,
          );
        }

        const duration = Date.now() - startTime;
        apiLatency.record(duration, { endpoint: path, status: String(res.status) });
        span.setAttribute("http.status_code", res.status);

        if (!res.ok) {
          apiErrors.add(1, { endpoint: path, error_type: `http_${res.status}` });

          if (res.status === 401) {
            throw new CliError(
              "UNAUTHORIZED",
              "Backend rejected the request — invalid or missing API token.",
              "Set the M2LA_API_TOKEN environment variable or pass --api-token <token>.",
            );
          }

          throw new CliError(
            "BACKEND_ERROR",
            `Backend returned ${res.status} ${res.statusText}`,
            "Check backend logs for details.",
          );
        }

        if (!res.body) {
          throw new CliError(
            "BACKEND_ERROR",
            "Backend response has no body",
            "This should not happen with streaming responses.",
          );
        }

        return res;
      },
      { "api.endpoint": path },
    );

    // Parse NDJSON stream (newline-delimited JSON)
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines (separated by newlines)
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          try {
            const event = JSON.parse(trimmed) as StreamingEvent;
            yield event;
          } catch (parseError) {
            console.warn(`Failed to parse streaming event: ${trimmed}`);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Send a validate request with an uploaded output artifacts zip.
   */
  async validate(pkg: PackageResult): Promise<ValidationReport> {
    const formData = this.buildFormData(pkg);
    return this.postMultipart<ValidationReport>("/validate", formData);
  }

  /**
   * Build a FormData with the file from a PackageResult.
   */
  private buildFormData(pkg: PackageResult): FormData {
    const formData = new FormData();
    const blob = new Blob([new Uint8Array(pkg.buffer)], { type: pkg.contentType });
    formData.append("file", blob, pkg.filename);
    return formData;
  }

  /**
   * Make a multipart POST request to the backend.
   */
  private async postMultipart<T>(path: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    return withSpan(
      "m2la.cli.api.request",
      async (span) => {
        span.setAttribute("http.method", "POST");
        span.setAttribute("http.url", url);
        span.setAttribute("http.target", path);

        const headers: Record<string, string> = {};
        if (this.apiToken) {
          headers["x-api-token"] = this.apiToken;
        }

        // Inject trace propagation headers for distributed tracing
        const propagationHeaders = getPropagationHeaders();
        Object.assign(headers, propagationHeaders);

        const startTime = Date.now();
        let response: Response;

        try {
          apiCalls.add(1, { endpoint: path, method: "POST" });

          response = await fetch(url, {
            method: "POST",
            headers,
            body: formData,
          });
        } catch (error) {
          const duration = Date.now() - startTime;
          apiLatency.record(duration, { endpoint: path, status: "error" });
          apiErrors.add(1, { endpoint: path, error_type: "connection_failed" });

          const message = error instanceof Error ? error.message : "Connection failed";
          throw new CliError(
            "BACKEND_UNREACHABLE",
            `Cannot connect to backend at ${this.baseUrl}: ${message}`,
            `Ensure the backend is running at ${this.baseUrl}. You can configure the URL with --backend-url or M2LA_BACKEND_URL env var.`,
          );
        }

        const duration = Date.now() - startTime;
        apiLatency.record(duration, { endpoint: path, status: String(response.status) });

        span.setAttribute("http.status_code", response.status);

        if (!response.ok) {
          apiErrors.add(1, { endpoint: path, error_type: `http_${response.status}` });

          if (response.status === 401) {
            throw new CliError(
              "UNAUTHORIZED",
              "Backend rejected the request — invalid or missing API token.",
              "Set the M2LA_API_TOKEN environment variable or pass --api-token <token>.",
            );
          }

          let detail = "";
          try {
            const errorBody = (await response.json()) as Record<string, unknown>;
            detail = typeof errorBody.detail === "string" ? `: ${errorBody.detail}` : "";
          } catch {
            // ignore json parse errors on error responses
          }

          throw new CliError(
            "BACKEND_ERROR",
            `Backend returned ${response.status} ${response.statusText}${detail}`,
            "Check backend logs for details.",
          );
        }

        return (await response.json()) as T;
      },
      {
        "api.endpoint": path,
      },
    );
  }
}
