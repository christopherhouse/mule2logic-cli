import { readInput } from '../core/io.js';
import { buildPrompt } from '../core/prompt.js';
import { runCopilot } from '../core/copilot.js';
import { validateJson } from '../core/validate.js';
import { writeFile } from 'fs/promises';

// ANSI color helpers
const c = {
  cyan: (s) => `\x1b[36m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
  bold: (s) => `\x1b[1m${s}\x1b[0m`,
};

const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

const activeSpinners = [];

function createSpinner(message) {
  let i = 0;
  const spinner = {
    _id: setInterval(() => {
      const frame = c.cyan(spinnerFrames[i++ % spinnerFrames.length]);
      process.stderr.write(`\r${frame} ${message}`);
    }, 80),
    stop(finalMsg) {
      clearInterval(spinner._id);
      const idx = activeSpinners.indexOf(spinner);
      if (idx !== -1) activeSpinners.splice(idx, 1);
      process.stderr.write(`\r${finalMsg}\n`);
    },
  };
  activeSpinners.push(spinner);
  return spinner;
}

function stopAllSpinners() {
  for (const s of activeSpinners.splice(0)) clearInterval(s._id);
}

export async function convertCommand(input, options) {
  try {
    console.error(c.bold('\n🔄 mule2logic') + c.dim(' — MuleSoft → Azure Logic Apps\n'));

    // 1. Load input
    if (options.verbose) {
      console.error('[verbose] Loading input...');
    }
    const spinner1 = createSpinner(c.dim('Reading MuleSoft XML...'));
    const xml = await readInput(input);
    spinner1.stop(`${c.green('✔')} ${c.bold('Input loaded')} ${c.dim(`(${xml.length} chars)`)}`);

    // 2. Build prompt
    const prompt = buildPrompt(xml);
    if (options.verbose) {
      console.error('[verbose] Prompt:\n' + prompt);
    }
    console.error(`${c.green('✔')} ${c.bold('Prompt built')}`);

    // 3. Call Copilot
    if (options.verbose) {
      console.error('[verbose] Calling Copilot...');
    }
    const spinner3 = createSpinner(`${c.yellow('Calling Copilot AI')} ${c.dim('(this may take a moment...)')}`);
    const startTime = Date.now();
    let response = await runCopilot(prompt, { verbose: !!options.verbose });
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    spinner3.stop(`${c.green('✔')} ${c.bold('Copilot responded')} ${c.dim(`(${elapsed}s)`)}`);

    if (options.debug) {
      console.error(`\n${c.cyan('━━━ Raw Copilot Response ━━━')}`);
      console.error(response);
      console.error(`${c.cyan('━━━ End Raw Response ━━━')}\n`);
    }

    // 4. Validate JSON (retry once on failure)
    let parsed;
    try {
      parsed = validateJson(response);
      console.error(`${c.green('✔')} ${c.bold('Output validated')}`);
    } catch (err) {
      console.error(`${c.yellow('⚠')}  Validation failed, retrying...`);
      if (options.verbose) {
        console.error(`[verbose] Validation failed: ${err.message}. Retrying...`);
      }
      const spinner4 = createSpinner(c.yellow('Retrying Copilot call...'));
      response = await runCopilot(prompt, { verbose: !!options.verbose });
      spinner4.stop(`${c.green('✔')} ${c.bold('Retry complete')}`);
      if (options.debug) {
        console.error(`\n${c.cyan('━━━ Raw Copilot Response (retry) ━━━')}`);
        console.error(response);
        console.error(`${c.cyan('━━━ End Raw Response ━━━')}\n`);
      }
      try {
        parsed = validateJson(response);
        console.error(`${c.green('✔')} ${c.bold('Output validated on retry')}`);
      } catch (retryErr) {
        stopAllSpinners();
        console.error(`\n${c.red('✖')} ${c.red('Invalid JSON output after retry')} — ${retryErr.message}`);
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
      console.error(`${c.green('✔')} ${c.bold('Written to')} ${c.cyan(options.output)}`);
      if (options.verbose) {
        console.error(`[verbose] Output written to ${options.output}`);
      }
    } else {
      console.log(jsonString);
    }

    console.error(`\n${c.green('🎉 Conversion complete!')}\n`);
  } catch (err) {
    stopAllSpinners();
    console.error(`\n${c.red('✖')} ${c.red('Error:')} ${err.message}`);
    process.exit(1);
  }
}
