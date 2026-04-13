/**
 * Input validation service.
 * Validates MuleSoft project directories and single flow XML files.
 */
import { access, readdir, readFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { XMLParser } from "fast-xml-parser";
import { CliError } from "../ui/errors.js";

/**
 * Validate that a directory is a MuleSoft project root.
 * Checks for pom.xml and src/main/mule/ directory with XML files.
 * @param dirPath - Path to the project directory
 */
export async function validateProjectMode(dirPath: string): Promise<void> {
  const resolvedDir = resolve(dirPath);

  // Check pom.xml exists
  const pomPath = join(resolvedDir, "pom.xml");
  try {
    await access(pomPath);
  } catch {
    throw new CliError(
      "MISSING_POM_XML",
      `pom.xml not found in ${resolvedDir}`,
      "Ensure the path points to a MuleSoft project root containing pom.xml.",
    );
  }

  // Check src/main/mule/ directory exists and contains at least one XML file
  const muleDir = join(resolvedDir, "src", "main", "mule");
  try {
    await access(muleDir);
  } catch {
    throw new CliError(
      "MISSING_MULE_DIR",
      `Mule flow directory not found: ${muleDir}`,
      "A MuleSoft project should have flow XML files under src/main/mule/.",
    );
  }

  let entries;
  try {
    entries = await readdir(muleDir);
  } catch {
    throw new CliError(
      "UNREADABLE_MULE_DIR",
      `Cannot read Mule flow directory: ${muleDir}`,
      "Check directory permissions.",
    );
  }

  const xmlFiles = entries.filter((f) => f.toLowerCase().endsWith(".xml"));
  if (xmlFiles.length === 0) {
    throw new CliError(
      "NO_MULE_FLOWS",
      `No XML flow files found in ${muleDir}`,
      "Add Mule flow XML files to src/main/mule/ in your project.",
    );
  }
}

/**
 * Validate that a file is a valid Mule flow XML containing at least one
 * `<flow>` or `<sub-flow>` element.
 * @param filePath - Path to the XML file
 */
export async function validateSingleFlowMode(filePath: string): Promise<void> {
  const resolvedFile = resolve(filePath);

  let content: string;
  try {
    content = await readFile(resolvedFile, "utf-8");
  } catch {
    throw new CliError(
      "UNREADABLE_FILE",
      `Cannot read file: ${resolvedFile}`,
      "Check that the file exists and you have read permissions.",
    );
  }

  let parsed: Record<string, unknown>;
  try {
    const parser = new XMLParser({ ignoreAttributes: false });
    parsed = parser.parse(content) as Record<string, unknown>;
  } catch {
    throw new CliError(
      "INVALID_XML",
      `File is not valid XML: ${resolvedFile}`,
      "Ensure the file is a well-formed Mule flow XML document.",
    );
  }

  // Look for <flow> or <sub-flow> elements anywhere in the parsed document
  if (!containsMuleFlowElements(parsed)) {
    throw new CliError(
      "NO_FLOW_ELEMENTS",
      `No <flow> or <sub-flow> elements found in ${resolvedFile}`,
      "The file must contain at least one <flow> or <sub-flow> element to be a valid Mule flow.",
    );
  }
}

/**
 * Recursively search for flow or sub-flow keys in parsed XML.
 */
function containsMuleFlowElements(obj: unknown): boolean {
  if (obj === null || obj === undefined || typeof obj !== "object") {
    return false;
  }

  if (Array.isArray(obj)) {
    return obj.some((item) => containsMuleFlowElements(item));
  }

  const record = obj as Record<string, unknown>;
  for (const key of Object.keys(record)) {
    if (key === "flow" || key === "sub-flow") {
      return true;
    }
    if (containsMuleFlowElements(record[key])) {
      return true;
    }
  }

  return false;
}
