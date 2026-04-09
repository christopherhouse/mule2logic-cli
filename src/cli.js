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
  .option('--output <file>', 'Write JSON to file')
  .option('--explain', 'Include explanation')
  .option('--pretty', 'Pretty-print JSON')
  .option('--verbose', 'Debug logs')
  .action(convertCommand);

program.parse();
