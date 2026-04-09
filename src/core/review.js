import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { runCopilot } from './copilot.js';
import { validateJson, validateWorkflowStructure } from './validate.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REVIEW_PROMPT = readFileSync(
  join(__dirname, '..', 'prompts', 'review.prompt.md'),
  'utf-8'
).trim();

/**
 * Runs the review agent: sends the original XML + generated JSON back through
 * Copilot with a validation-focused system prompt. Returns the (possibly corrected)
 * parsed workflow object.
 */
export async function reviewWorkflow(xml, parsed, { verbose = false, model } = {}) {
  const structuralIssues = validateWorkflowStructure(parsed);

  if (structuralIssues.length === 0) {
    if (verbose) {
      console.error('[review] Structural validation passed, running AI review...');
    }
  } else {
    if (verbose) {
      console.error('[review] Structural issues found:');
      for (const issue of structuralIssues) {
        console.error(`[review]   - ${issue}`);
      }
    }
  }

  const reviewPrompt = buildReviewPrompt(xml, parsed, structuralIssues);

  const response = await runCopilot(reviewPrompt, {
    verbose,
    systemPrompt: REVIEW_PROMPT,
    model,
  });

  const reviewed = validateJson(response);
  const postReviewIssues = validateWorkflowStructure(reviewed);

  if (verbose && postReviewIssues.length > 0) {
    console.error('[review] Post-review issues remain:');
    for (const issue of postReviewIssues) {
      console.error(`[review]   - ${issue}`);
    }
  }

  return { workflow: reviewed, issues: postReviewIssues };
}

function buildReviewPrompt(xml, parsed, issues) {
  let prompt = `Review and validate this Azure Logic Apps workflow that was converted from MuleSoft XML.

<original-mulesoft-xml>
${xml}
</original-mulesoft-xml>

<converted-workflow-json>
${JSON.stringify(parsed, null, 2)}
</converted-workflow-json>`;

  if (issues.length > 0) {
    prompt += `

<structural-issues-detected>
${issues.map((i) => `- ${i}`).join('\n')}
</structural-issues-detected>

Fix the structural issues listed above and return the corrected workflow JSON.`;
  } else {
    prompt += `

Verify this workflow is correct and complete. If it is valid, return it as-is. If you find any issues, return the corrected version.`;
  }

  prompt += `

Respond with ONLY the raw JSON object. No markdown, no code fences, no explanation.`;

  return prompt;
}
