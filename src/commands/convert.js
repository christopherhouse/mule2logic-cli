import { readInput } from '../core/io.js';
import { buildPrompt } from '../core/prompt.js';
import { runCopilot, DEFAULT_MODEL, DEFAULT_TIMEOUT } from '../core/copilot.js';
import { validateJson, validateWorkflowStructure } from '../core/validate.js';
import { reviewWorkflow } from '../core/review.js';
import { generateReport } from '../core/report.js';
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
    const model = options.model || DEFAULT_MODEL;
    const timeout = options.timeout || DEFAULT_TIMEOUT;
    if (options.verbose) {
      console.error(`[verbose] Using model: ${model}`);
      console.error(`[verbose] Timeout: ${timeout}ms`);
    }

    // 3. Call Copilot
    if (options.verbose) {
      console.error('[verbose] Calling Copilot...');
    }
    const spinner3 = createSpinner(`${c.yellow('Calling Copilot AI')} ${c.dim('(this may take a moment...)')}`);
    const startTime = Date.now();
    let response = await runCopilot(prompt, { verbose: !!options.verbose, model, timeout });
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
      response = await runCopilot(prompt, { verbose: !!options.verbose, model, timeout });
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

    // 5. Review agent (quality control)
    if (!options.noReview) {
      const structuralIssues = validateWorkflowStructure(parsed);
      if (structuralIssues.length > 0 && options.verbose) {
        console.error(`${c.yellow('⚠')}  Structural issues detected:`);
        for (const issue of structuralIssues) {
          console.error(`${c.dim('   •')} ${issue}`);
        }
      }

      const spinner5 = createSpinner(`${c.yellow('Running QC review agent')} ${c.dim('(validating workflow...)')}`);
      try {
        const reviewStart = Date.now();
        const { workflow: reviewed, issues: remainingIssues } = await reviewWorkflow(xml, parsed, { verbose: !!options.verbose, model, timeout });
        const reviewElapsed = ((Date.now() - reviewStart) / 1000).toFixed(1);

        if (remainingIssues.length > 0) {
          spinner5.stop(`${c.yellow('⚠')}  ${c.bold('Review complete')} ${c.dim(`(${reviewElapsed}s)`)} — ${remainingIssues.length} issue(s) remain`);
          if (options.verbose) {
            for (const issue of remainingIssues) {
              console.error(`${c.dim('   •')} ${issue}`);
            }
          }
        } else {
          spinner5.stop(`${c.green('✔')} ${c.bold('QC review passed')} ${c.dim(`(${reviewElapsed}s)`)}`);
        }

        parsed = reviewed;
      } catch (reviewErr) {
        spinner5.stop(`${c.yellow('⚠')}  ${c.bold('Review agent failed')} — using original output`);
        if (options.verbose) {
          console.error(`[verbose] Review error: ${reviewErr.message}`);
        }
      }
    } else {
      console.error(`${c.dim('⏭  Review skipped (--no-review)')}`);
    }

    // 6. Format output
    let output;
    if (options.explain) {
      output = { workflow: parsed, explanation: response };
    } else {
      output = parsed;
    }

    const jsonString = options.pretty
      ? JSON.stringify(output, null, 2)
      : JSON.stringify(output);

    // 7. Write output
    if (options.output) {
      await writeFile(options.output, jsonString, 'utf-8');
      console.error(`${c.green('✔')} ${c.bold('Written to')} ${c.cyan(options.output)}`);
      if (options.verbose) {
        console.error(`[verbose] Output written to ${options.output}`);
      }
    } else {
      console.log(jsonString);
    }

    // 8. Generate migration report
    if (options.report) {
      const spinner6 = createSpinner(`${c.yellow('Generating migration report')} ${c.dim('(analyzing conversion...)')}`);
      try {
        const reportStart = Date.now();
        const reportMd = await generateReport(xml, parsed, { verbose: !!options.verbose, model, timeout });
        const reportElapsed = ((Date.now() - reportStart) / 1000).toFixed(1);
        await writeFile(options.report, reportMd, 'utf-8');
        spinner6.stop(`${c.green('✔')} ${c.bold('Report written to')} ${c.cyan(options.report)} ${c.dim(`(${reportElapsed}s)`)}`);
      } catch (reportErr) {
        spinner6.stop(`${c.yellow('⚠')}  ${c.bold('Report generation failed')} — ${reportErr.message}`);
        if (options.verbose) {
          console.error(`[verbose] Report error: ${reportErr.message}`);
        }
      }
    }

    console.error(`\n${c.green('🎉 Conversion complete!')}\n`);
  } catch (err) {
    stopAllSpinners();
    console.error(`\n${c.red('✖')} ${c.red('Error:')} ${err.message}`);
    process.exit(1);
  }
}
