#!/usr/bin/env node

import { program } from 'commander';
import { convertCommand } from './commands/convert.js';

program
  .name('mule2logic')
  .description('Convert MuleSoft XML flows to Azure Logic Apps Standard workflow JSON')
  .version('1.0.0');

program
  .command('convert [input]')
  .description('Convert a MuleSoft XML flow to Logic Apps JSON')
  .option('--output <file>', 'Write JSON to file or directory (required with --project)')
  .option('--project <path>', 'Convert an entire MuleSoft project directory')
  .option('--report <file>', 'Write a migration analysis report (Markdown) to file')
  .option('--explain', 'Include explanation')
  .option('--pretty', 'Pretty-print JSON')
  .option('--verbose', 'Debug logs')
  .option('--debug', 'Dump raw Copilot response to stderr')
  .option('--model <model>', 'Model to use (default: claude-opus-4.6)')
  .option('--timeout <ms>', 'Timeout per Copilot call in ms (default: 300000)', parseInt)
  .option('--no-review', 'Skip the QC review agent step')
  .action(convertCommand);

program.parse();
