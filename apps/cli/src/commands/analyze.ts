/**
 * `analyze` command — analyzes a MuleSoft project or single flow.
 */
import { Command } from "commander";
import { detectInputMode } from "../services/input-detector.js";
import { validateProjectMode, validateSingleFlowMode } from "../services/input-validator.js";
import { packageProjectDir, packageSingleFlow } from "../services/project-packager.js";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printModeIndicator, printAnalysisResult, createSpinner } from "../ui/output.js";
import { handleError } from "../ui/errors.js";
import { withSpan } from "../telemetry/index.js";
import { commandsExecuted, commandDuration, uploadBytes } from "../telemetry/metrics.js";

/**
 * Create the analyze command.
 */
export function createAnalyzeCommand(): Command {
  return new Command("analyze")
    .description("Analyze a MuleSoft project or single flow for migration readiness")
    .argument("<inputPath>", "Path to MuleSoft project directory or single flow XML file")
    .action(async (inputPath: string, _options: unknown, cmd: Command) => {
      const startTime = Date.now();
      try {
        await withSpan(
          "m2la.cli.command.analyze",
          async (span) => {
            const parentOpts = cmd.parent?.opts() as
              | { backendUrl?: string; apiToken?: string }
              | undefined;
            const config = getConfig({
              backendUrl: parentOpts?.backendUrl,
              apiToken: parentOpts?.apiToken,
            });

            // Detect input mode
            const mode = await detectInputMode(inputPath);
            printModeIndicator(mode);

            span.setAttribute("input.mode", mode);
            span.setAttribute("input.filename", inputPath.split("/").pop() || "unknown");

            // Validate input
            if (mode === "project") {
              await validateProjectMode(inputPath);
            } else {
              await validateSingleFlowMode(inputPath);
            }

            // Package input for upload
            const spinner = createSpinner("Packaging input...");
            spinner.start();

            const pkg =
              mode === "project"
                ? await packageProjectDir(inputPath)
                : await packageSingleFlow(inputPath);

            uploadBytes.add(pkg.buffer.byteLength, {
              command: "analyze",
              mode,
            });

            spinner.text = "Analyzing...";

            // Call backend with file upload
            const client = new ApiClient(config.backendUrl, config.apiToken);
            const result = await client.analyze(pkg, mode);
            spinner.succeed("  Analysis complete!");

            printAnalysisResult(result);

            // Record metrics
            commandsExecuted.add(1, { command: "analyze", status: "success", mode });
          },
          {
            command: "analyze",
          },
        );
      } catch (error) {
        commandsExecuted.add(1, { command: "analyze", status: "error" });
        handleError(error);
      } finally {
        const duration = Date.now() - startTime;
        commandDuration.record(duration, { command: "analyze" });
      }
    });
}
