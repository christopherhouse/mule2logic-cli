import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { runCopilot } from './copilot.js';

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

export function buildReportPrompt(xml, workflowJson) {
  return reportUserTemplate
    .replace('{{xml}}', xml)
    .replace('{{workflowJson}}', JSON.stringify(workflowJson, null, 2));
}

export async function generateReport(xml, workflowJson, { verbose = false, model, timeout } = {}) {
  const prompt = buildReportPrompt(xml, workflowJson);

  const response = await runCopilot(prompt, {
    verbose,
    systemPrompt: REPORT_SYSTEM_PROMPT,
    model,
    timeout,
  });

  return response;
}
