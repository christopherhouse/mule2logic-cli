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
  printStreamingProgress,
  printStreamingToolCall,
  printStreamingComplete,
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

  it("printAnalysisResult should display warnings and gaps when present", () => {
    const response: AnalyzeResponse = {
      mode: "project",
      project_name: "test-project",
      flows: [],
      overall_constructs: { supported: 3, unsupported: 2, partial: 1, details: {} },
      gaps: [
        {
          construct_name: "mule-http-connector",
          source_location: "flow.xml:42",
          category: "unsupported_construct",
          severity: "warning",
          message: "HTTP connector not supported",
          suggested_workaround: "Use Azure API Management",
        },
      ],
      warnings: [
        {
          code: "MISSING_CONFIG",
          message: "Connector configuration not found",
          severity: "warning",
          source_location: "flow.xml:10",
        },
      ],
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printAnalysisResult(response);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Warnings:");
    expect(output).toContain("MISSING_CONFIG");
    expect(output).toContain("Connector configuration not found");
    expect(output).toContain("Migration Gaps:");
    expect(output).toContain("mule-http-connector");
    expect(output).toContain("Use Azure API Management");
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

  it("printTransformResult should display warnings and gaps when present", () => {
    const response: TransformResponse = {
      mode: "project",
      project_name: "test-project",
      artifacts: {
        artifacts: [{ path: "workflow.json", artifact_type: "workflow" }],
        output_directory: "./output",
        mode: "project",
      },
      gaps: [
        {
          construct_name: "batch-processing",
          source_location: "batch.xml:15",
          category: "unsupported_construct",
          severity: "error",
          message: "Batch processing not supported in Logic Apps",
        },
      ],
      warnings: [
        {
          code: "AGENT_REASONING",
          message: "[TransformerAgent] Using HTTP connector for API calls",
          severity: "info",
        },
      ],
      constructs: { supported: 8, unsupported: 2, partial: 1, details: {} },
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printTransformResult(response);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("Warnings:");
    expect(output).toContain("AGENT_REASONING");
    expect(output).toContain("Migration Gaps:");
    expect(output).toContain("batch-processing");
  });

  it("printTransformResult should show error message when no artifacts generated", () => {
    const response: TransformResponse = {
      mode: "project",
      project_name: "test-project",
      artifacts: {
        artifacts: [],
        output_directory: "./output",
        mode: "project",
      },
      gaps: [],
      warnings: [
        {
          code: "PARSE_ERROR",
          message: "Failed to parse flow XML",
          severity: "error",
        },
      ],
      constructs: { supported: 0, unsupported: 0, partial: 0, details: {} },
      telemetry: { trace_id: "t1", span_id: "s1", correlation_id: "c1" },
    };

    printTransformResult(response);
    const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
    expect(output).toContain("No artifacts were generated");
    expect(output).toContain("transformation pipeline encountered errors");
    expect(output).toContain("Check the warnings and gaps above");
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

describe("Streaming UI helpers", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  describe("printStreamingProgress", () => {
    it("should show started state with agent name", () => {
      printStreamingProgress("AnalyzerAgent", "started");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("AnalyzerAgent");
      expect(output).toContain("started");
    });

    it("should show progress state with message", () => {
      printStreamingProgress("PlannerAgent", "progress", undefined, "Processing flows");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("PlannerAgent");
      expect(output).toContain("Processing flows");
    });

    it("should show progress state without message", () => {
      printStreamingProgress("PlannerAgent", "progress");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("PlannerAgent");
    });

    it("should show completed state with success icon for success status", () => {
      printStreamingProgress("TransformerAgent", "completed", 2300, undefined, "success");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("TransformerAgent");
      expect(output).toContain("completed");
      expect(output).toContain("✅");
      expect(output).toContain("2.3s");
    });

    it("should show completed state with warning icon for partial status", () => {
      printStreamingProgress("ValidatorAgent", "completed", 1500, undefined, "partial");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("ValidatorAgent");
      expect(output).toContain("⚠️");
    });

    it("should show completed state with error icon for failure status", () => {
      printStreamingProgress("RepairAdvisorAgent", "completed", 800, undefined, "failure");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("RepairAdvisorAgent");
      expect(output).toContain("❌");
    });

    it("should show completed state without duration when not provided", () => {
      printStreamingProgress("AnalyzerAgent", "completed");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("AnalyzerAgent");
      expect(output).toContain("completed");
    });

    it("should show error state with agent name", () => {
      printStreamingProgress("TransformerAgent", "error");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("TransformerAgent");
      expect(output).toContain("failed");
    });
  });

  describe("printStreamingToolCall", () => {
    it("should display agent name and tool name", () => {
      printStreamingToolCall("AnalyzerAgent", "search_mulesoft_docs");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("AnalyzerAgent");
      expect(output).toContain("search_mulesoft_docs");
    });

    it("should include tool call indicator", () => {
      printStreamingToolCall("TransformerAgent", "fetch_logic_apps_doc");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("🔧");
    });

    it("should include arrow separator between agent and tool", () => {
      printStreamingToolCall("PlannerAgent", "parse_mule_flow");
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("→");
    });
  });

  describe("printStreamingComplete", () => {
    it("should show success message when overall status is success", () => {
      printStreamingComplete("success", 7500, 5);
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("✅");
      expect(output).toContain("7.5s");
      expect(output).toContain("5");
    });

    it("should show failure message when overall status is failure", () => {
      printStreamingComplete("failure", 3200, 2);
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("❌");
      expect(output).toContain("3.2s");
    });

    it("should show warning message for non-success/failure statuses", () => {
      printStreamingComplete("partial", 5000, 4);
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("⚠️");
      expect(output).toContain("5.0s");
    });

    it("should show agent count", () => {
      printStreamingComplete("success", 10000, 3);
      const output = consoleSpy.mock.calls.map((c) => String(c[0] ?? "")).join("\n");
      expect(output).toContain("3");
    });
  });
});
