import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, writeFile, rm, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { validateProjectMode, validateSingleFlowMode } from "../src/services/input-validator.js";
import { CliError } from "../src/ui/errors.js";

describe("validateProjectMode", () => {
  let tempDir: string;

  beforeAll(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "m2la-proj-"));
  });

  afterAll(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("should pass for a valid Mule project structure", async () => {
    // Create valid project structure
    const projDir = join(tempDir, "valid-project");
    await mkdir(projDir, { recursive: true });
    await writeFile(join(projDir, "pom.xml"), "<project></project>");
    await mkdir(join(projDir, "src", "main", "mule"), { recursive: true });
    await writeFile(join(projDir, "src", "main", "mule", "main-flow.xml"), "<mule></mule>");

    await expect(validateProjectMode(projDir)).resolves.toBeUndefined();
  });

  it("should throw MISSING_POM_XML when pom.xml is absent", async () => {
    const projDir = join(tempDir, "no-pom");
    await mkdir(projDir, { recursive: true });
    await mkdir(join(projDir, "src", "main", "mule"), { recursive: true });
    await writeFile(join(projDir, "src", "main", "mule", "flow.xml"), "<mule></mule>");

    try {
      await validateProjectMode(projDir);
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("MISSING_POM_XML");
    }
  });

  it("should throw MISSING_MULE_DIR when src/main/mule/ is absent", async () => {
    const projDir = join(tempDir, "no-mule-dir");
    await mkdir(projDir, { recursive: true });
    await writeFile(join(projDir, "pom.xml"), "<project></project>");

    try {
      await validateProjectMode(projDir);
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("MISSING_MULE_DIR");
    }
  });

  it("should throw NO_MULE_FLOWS when src/main/mule/ has no XML files", async () => {
    const projDir = join(tempDir, "empty-mule-dir");
    await mkdir(projDir, { recursive: true });
    await writeFile(join(projDir, "pom.xml"), "<project></project>");
    await mkdir(join(projDir, "src", "main", "mule"), { recursive: true });
    await writeFile(join(projDir, "src", "main", "mule", "readme.txt"), "not xml");

    try {
      await validateProjectMode(projDir);
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("NO_MULE_FLOWS");
    }
  });
});

describe("validateSingleFlowMode", () => {
  let tempDir: string;

  beforeAll(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "m2la-flow-"));
  });

  afterAll(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("should pass for XML with <flow> element", async () => {
    const filePath = join(tempDir, "valid-flow.xml");
    await writeFile(
      filePath,
      `<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core">
  <flow name="testFlow">
    <logger message="hello"/>
  </flow>
</mule>`,
    );

    await expect(validateSingleFlowMode(filePath)).resolves.toBeUndefined();
  });

  it("should pass for XML with <sub-flow> element", async () => {
    const filePath = join(tempDir, "valid-subflow.xml");
    await writeFile(
      filePath,
      `<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns="http://www.mulesoft.org/schema/mule/core">
  <sub-flow name="mySubFlow">
    <logger message="hello"/>
  </sub-flow>
</mule>`,
    );

    await expect(validateSingleFlowMode(filePath)).resolves.toBeUndefined();
  });

  it("should throw NO_FLOW_ELEMENTS for XML without flow/sub-flow", async () => {
    const filePath = join(tempDir, "no-flow.xml");
    await writeFile(filePath, `<?xml version="1.0"?><root><data/></root>`);

    try {
      await validateSingleFlowMode(filePath);
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("NO_FLOW_ELEMENTS");
    }
  });

  it("should throw for non-XML content", async () => {
    const filePath = join(tempDir, "bad.xml");
    await writeFile(filePath, "this is not xml at all {{{");

    try {
      await validateSingleFlowMode(filePath);
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      // fast-xml-parser may parse some non-XML leniently, so we accept either INVALID_XML or NO_FLOW_ELEMENTS
      const code = (e as CliError).code;
      expect(["INVALID_XML", "NO_FLOW_ELEMENTS"]).toContain(code);
    }
  });

  it("should throw UNREADABLE_FILE for non-existent file", async () => {
    try {
      await validateSingleFlowMode(join(tempDir, "nope.xml"));
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(CliError);
      expect((e as CliError).code).toBe("UNREADABLE_FILE");
    }
  });
});
