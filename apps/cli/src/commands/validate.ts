/**
 * `validate` command — validates generated Logic Apps Standard artifacts.
 */
import { Command } from "commander";
import { stat } from "node:fs/promises";
import { resolve } from "node:path";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printValidationResult, createSpinner } from "../ui/output.js";
import { CliError, handleError } from "../ui/errors.js";

/**
 * Create the validate command.
 */
export function createValidateCommand(): Command {
  return new Command("validate")
    .description("Validate generated Logic Apps Standard output artifacts")
    .argument("<outputPath>", "Path to the generated Logic Apps output directory")
    .action(async (outputPath: string, _options: unknown, cmd: Command) => {
      try {
        const parentOpts = cmd.parent?.opts() as { backendUrl?: string } | undefined;
        const config = getConfig({ backendUrl: parentOpts?.backendUrl });

        // Verify output path exists
        const resolvedPath = resolve(outputPath);
        try {
          await stat(resolvedPath);
        } catch {
          throw new CliError(
            "OUTPUT_NOT_FOUND",
            `Output path does not exist: ${resolvedPath}`,
            "Run the transform command first to generate output artifacts.",
          );
        }

        // Call backend
        const spinner = createSpinner("Validating...");
        spinner.start();

        const client = new ApiClient(config.backendUrl);
        const result = await client.validate(resolvedPath);

        if (result.valid) {
          spinner.succeed("  Validation complete!");
        } else {
          spinner.fail("  Validation found issues");
        }

        printValidationResult(result);
      } catch (error) {
        handleError(error);
      }
    });
}
