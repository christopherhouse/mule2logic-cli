import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const promptsDir = join(__dirname, '..', 'prompts');

function loadPrompt(filename) {
  return readFileSync(join(promptsDir, filename), 'utf-8').trim();
}

export const SYSTEM_PROMPT = loadPrompt('system.prompt.md');

const userTemplate = loadPrompt('user.prompt.md');

export function buildPrompt(xml) {
  return userTemplate.replace('{{xml}}', xml);
}
