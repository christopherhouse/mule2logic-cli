import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, writeFile, rm, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { detectInputMode } from "../src/services/input-detector.js";
import { CliError } from "../src/ui/errors.js";

describe("detectInputMode", () => {
  let tempDir: string;

  beforeAll(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "m2la-test-"));
    // Create a sample .xml file
    await writeFile(join(tempDir, "flow.xml"), "<mule><flow name='test'/></mule>");
    // Create a non-xml file
    await writeFile(join(tempDir, "readme.txt"), "hello");
    // Create a subdirectory
    await mkdir(join(tempDir, "subdir"));
  });

  afterAll(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("should detect directory as project mode", async () => {
    const mode = await detectInputMode(tempDir);
    expect(mode).toBe("project");
  });

  it("should detect .xml file as single_flow mode", async () => {
    const mode = await detectInputMode(join(tempDir, "flow.xml"));
    expect(mode).toBe("single_flow");
  });

  it("should throw for non-existent path", async () => {
    try {
      await detectInputMode(join(tempDir, "nonexistent"));
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("INPUT_NOT_FOUND");
    }
  });

  it("should throw for non-xml file", async () => {
    try {
      await detectInputMode(join(tempDir, "readme.txt"));
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("INVALID_INPUT_TYPE");
    }
  });

  it("should detect subdirectory as project mode", async () => {
    const mode = await detectInputMode(join(tempDir, "subdir"));
    expect(mode).toBe("project");
  });
});
