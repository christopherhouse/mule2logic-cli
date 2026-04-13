import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type {
  AnalyzeResponse,
  InputMode,
  TransformResponse,
  ValidationReport,
} from "@m2la/contracts";
import {
  printHeader,
  printModeIndicator,
  printSuccess,
  printWarning,
  printErrorMessage,
  printAnalysisResult,
  printTransformResult,
  printValidationResult,
} from "../src/ui/output.js";

describe("UI output helpers", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it("printHeader should print styled header", () => {
    printHeader("🔍", "Analyzing project");
    expect(consoleSpy).toHaveBeenCalled();
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Analyzing project");
  });

  it("printModeIndicator should show Project Mode for 'project'", () => {
    printModeIndicator("project" as InputMode);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Project Mode");
  });

  it("printModeIndicator should show Single-Flow Mode for 'single_flow'", () => {
    printModeIndicator("single_flow" as InputMode);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Single-Flow Mode");
    expect(output).toContain("External references");
  });

  it("printSuccess should render without errors", () => {
    expect(() => printSuccess("Done")).not.toThrow();
  });

  it("printWarning should render without errors", () => {
    expect(() => printWarning("Watch out")).not.toThrow();
  });

  it("printErrorMessage should render without errors", () => {
    expect(() => printErrorMessage("Oops")).not.toThrow();
  });

  it("printAnalysisResult should display summary", () => {
    const response: AnalyzeResponse = {
      mode: "project",
      project_name: "test-project",
      flows: [
        {
          flow_name: "main",
          source_file: "main.xml",
          constructs: { supported: 5, unsupported: 1, partial: 0, details: {} },
          gaps: [],
          warnings: [],
        },
      ],
      overall_constructs: { supported: 5, unsupported: 1, partial: 0, details: {} },
      gaps: [],
      warnings: [],
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printAnalysisResult(response);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Summary");
    expect(output).toContain("test-project");
    expect(output).toContain("1");
  });

  it("printTransformResult should display summary", () => {
    const response: TransformResponse = {
      mode: "project",
      project_name: "test-project",
      artifacts: {
        artifacts: [{ path: "workflow.json", artifact_type: "workflow" }],
        output_directory: "./output",
        mode: "project",
      },
      gaps: [],
      warnings: [],
      constructs: { supported: 5, unsupported: 0, partial: 0, details: {} },
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printTransformResult(response);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Transform Summary");
    expect(output).toContain("1");
  });

  it("printValidationResult should show passed state", () => {
    const report: ValidationReport = {
      valid: true,
      issues: [],
      artifacts_validated: 3,
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printValidationResult(report);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Validation Passed");
  });

  it("printValidationResult should show failed state with issues", () => {
    const report: ValidationReport = {
      valid: false,
      issues: [
        {
          rule_id: "SCHEMA_001",
          message: "Invalid schema",
          severity: "error",
          artifact_path: "workflow.json",
        },
      ],
      artifacts_validated: 1,
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printValidationResult(report);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Validation Failed");
    expect(output).toContain("SCHEMA_001");
  });
});
