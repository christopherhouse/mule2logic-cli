/**
 * UI output helpers for consistent, colorful CLI output.
 */
import chalk from "chalk";
import ora from "ora";
import type {
  AnalyzeResponse,
  InputMode,
  TransformResponse,
  ValidationReport,
} from "@m2la/contracts";

/**
 * Print a styled section header.
 */
export function printHeader(emoji: string, text: string): void {
  console.log();
  console.log(chalk.bold.cyan(`  ${emoji}  ${text}`));
}

/**
 * Print the detected input mode with appropriate icon and styling.
 */
export function printModeIndicator(mode: InputMode): void {
  console.log();
  if (mode === "project") {
    console.log(chalk.bold.blue("  📁  Project Mode detected"));
  } else {
    console.log(chalk.bold.blue("  📄  Single-Flow Mode detected"));
    console.log(
      chalk.yellow("  ⚠️   External references (connector configs, properties) may be unavailable"),
    );
  }
}

/**
 * Print a success message.
 */
export function printSuccess(message: string): void {
  console.log(chalk.green(`  ✅  ${message}`));
}

/**
 * Print a warning message.
 */
export function printWarning(message: string): void {
  console.log(chalk.yellow(`  ⚠️   ${message}`));
}

/**
 * Print an error message (non-fatal, for display within results).
 */
export function printErrorMessage(message: string): void {
  console.log(chalk.red(`  ❌  ${message}`));
}

/**
 * Create an ora spinner with consistent styling.
 */
export function createSpinner(text: string): ReturnType<typeof ora> {
  return ora({
    text: `  ${text}`,
    color: "cyan",
    spinner: "dots",
  });
}

/**
 * Print a formatted analysis result summary.
 */
export function printAnalysisResult(response: AnalyzeResponse): void {
  console.log();
  console.log(chalk.bold.white("  📊  Summary:"));

  if (response.project_name) {
    console.log(chalk.white(`      Project: ${response.project_name}`));
  }

  console.log(chalk.white(`      Flows analyzed: ${response.flows.length}`));
  console.log(chalk.green(`      Supported constructs: ${response.overall_constructs.supported}`));

  if (response.overall_constructs.unsupported > 0) {
    console.log(
      chalk.yellow(`      Unsupported constructs: ${response.overall_constructs.unsupported}`),
    );
  }

  if (response.overall_constructs.partial > 0) {
    console.log(chalk.yellow(`      Partially supported: ${response.overall_constructs.partial}`));
  }

  if (response.gaps.length > 0) {
    console.log(chalk.yellow(`      Migration gaps: ${response.gaps.length}`));
  }

  if (response.warnings.length > 0) {
    console.log(chalk.yellow(`      Warnings: ${response.warnings.length}`));
  }

  console.log();
}

/**
 * Print a formatted transformation result summary.
 */
export function printTransformResult(response: TransformResponse): void {
  console.log();
  console.log(chalk.bold.white("  📦  Transform Summary:"));

  if (response.project_name) {
    console.log(chalk.white(`      Project: ${response.project_name}`));
  }

  console.log(chalk.white(`      Artifacts generated: ${response.artifacts.artifacts.length}`));
  console.log(chalk.white(`      Output directory: ${response.artifacts.output_directory}`));

  if (response.gaps.length > 0) {
    console.log(chalk.yellow(`      Migration gaps: ${response.gaps.length}`));
  }

  if (response.warnings.length > 0) {
    console.log(chalk.yellow(`      Warnings: ${response.warnings.length}`));
  }

  console.log();
}

/**
 * Print a formatted validation result summary.
 */
export function printValidationResult(report: ValidationReport): void {
  console.log();
  if (report.valid) {
    console.log(chalk.bold.green("  ✅  Validation Passed"));
  } else {
    console.log(chalk.bold.red("  ❌  Validation Failed"));
  }

  console.log(chalk.white(`      Artifacts validated: ${report.artifacts_validated}`));
  console.log(chalk.white(`      Issues found: ${report.issues.length}`));

  if (report.issues.length > 0) {
    console.log();
    for (const issue of report.issues) {
      const icon = issue.severity === "error" || issue.severity === "critical" ? "❌" : "⚠️";
      const colorFn =
        issue.severity === "error" || issue.severity === "critical" ? chalk.red : chalk.yellow;
      const location = issue.artifact_path ? ` (${issue.artifact_path})` : "";
      console.log(colorFn(`      ${icon} [${issue.rule_id}] ${issue.message}${location}`));
    }
  }

  console.log();
}
