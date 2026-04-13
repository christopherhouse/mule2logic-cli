import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type {
  AnalyzeRequest,
  AnalyzeResponse,
  TransformRequest,
  TransformResponse,
  ValidationReport,
  InputMode,
  Severity,
  GapCategory,
} from "../src/index.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const examplesDir = resolve(__dirname, "../../examples");

function loadExample(filename: string): unknown {
  return JSON.parse(readFileSync(resolve(examplesDir, filename), "utf-8"));
}

describe("TypeScript contract types", () => {
  describe("enum type values", () => {
    it("InputMode accepts valid values", () => {
      const project: InputMode = "project";
      const singleFlow: InputMode = "single_flow";
      expect(project).toBe("project");
      expect(singleFlow).toBe("single_flow");
    });

    it("Severity accepts valid values", () => {
      const values: Severity[] = ["info", "warning", "error", "critical"];
      expect(values).toHaveLength(4);
    });

    it("GapCategory accepts valid values", () => {
      const values: GapCategory[] = [
        "unsupported_construct",
        "unresolvable_reference",
        "partial_support",
        "connector_mismatch",
        "dataweave_complexity",
      ];
      expect(values).toHaveLength(5);
    });
  });

  describe("example payloads conform to types", () => {
    it("analyze_request_project.json conforms to AnalyzeRequest", () => {
      const data = loadExample("analyze_request_project.json") as AnalyzeRequest;
      expect(data.input_path).toBeDefined();
      expect(typeof data.input_path).toBe("string");
      expect(data.mode).toBe("project");
    });

    it("analyze_request_single_flow.json conforms to AnalyzeRequest", () => {
      const data = loadExample("analyze_request_single_flow.json") as AnalyzeRequest;
      expect(data.input_path).toBeDefined();
      expect(data.mode).toBe("single_flow");
    });

    it("analyze_response_project.json conforms to AnalyzeResponse", () => {
      const data = loadExample("analyze_response_project.json") as AnalyzeResponse;
      expect(data.mode).toBe("project");
      expect(data.flows).toBeInstanceOf(Array);
      expect(data.flows.length).toBeGreaterThan(0);
      expect(data.overall_constructs).toBeDefined();
      expect(data.telemetry).toBeDefined();
      expect(data.telemetry.trace_id).toBeDefined();
    });

    it("analyze_response_single_flow.json conforms to AnalyzeResponse", () => {
      const data = loadExample("analyze_response_single_flow.json") as AnalyzeResponse;
      expect(data.mode).toBe("single_flow");
      expect(data.project_name).toBeNull();
      expect(data.warnings.length).toBeGreaterThan(0);
    });

    it("transform_request_project.json conforms to TransformRequest", () => {
      const data = loadExample("transform_request_project.json") as TransformRequest;
      expect(data.input_path).toBeDefined();
      expect(data.mode).toBe("project");
    });

    it("transform_response_project.json conforms to TransformResponse", () => {
      const data = loadExample("transform_response_project.json") as TransformResponse;
      expect(data.mode).toBe("project");
      expect(data.artifacts).toBeDefined();
      expect(data.artifacts.artifacts).toBeInstanceOf(Array);
      expect(data.artifacts.artifacts.length).toBeGreaterThan(0);
    });

    it("transform_response_single_flow.json conforms to TransformResponse", () => {
      const data = loadExample("transform_response_single_flow.json") as TransformResponse;
      expect(data.mode).toBe("single_flow");
      expect(data.artifacts.artifacts).toHaveLength(1);
      expect(data.artifacts.artifacts[0].artifact_type).toBe("workflow");
    });

    it("validation_report.json conforms to ValidationReport", () => {
      const data = loadExample("validation_report.json") as ValidationReport;
      expect(typeof data.valid).toBe("boolean");
      expect(data.issues).toBeInstanceOf(Array);
      expect(data.artifacts_validated).toBeGreaterThan(0);
      expect(data.telemetry).toBeDefined();
    });
  });
});
