/**
 * `analyze` command — analyzes a MuleSoft project or single flow.
 */
import { Command } from "commander";
import type { AnalyzeRequest } from "@m2la/contracts";
import { detectInputMode } from "../services/input-detector.js";
import { validateProjectMode, validateSingleFlowMode } from "../services/input-validator.js";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printModeIndicator, printAnalysisResult, createSpinner } from "../ui/output.js";
import { handleError } from "../ui/errors.js";

/**
 * Create the analyze command.
 */
export function createAnalyzeCommand(): Command {
  return new Command("analyze")
    .description("Analyze a MuleSoft project or single flow for migration readiness")
    .argument("<inputPath>", "Path to MuleSoft project directory or single flow XML file")
    .action(async (inputPath: string, _options: unknown, cmd: Command) => {
      try {
        const parentOpts = cmd.parent?.opts() as { backendUrl?: string; apiToken?: string } | undefined;
        const config = getConfig({ backendUrl: parentOpts?.backendUrl, apiToken: parentOpts?.apiToken });

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
        const spinner = createSpinner("Analyzing...");
        spinner.start();

        const client = new ApiClient(config.backendUrl, config.apiToken);
        const request: AnalyzeRequest = {
          input_path: inputPath,
          mode,
        };

        const result = await client.analyze(request);
        spinner.succeed("  Analysis complete!");

        printAnalysisResult(result);
      } catch (error) {
        handleError(error);
      }
    });
}
