import { describe, it, expect } from "vitest";
import { Command } from "commander";
import { createAnalyzeCommand } from "../src/commands/analyze.js";
import { createTransformCommand } from "../src/commands/transform.js";
import { createValidateCommand } from "../src/commands/validate.js";

describe("CLI commands", () => {
  it("analyze command should have correct name and argument", () => {
    const cmd = createAnalyzeCommand();
    expect(cmd.name()).toBe("analyze");
    expect(cmd.description()).toContain("Analyze");
    // Should require inputPath argument
    const args = cmd.registeredArguments;
    expect(args.length).toBe(1);
    expect(args[0].name()).toBe("inputPath");
    expect(args[0].required).toBe(true);
  });

  it("transform command should have correct name and options", () => {
    const cmd = createTransformCommand();
    expect(cmd.name()).toBe("transform");
    expect(cmd.description()).toContain("Transform");
    // Should have --output option
    const outputOpt = cmd.options.find((o) => o.long === "--output");
    expect(outputOpt).toBeDefined();
  });

  it("validate command should have correct name and argument", () => {
    const cmd = createValidateCommand();
    expect(cmd.name()).toBe("validate");
    expect(cmd.description()).toContain("Validate");
    const args = cmd.registeredArguments;
    expect(args.length).toBe(1);
    expect(args[0].name()).toBe("outputPath");
    expect(args[0].required).toBe(true);
  });

  it("program should include all commands and --backend-url option", () => {
    const program = new Command();
    program.name("mule2logic").version("0.1.0").option("--backend-url <url>", "Backend API URL");

    program.addCommand(createAnalyzeCommand());
    program.addCommand(createTransformCommand());
    program.addCommand(createValidateCommand());

    const commandNames = program.commands.map((c) => c.name());
    expect(commandNames).toContain("analyze");
    expect(commandNames).toContain("transform");
    expect(commandNames).toContain("validate");

    const backendOpt = program.options.find((o) => o.long === "--backend-url");
    expect(backendOpt).toBeDefined();
  });
});
