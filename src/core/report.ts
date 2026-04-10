import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { runCopilot } from './copilot.js';
import type { WorkflowDefinition } from './validate.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const promptsDir = join(__dirname, '..', 'prompts');

const REPORT_SYSTEM_PROMPT = readFileSync(
  join(promptsDir, 'report.prompt.md'),
  'utf-8'
).trim();

const reportUserTemplate = readFileSync(
  join(promptsDir, 'report.user.prompt.md'),
  'utf-8'
).trim();

export interface ReportOptions {
  verbose?: boolean;
  model?: string;
  timeout?: number;
}

export function buildReportPrompt(xml: string, workflowJson: WorkflowDefinition): string {
  return reportUserTemplate
    .replace('{{xml}}', xml)
    .replace('{{workflowJson}}', JSON.stringify(workflowJson, null, 2));
}

export async function generateReport(
  xml: string,
  workflowJson: WorkflowDefinition,
  { verbose = false, model, timeout }: ReportOptions = {}
): Promise<string> {
  const prompt = buildReportPrompt(xml, workflowJson);

  const response = await runCopilot(prompt, {
    verbose,
    systemPrompt: REPORT_SYSTEM_PROMPT,
    model,
    timeout,
  });

  return response;
}
