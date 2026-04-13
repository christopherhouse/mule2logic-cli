/**
 * `transform` command — transforms a MuleSoft project or single flow
 * into Logic Apps Standard artifacts.
 */
import { Command } from "commander";
import type { TransformRequest } from "@m2la/contracts";
import { detectInputMode } from "../services/input-detector.js";
import { validateProjectMode, validateSingleFlowMode } from "../services/input-validator.js";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printModeIndicator, printTransformResult, createSpinner } from "../ui/output.js";
import { handleError } from "../ui/errors.js";

/**
 * Create the transform command.
 */
export function createTransformCommand(): Command {
  return new Command("transform")
    .description("Transform a MuleSoft project or single flow into Logic Apps Standard artifacts")
    .argument("<inputPath>", "Path to MuleSoft project directory or single flow XML file")
    .option("-o, --output <dir>", "Output directory for generated artifacts", "./output")
    .action(async (inputPath: string, options: { output: string }, cmd: Command) => {
      try {
        const parentOpts = cmd.parent?.opts() as { backendUrl?: string } | undefined;
        const config = getConfig({ backendUrl: parentOpts?.backendUrl });

        // Detect input mode
        const mode = await detectInputMode(inputPath);
        printModeIndicator(mode);

        // Validate input
        if (mode === "project") {
          await validateProjectMode(inputPath);
        } else {
          await validateSingleFlowMode(inputPath);
        }

        // Call backend
        const spinner = createSpinner("Transforming...");
        spinner.start();

        const client = new ApiClient(config.backendUrl);
        const request: TransformRequest = {
          input_path: inputPath,
          mode,
          output_directory: options.output,
        };

        const result = await client.transform(request);
        spinner.succeed("  Transformation complete!");

        printTransformResult(result);
      } catch (error) {
        handleError(error);
      }
    });
}
