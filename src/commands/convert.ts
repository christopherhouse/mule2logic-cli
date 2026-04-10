import { readInput } from '../core/io.js';
import { buildPrompt } from '../core/prompt.js';
import { runCopilot, DEFAULT_MODEL, DEFAULT_TIMEOUT } from '../core/copilot.js';
import { validateJson, validateWorkflowStructure, validateConversionModel } from '../core/validate.js';
import type { WorkflowDefinition, ConversionModel } from '../core/validate.js';
import { reviewWorkflow } from '../core/review.js';
import { generateReport } from '../core/report.js';
import { discoverProject } from '../core/project.js';
import { assessProject } from '../core/assess.js';
import { scaffoldProject } from '../core/scaffold.js';
import { writeFile, readFile, mkdir } from 'fs/promises';
import { join } from 'path';

// ANSI color helpers
const c = {
  cyan: (s: string): string => `\x1b[36m${s}\x1b[0m`,
  green: (s: string): string => `\x1b[32m${s}\x1b[0m`,
  yellow: (s: string): string => `\x1b[33m${s}\x1b[0m`,
  red: (s: string): string => `\x1b[31m${s}\x1b[0m`,
  dim: (s: string): string => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string): string => `\x1b[1m${s}\x1b[0m`,
};

const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

interface Spinner {
  _id: ReturnType<typeof setInterval>;
  stop(finalMsg: string): void;
}

const activeSpinners: Spinner[] = [];

function createSpinner(message: string): Spinner {
  let i = 0;
  const spinner: Spinner = {
    _id: setInterval(() => {
      const frame = c.cyan(spinnerFrames[i++ % spinnerFrames.length]);
      process.stderr.write(`\r${frame} ${message}`);
    }, 80),
    stop(finalMsg: string) {
      clearInterval(spinner._id);
      const idx = activeSpinners.indexOf(spinner);
      if (idx !== -1) activeSpinners.splice(idx, 1);
      process.stderr.write(`\r${finalMsg}\n`);
    },
  };
  activeSpinners.push(spinner);
  return spinner;
}

function stopAllSpinners(): void {
  for (const s of activeSpinners.splice(0)) clearInterval(s._id);
}

export interface ConvertOptions {
  output?: string;
  project?: string;
  report?: string;
  explain?: boolean;
  pretty?: boolean;
  verbose?: boolean;
  debug?: boolean;
  model?: string;
  timeout?: number;
  noReview?: boolean;
  review?: boolean;
}

export async function convertCommand(input: string | undefined, options: ConvertOptions): Promise<void> {
  if (options.project) {
    return projectConvertCommand(options);
  }

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
    let parsed: WorkflowDefinition;
    try {
      parsed = validateJson(response);
      console.error(`${c.green('✔')} ${c.bold('Output validated')}`);
    } catch (err) {
      console.error(`${c.yellow('⚠')}  Validation failed, retrying...`);
      if (options.verbose) {
        console.error(`[verbose] Validation failed: ${(err as Error).message}. Retrying...`);
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
        console.error(`\n${c.red('✖')} ${c.red('Invalid JSON output after retry')} — ${(retryErr as Error).message}`);
        process.exit(1);
      }
    }

    // 5. Review agent (quality control)
    if (!options.noReview) {
      const structuralIssues = validateWorkflowStructure(parsed!);
      if (structuralIssues.length > 0 && options.verbose) {
        console.error(`${c.yellow('⚠')}  Structural issues detected:`);
        for (const issue of structuralIssues) {
          console.error(`${c.dim('   •')} ${issue}`);
        }
      }

      const spinner5 = createSpinner(`${c.yellow('Running QC review agent')} ${c.dim('(validating workflow...)')}`);
      try {
        const reviewStart = Date.now();
        const { workflow: reviewed, issues: remainingIssues } = await reviewWorkflow(xml, parsed!, { verbose: !!options.verbose, model, timeout });
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
          console.error(`[verbose] Review error: ${(reviewErr as Error).message}`);
        }
      }
    } else {
      console.error(`${c.dim('⏭  Review skipped (--no-review)')}`);
    }

    // 6. Format output
    let output: WorkflowDefinition | { workflow: WorkflowDefinition; explanation: string };
    if (options.explain) {
      output = { workflow: parsed!, explanation: response };
    } else {
      output = parsed!;
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
        const reportMd = await generateReport(xml, parsed!, { verbose: !!options.verbose, model, timeout });
        const reportElapsed = ((Date.now() - reportStart) / 1000).toFixed(1);
        await writeFile(options.report, reportMd, 'utf-8');
        spinner6.stop(`${c.green('✔')} ${c.bold('Report written to')} ${c.cyan(options.report)} ${c.dim(`(${reportElapsed}s)`)}`);
      } catch (reportErr) {
        spinner6.stop(`${c.yellow('⚠')}  ${c.bold('Report generation failed')} — ${(reportErr as Error).message}`);
        if (options.verbose) {
          console.error(`[verbose] Report error: ${(reportErr as Error).message}`);
        }
      }
    }

    console.error(`\n${c.green('🎉 Conversion complete!')}\n`);
  } catch (err) {
    stopAllSpinners();
    console.error(`\n${c.red('✖')} ${c.red('Error:')} ${(err as Error).message}`);
    process.exit(1);
  }
}

