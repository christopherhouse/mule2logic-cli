import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { runCopilot } from './copilot.js';
import { validateConversionModel } from './validate.js';
import type { ConversionModel } from './validate.js';
import type { ProjectContext } from './project.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const promptsDir = join(__dirname, '..', 'prompts');

const ASSESS_SYSTEM_PROMPT = readFileSync(
  join(promptsDir, 'assess.prompt.md'),
  'utf-8',
).trim();

const assessUserTemplate = readFileSync(
  join(promptsDir, 'assess.user.prompt.md'),
  'utf-8',
).trim();

export interface AssessOptions {
  verbose?: boolean;
  model?: string;
  timeout?: number;
}

export function buildAssessPrompt(context: ProjectContext): string {
  const projectTree = context.tree.join('\n');

  const fileContents = Array.from(context.files.entries())
    .map(([path, content]) => `<file path="${path}">\n${content}\n</file>`)
    .join('\n\n');

  return assessUserTemplate
    .replace('{{projectTree}}', projectTree)
    .replace('{{fileContents}}', fileContents);
}

export async function assessProject(
  context: ProjectContext,
  { verbose = false, model, timeout }: AssessOptions = {},
): Promise<ConversionModel> {
  const prompt = buildAssessPrompt(context);

  if (verbose) {
    console.error(`[verbose] Assessment prompt length: ${prompt.length} chars`);
  }

  const response = await runCopilot(prompt, {
    verbose,
    systemPrompt: ASSESS_SYSTEM_PROMPT,
    model,
    timeout,
  });

  return validateConversionModel(response);
}
