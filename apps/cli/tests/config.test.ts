import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { getConfig } from "../src/config.js";

describe("getConfig", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("should return default backend URL when no env var or override", () => {
    delete process.env.M2LA_BACKEND_URL;
    const config = getConfig();
    expect(config.backendUrl).toBe("http://localhost:8000");
  });

  it("should use M2LA_BACKEND_URL env var", () => {
    process.env.M2LA_BACKEND_URL = "http://custom:9000";
    const config = getConfig();
    expect(config.backendUrl).toBe("http://custom:9000");
  });

  it("should prefer override over env var", () => {
    process.env.M2LA_BACKEND_URL = "http://custom:9000";
    const config = getConfig({ backendUrl: "http://override:8080" });
    expect(config.backendUrl).toBe("http://override:8080");
  });

  it("should default verbose to false", () => {
    delete process.env.M2LA_VERBOSE;
    const config = getConfig();
    expect(config.verbose).toBe(false);
  });

  it("should enable verbose from env var", () => {
    process.env.M2LA_VERBOSE = "true";
    const config = getConfig();
    expect(config.verbose).toBe(true);
  });
});