async function projectConvertCommand(options: ConvertOptions): Promise<void> {
  try {
    console.error(c.bold('\n🔄 mule2logic') + c.dim(' — MuleSoft Project → Azure Logic Apps\n'));

    // Validate required options
    if (!options.output) {
      console.error(`${c.red('✖')} ${c.red('Error:')} --output <directory> is required when using --project`);
      process.exit(1);
    }

    const model = options.model || DEFAULT_MODEL;
    const timeout = options.timeout || DEFAULT_TIMEOUT;

    // 1. Discover project
    const spinner1 = createSpinner(c.dim('Scanning MuleSoft project...'));
    const context = await discoverProject(options.project!);
    spinner1.stop(`${c.green('✔')} ${c.bold('Project discovered')} ${c.dim(`(${context.files.size} files, ${context.tree.length} entries)`)}`);

    if (options.verbose) {
      console.error(`[verbose] Project tree:\n${context.tree.map((t: string) => `  ${t}`).join('\n')}`);
    }

    // 2. Assess project
    const spinner2 = createSpinner(`${c.yellow('Assessing project with AI')} ${c.dim('(this may take a moment...)')}`);
    const assessStart = Date.now();
    let conversionModel: ConversionModel;
    try {
      conversionModel = await assessProject(context, { verbose: !!options.verbose, model, timeout });
    } catch (err) {
      // Retry once
      spinner2.stop(`${c.yellow('⚠')}  ${c.bold('Assessment failed, retrying...')}`);
      if (options.verbose) {
        console.error(`[verbose] Assessment error: ${(err as Error).message}`);
      }
      const spinner2b = createSpinner(c.yellow('Retrying assessment...'));
      try {
        conversionModel = await assessProject(context, { verbose: !!options.verbose, model, timeout });
        spinner2b.stop(`${c.green('✔')} ${c.bold('Assessment succeeded on retry')}`);
      } catch (retryErr) {
        spinner2b.stop('');
        stopAllSpinners();
        console.error(`\n${c.red('✖')} ${c.red('Assessment failed after retry')} — ${(retryErr as Error).message}`);
        process.exit(1);
      }
    }
    const assessElapsed = ((Date.now() - assessStart) / 1000).toFixed(1);
    spinner2.stop(`${c.green('✔')} ${c.bold('Assessment complete')} ${c.dim(`(${assessElapsed}s)`)}`);

    if (options.debug) {
      console.error(`\n${c.cyan('━━━ Conversion Model ━━━')}`);
      console.error(JSON.stringify(conversionModel, null, 2));
      console.error(`${c.cyan('━━━ End Conversion Model ━━━')}\n`);
    }

    // 3. Save conversion model
    await mkdir(options.output, { recursive: true });
    await writeFile(
      join(options.output, 'conversion-model.json'),
      JSON.stringify(conversionModel, null, 2),
      'utf-8',
    );
    console.error(`${c.green('✔')} ${c.bold('Conversion model saved')} ${c.dim(`→ ${join(options.output, 'conversion-model.json')}`)}`);

    // 4. Scaffold project structure
    const spinner4 = createSpinner(c.dim('Scaffolding Logic Apps project...'));
    await scaffoldProject(conversionModel, options.output);
    spinner4.stop(`${c.green('✔')} ${c.bold('Project scaffolded')}`);

    // 5. Convert each workflow
    let converted = 0;
    let skipped = 0;
    let errors = 0;

    for (const app of conversionModel.target.logicAppsStandardApps) {
      console.error(`\n${c.bold(`📦 ${app.name}`)} ${c.dim(app.rationale || '')}`);

      for (const workflow of app.workflows) {
        const impl = workflow.recommendedImplementation;
        if (impl !== 'workflow' && impl !== 'child-workflow') {
          console.error(`${c.dim('  ⏭')}  ${workflow.name} ${c.dim(`(${impl} — skipped)`)}`);
          skipped++;
          continue;
        }

        const spinner = createSpinner(`  ${c.yellow(workflow.name)} ${c.dim('converting...')}`);
        try {
          // Read source artifacts
          const xmlParts: string[] = [];
          for (const artifact of workflow.sourceArtifacts) {
            const fullPath = join(context.rootPath, artifact);
            try {
              const content = await readFile(fullPath, 'utf-8');
              xmlParts.push(content);
            } catch {
              if (options.verbose) {
                console.error(`[verbose] Could not read source artifact: ${fullPath}`);
              }
            }
          }

          if (xmlParts.length === 0) {
            spinner.stop(`${c.yellow('⚠')}  ${workflow.name} ${c.dim('(no source artifacts readable)')}`);
            skipped++;
            continue;
          }

          const xml = xmlParts.join('\n');

          // Build prompt and call Copilot
          const prompt = buildPrompt(xml);
          const wfStart = Date.now();
          let response = await runCopilot(prompt, { verbose: !!options.verbose, model, timeout });

          // Validate (retry once)
          let parsed: WorkflowDefinition;
          try {
            parsed = validateJson(response);
          } catch {
            response = await runCopilot(prompt, { verbose: !!options.verbose, model, timeout });
            parsed = validateJson(response);
          }

          // Review (unless --no-review)
          if (!options.noReview) {
            try {
              const { workflow: reviewed } = await reviewWorkflow(xml, parsed, { verbose: !!options.verbose, model, timeout });
              parsed = reviewed;
            } catch {
              // Use original on review failure
            }
          }

          // Write workflow.json
          const workflowDir = join(options.output, app.name, workflow.name);
          await mkdir(workflowDir, { recursive: true });
          await writeFile(
            join(workflowDir, 'workflow.json'),
            JSON.stringify(parsed, null, 2),
            'utf-8',
          );

          const wfElapsed = ((Date.now() - wfStart) / 1000).toFixed(1);
          spinner.stop(`  ${c.green('✔')} ${c.bold(workflow.name)} ${c.dim(`(${wfElapsed}s)`)}`);
          converted++;
        } catch (err) {
          spinner.stop(`  ${c.red('✖')} ${c.bold(workflow.name)} ${c.red((err as Error).message)}`);
          errors++;
        }
      }
    }

    // 6. Summary
    console.error(`\n${c.bold('━━━ Summary ━━━')}`);
    console.error(`  ${c.green('✔')} Converted: ${converted}`);
    if (skipped > 0) console.error(`  ${c.dim('⏭')}  Skipped:   ${skipped}`);
    if (errors > 0) console.error(`  ${c.red('✖')} Errors:    ${errors}`);
    console.error(`  ${c.dim('📁')} Output:    ${options.output}`);
    console.error(`\n${c.green('🎉 Project conversion complete!')}\n`);
  } catch (err) {
    stopAllSpinners();
    console.error(`\n${c.red('✖')} ${c.red('Error:')} ${(err as Error).message}`);
    process.exit(1);
  }
}
