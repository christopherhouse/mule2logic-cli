/**
 * Backend API client.
 * Communicates with the migration platform backend via HTTP.
 * Uses multipart/form-data to upload project zips and single-flow XML files.
 */
import type {
  AnalyzeResponse,
  TransformResponse,
  ValidationReport,
} from "@m2la/contracts";
import { CliError } from "../ui/errors.js";
import type { PackageResult } from "./project-packager.js";

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
  async analyze(
    pkg: PackageResult,
    mode?: string,
  ): Promise<AnalyzeResponse> {
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

    const headers: Record<string, string> = {};
    if (this.apiToken) {
      headers["x-api-token"] = this.apiToken;
    }

    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers,
        body: formData,
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
  }
}
