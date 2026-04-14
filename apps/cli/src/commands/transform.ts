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
import {
  printModeIndicator,
  printTransformResult,
  createSpinner,
  printStreamingProgress,
  printStreamingComplete,
} from "../ui/output.js";
import { handleError } from "../ui/errors.js";

/**
 * Create the transform command.
 */
export function createTransformCommand(): Command {
  return new Command("transform")
    .description("Transform a MuleSoft project or single flow into Logic Apps Standard artifacts")
    .argument("<inputPath>", "Path to MuleSoft project directory or single flow XML file")
    .option("-o, --output <dir>", "Output directory for generated artifacts", "./output")
    .option("--stream", "Use streaming mode for real-time progress updates", false)
    .action(
      async (inputPath: string, options: { output: string; stream: boolean }, cmd: Command) => {
        try {
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

          spinner.succeed("  Input packaged");

          // Call backend with file upload
          const client = new ApiClient(config.backendUrl, config.apiToken);

          if (options.stream) {
            // Use streaming mode
            console.log();
            console.log("  🔄  Starting transformation pipeline...");
            console.log();

            try {
              for await (const event of client.transformStreaming(pkg, mode, options.output)) {
                if (event.event_type === "agent_started" && event.agent_name) {
                  printStreamingProgress(event.agent_name, "started");
                } else if (event.event_type === "agent_completed" && event.agent_name) {
                  const durationMs =
                    typeof event.data.duration_ms === "number" ? event.data.duration_ms : undefined;
                  printStreamingProgress(event.agent_name, "completed", durationMs);
                } else if (event.event_type === "complete") {
                  const overallStatus =
                    typeof event.data.overall_status === "string"
                      ? event.data.overall_status
                      : "unknown";
                  const totalDurationMs =
                    typeof event.data.total_duration_ms === "number"
                      ? event.data.total_duration_ms
                      : 0;
                  const steps = typeof event.data.steps === "number" ? event.data.steps : 0;
                  printStreamingComplete(overallStatus, totalDurationMs, steps);
                } else if (event.event_type === "error") {
                  console.error(`  ❌  Error: ${event.message || "Unknown error"}`);
                }
              }
            } catch (error) {
              handleError(error);
            }
          } else {
            // Use traditional non-streaming mode
            spinner.text = "Transforming...";
            spinner.start();

            const result = await client.transform(pkg, mode, options.output);
            spinner.succeed("  Transformation complete!");

            printTransformResult(result);
          }
        } catch (error) {
          handleError(error);
        }
      },
    );
}
