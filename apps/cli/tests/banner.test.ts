import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { showBanner } from "../src/ui/banner.js";

describe("showBanner", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it("should print the banner without errors", () => {
    expect(() => showBanner()).not.toThrow();
  });

  it("should print multiple lines", () => {
    showBanner();
    expect(consoleSpy).toHaveBeenCalled();
    expect(consoleSpy.mock.calls.length).toBeGreaterThan(5);
  });

  it("should include key banner content", () => {
    showBanner();
    const output = consoleSpy.mock.calls.map((call) => String(call[0] ?? "")).join("\n");
    expect(output).toContain("MuleSoft");
    expect(output).toContain("Logic Apps");
  });
});
