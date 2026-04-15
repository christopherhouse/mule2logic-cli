#!/usr/bin/env node
import { Command } from "commander";
import { showBanner } from "./ui/banner.js";
import {
  createAnalyzeCommand,
  createTransformCommand,
  createValidateCommand,
} from "./commands/index.js";
import { initTelemetry } from "./telemetry/index.js";

// Initialize telemetry at startup (before any commands execute)
await initTelemetry();

const program = new Command();

program
  .name("mule2logic")
  .version("0.1.0")
  .description("MuleSoft → Logic Apps Standard migration tool")
  .option("--backend-url <url>", "Backend API URL (overrides M2LA_BACKEND_URL env var)")
  .option(
    "--api-token <token>",
    "API token for backend authentication (overrides M2LA_API_TOKEN env var)",
  )
  .hook("preAction", () => {
    showBanner();
  });

program.addCommand(createAnalyzeCommand());
program.addCommand(createTransformCommand());
program.addCommand(createValidateCommand());

// Show banner when run with no arguments
if (process.argv.length <= 2) {
  showBanner();
  program.help();
}

program.parse();
