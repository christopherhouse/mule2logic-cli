/**
 * `validate` command — validates generated Logic Apps Standard artifacts.
 */
import { Command } from "commander";
import { stat } from "node:fs/promises";
import { resolve } from "node:path";
import { packageProjectDir } from "../services/project-packager.js";
import { ApiClient } from "../services/api-client.js";
import { getConfig } from "../config.js";
import { printValidationResult, createSpinner } from "../ui/output.js";
import { CliError, handleError } from "../ui/errors.js";
import { withSpan } from "../telemetry/index.js";
import { commandsExecuted, commandDuration, uploadBytes } from "../telemetry/metrics.js";

/**
 * Create the validate command.
 */
export function createValidateCommand(): Command {
  return new Command("validate")
    .description("Validate generated Logic Apps Standard output artifacts")
    .argument("<outputPath>", "Path to the generated Logic Apps output directory")
    .action(async (outputPath: string, _options: unknown, cmd: Command) => {
      const startTime = Date.now();
      try {
        await withSpan(
          "m2la.cli.command.validate",
          async (span) => {
            const parentOpts = cmd.parent?.opts() as
              | { backendUrl?: string; apiToken?: string }
              | undefined;
            const config = getConfig({
              backendUrl: parentOpts?.backendUrl,
              apiToken: parentOpts?.apiToken,
            });

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

            span.setAttribute("output.path", outputPath);

            // Package output directory for upload
            const spinner = createSpinner("Packaging output...");
            spinner.start();

            const pkg = await packageProjectDir(resolvedPath);

            uploadBytes.add(pkg.buffer.byteLength, {
              command: "validate",
            });

            spinner.text = "Validating...";

            // Call backend with file upload
            const client = new ApiClient(config.backendUrl, config.apiToken);
            const result = await client.validate(pkg);

            if (result.valid) {
              spinner.succeed("  Validation complete!");
            } else {
              spinner.fail("  Validation found issues");
            }

            printValidationResult(result);

            // Record metrics
            commandsExecuted.add(1, {
              command: "validate",
              status: result.valid ? "success" : "warning",
            });
          },
          {
            command: "validate",
          },
        );
      } catch (error) {
        commandsExecuted.add(1, { command: "validate", status: "error" });
        handleError(error);
      } finally {
        const duration = Date.now() - startTime;
        commandDuration.record(duration, { command: "validate" });
      }
    });
}
