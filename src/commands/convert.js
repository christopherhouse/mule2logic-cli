import { readInput } from '../core/io.js';
import { buildPrompt } from '../core/prompt.js';
import { runCopilot } from '../core/copilot.js';
import { validateJson } from '../core/validate.js';
import { writeFile } from 'fs/promises';

export async function convertCommand(input, options) {
  try {
    // 1. Load input
    if (options.verbose) {
      console.error('[verbose] Loading input...');
    }
    const xml = await readInput(input);

    // 2. Build prompt
    const prompt = buildPrompt(xml);
    if (options.verbose) {
      console.error('[verbose] Prompt:\n' + prompt);
    }

    // 3. Call Copilot
    if (options.verbose) {
      console.error('[verbose] Calling Copilot...');
    }
    let response = await runCopilot(prompt);

    // 4. Validate JSON (retry once on failure)
    let parsed;
    try {
      parsed = validateJson(response);
    } catch (err) {
      if (options.verbose) {
        console.error(`[verbose] Validation failed: ${err.message}. Retrying...`);
      }
      response = await runCopilot(prompt);
      try {
        parsed = validateJson(response);
      } catch (retryErr) {
        console.error(`Error: Invalid JSON output after retry — ${retryErr.message}`);
        process.exit(1);
      }
    }

    // 5. Format output
    let output;
    if (options.explain) {
      output = { workflow: parsed, explanation: response };
    } else {
      output = parsed;
    }

    const jsonString = options.pretty
      ? JSON.stringify(output, null, 2)
      : JSON.stringify(output);

    // 6. Write output
    if (options.output) {
      await writeFile(options.output, jsonString, 'utf-8');
      if (options.verbose) {
        console.error(`[verbose] Output written to ${options.output}`);
      }
    } else {
      console.log(jsonString);
    }
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}
