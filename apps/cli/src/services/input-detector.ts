/**
 * Input mode detection service.
 * Auto-detects whether the input is a MuleSoft project root (directory)
 * or a single Mule flow XML file.
 */
import { stat } from "node:fs/promises";
import { extname, resolve } from "node:path";
import type { InputMode } from "@m2la/contracts";
import { CliError } from "../ui/errors.js";

/**
 * Detect the input mode from the given path.
 * - Directory → "project" mode
 * - .xml file → "single_flow" mode
 * @param inputPath - Path to a MuleSoft project directory or single flow XML file
 * @returns The detected input mode
 */
export async function detectInputMode(inputPath: string): Promise<InputMode> {
  const resolvedPath = resolve(inputPath);

  let stats;
  try {
    stats = await stat(resolvedPath);
  } catch {
    throw new CliError(
      "INPUT_NOT_FOUND",
      `Path does not exist: ${resolvedPath}`,
      "Check that the path is correct and the file or directory exists.",
    );
  }

  if (stats.isDirectory()) {
    return "project";
  }

  if (stats.isFile()) {
    const ext = extname(resolvedPath).toLowerCase();
    if (ext === ".xml") {
      return "single_flow";
    }

    throw new CliError(
      "INVALID_INPUT_TYPE",
      `File is not an XML file: ${resolvedPath}`,
      "Provide a .xml Mule flow file or a MuleSoft project directory.",
    );
  }

  throw new CliError(
    "INVALID_INPUT_TYPE",
    `Path is neither a file nor a directory: ${resolvedPath}`,
    "Provide a MuleSoft project directory or a single Mule flow XML file.",
  );
}
