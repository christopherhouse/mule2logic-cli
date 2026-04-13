/**
 * Backend API client.
 * Communicates with the migration platform backend via HTTP.
 */
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  TransformRequest,
  TransformResponse,
  ValidationReport,
} from "@m2la/contracts";
import { CliError } from "../ui/errors.js";

/** API client for the migration backend. */
export class ApiClient {
  private readonly baseUrl: string;

  constructor(backendUrl: string) {
    // Ensure no trailing slash
    this.baseUrl = backendUrl.replace(/\/+$/, "");
  }

  /**
   * Send an analyze request to the backend.
   */
  async analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
    return this.post<AnalyzeResponse>("/analyze", request);
  }

  /**
   * Send a transform request to the backend.
   */
  async transform(request: TransformRequest): Promise<TransformResponse> {
    return this.post<TransformResponse>("/transform", request);
  }

  /**
   * Send a validate request to the backend.
   */
  async validate(outputPath: string): Promise<ValidationReport> {
    return this.post<ValidationReport>("/validate", { output_path: outputPath });
  }

  /**
   * Make a POST request to the backend.
   */
  private async post<T>(path: string, body: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Connection failed";
      throw new CliError(
        "BACKEND_UNREACHABLE",
        `Cannot connect to backend at ${this.baseUrl}: ${message}`,
        `Ensure the backend is running at ${this.baseUrl}. You can configure the URL with --backend-url or M2LA_BACKEND_URL env var.`,
      );
    }

    if (!response.ok) {
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
  }
}
