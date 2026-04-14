/**
 * Project packager service.
 * Packages MuleSoft project directories into zip archives for upload,
 * or reads single-flow XML files into buffers.
 */
import { createReadStream, createWriteStream } from "node:fs";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, basename } from "node:path";
import { randomUUID } from "node:crypto";
import archiver from "archiver";
import { CliError } from "../ui/errors.js";

/**
 * Result of packaging a project or single-flow file for upload.
 */
export interface PackageResult {
  /** The file buffer containing zip or XML content. */
  buffer: Buffer;
  /** The suggested filename for the upload. */
  filename: string;
  /** The MIME type for the upload. */
  contentType: string;
}

/**
 * Package a MuleSoft project directory into a zip archive.
 * @param dirPath - Path to the MuleSoft project root directory
 * @returns A PackageResult with the zip buffer
 */
export async function packageProjectDir(dirPath: string): Promise<PackageResult> {
  const resolvedDir = resolve(dirPath);
  const dirName = basename(resolvedDir);

  const tmpZipPath = join(tmpdir(), `m2la-${randomUUID()}.zip`);

  try {
    const buffer = await createZipFromDir(resolvedDir, dirName, tmpZipPath);
    return {
      buffer,
      filename: `${dirName}.zip`,
      contentType: "application/zip",
    };
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    throw new CliError(
      "PACKAGING_FAILED",
      `Failed to package project directory: ${msg}`,
      "Ensure the project directory is readable and not too large.",
    );
  }
}

/**
 * Read a single-flow XML file into a buffer for upload.
 * @param filePath - Path to the Mule flow XML file
 * @returns A PackageResult with the XML buffer
 */
export async function packageSingleFlow(filePath: string): Promise<PackageResult> {
  const resolvedPath = resolve(filePath);
  const fileName = basename(resolvedPath);

  try {
    const buffer = await readFile(resolvedPath);
    return {
      buffer: Buffer.from(buffer),
      filename: fileName,
      contentType: "application/xml",
    };
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    throw new CliError(
      "PACKAGING_FAILED",
      `Failed to read flow file: ${msg}`,
      "Ensure the file is readable.",
    );
  }
}

/**
 * Create a zip archive from a directory, returning the content as a Buffer.
 */
function createZipFromDir(
  sourceDir: string,
  rootDirName: string,
  tmpPath: string,
): Promise<Buffer> {
  return new Promise<Buffer>((resolve, reject) => {
    const output = createWriteStream(tmpPath);
    const archive = archiver("zip", { zlib: { level: 6 } });

    const chunks: Buffer[] = [];

    output.on("close", () => {
      // Read the temp file back as a buffer
      const stream = createReadStream(tmpPath);
      stream.on("data", (chunk: Buffer) => chunks.push(chunk));
      stream.on("end", () => {
        // Clean up temp file
        import("node:fs/promises").then(({ unlink }) =>
          unlink(tmpPath).catch(() => {
            /* ignore cleanup errors */
          }),
        );
        resolve(Buffer.concat(chunks));
      });
      stream.on("error", reject);
    });

    archive.on("error", reject);
    archive.pipe(output);

    // Add the directory contents under a top-level directory name
    archive.directory(sourceDir, rootDirName);
    archive.finalize();
  });
}
