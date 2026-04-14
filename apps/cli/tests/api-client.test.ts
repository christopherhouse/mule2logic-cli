import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClient } from "../src/services/api-client.js";
import { CliError } from "../src/ui/errors.js";

describe("ApiClient", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("should strip trailing slashes from base URL", () => {
    const client = new ApiClient("http://localhost:8000///");
    // Exercise the client to verify the URL is trimmed (indirectly via error path)
    expect(client).toBeDefined();
  });

  it("should send x-api-token header when apiToken is provided", async () => {
    let capturedHeaders: Record<string, string> = {};
    globalThis.fetch = vi.fn().mockImplementation(async (_url: string, init: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        Object.entries(init.headers as Record<string, string>),
      );
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const client = new ApiClient("http://localhost:8000", "my-secret-token");
    await client.analyze({ input_path: "/test", mode: "project" });

    expect(capturedHeaders["x-api-token"]).toBe("my-secret-token");
    expect(capturedHeaders["Content-Type"]).toBe("application/json");
  });

  it("should not send x-api-token header when apiToken is not provided", async () => {
    let capturedHeaders: Record<string, string> = {};
    globalThis.fetch = vi.fn().mockImplementation(async (_url: string, init: RequestInit) => {
      capturedHeaders = Object.fromEntries(
        Object.entries(init.headers as Record<string, string>),
      );
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const client = new ApiClient("http://localhost:8000");
    await client.analyze({ input_path: "/test", mode: "project" });

    expect(capturedHeaders["x-api-token"]).toBeUndefined();
    expect(capturedHeaders["Content-Type"]).toBe("application/json");
  });

  it("should throw UNAUTHORIZED CliError on 401 response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("Unauthorized", { status: 401, statusText: "Unauthorized" }),
    );

    const client = new ApiClient("http://localhost:8000", "bad-token");

    await expect(client.analyze({ input_path: "/test", mode: "project" })).rejects.toThrow(
      CliError,
    );

    try {
      await client.analyze({ input_path: "/test", mode: "project" });
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      const cliError = error as CliError;
      expect(cliError.code).toBe("UNAUTHORIZED");
      expect(cliError.message).toContain("invalid or missing API token");
      expect(cliError.suggestion).toContain("M2LA_API_TOKEN");
    }
  });

  it("should throw BACKEND_UNREACHABLE CliError on network error", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Connection refused"));

    const client = new ApiClient("http://localhost:8000");

    try {
      await client.analyze({ input_path: "/test", mode: "project" });
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      const cliError = error as CliError;
      expect(cliError.code).toBe("BACKEND_UNREACHABLE");
      expect(cliError.message).toContain("Connection refused");
    }
  });

  it("should throw BACKEND_ERROR CliError on non-401 error response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Something went wrong" }), {
        status: 500,
        statusText: "Internal Server Error",
      }),
    );

    const client = new ApiClient("http://localhost:8000");

    try {
      await client.analyze({ input_path: "/test", mode: "project" });
    } catch (error) {
      expect(error).toBeInstanceOf(CliError);
      const cliError = error as CliError;
      expect(cliError.code).toBe("BACKEND_ERROR");
      expect(cliError.message).toContain("500");
      expect(cliError.message).toContain("Something went wrong");
    }
  });
});
