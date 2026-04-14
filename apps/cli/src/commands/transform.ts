/**
 * `transform` command — transforms a MuleSoft project or single flow
 * into Logic Apps Standard artifacts.
 */
import { Command } from "commander";
import { detectInputMode } from "../services/input-detector.js";
import { validateProjectMode, validateSingleFlowMode } from "../services/input-validator.js";
import { packageProjectDir, packageSingleFlow } from "../services/project-packager.js";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printModeIndicator, printTransformResult, createSpinner } from "../ui/output.js";
import { handleError } from "../ui/errors.js";
import { withSpan } from "../telemetry/index.js";
import { commandsExecuted, commandDuration, uploadBytes } from "../telemetry/metrics.js";

/**
 * Create the transform command.
 */
export function createTransformCommand(): Command {
  return new Command("transform")
    .description("Transform a MuleSoft project or single flow into Logic Apps Standard artifacts")
    .argument("<inputPath>", "Path to MuleSoft project directory or single flow XML file")
    .option("-o, --output <dir>", "Output directory for generated artifacts", "./output")
    .action(async (inputPath: string, options: { output: string }, cmd: Command) => {
      const startTime = Date.now();
      try {
        await withSpan(
          "m2la.cli.command.transform",
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
              command: "transform",
              mode,
            });

            spinner.text = "Transforming...";

            // Call backend with file upload
            const client = new ApiClient(config.backendUrl, config.apiToken);
            const result = await client.transform(pkg, mode, options.output);
            spinner.succeed("  Transformation complete!");

            printTransformResult(result);

            // Record metrics
            commandsExecuted.add(1, { command: "transform", status: "success", mode });
          },
          {
            command: "transform",
          },
        );
      } catch (error) {
        commandsExecuted.add(1, { command: "transform", status: "error" });
        handleError(error);
      } finally {
        const duration = Date.now() - startTime;
        commandDuration.record(duration, { command: "transform" });
      }
    });
}
