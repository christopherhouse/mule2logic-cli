export const SYSTEM_PROMPT = `You are an expert Azure Integration Architect.

Convert MuleSoft flows into Azure Logic Apps Standard workflows.

Rules:
- Output ONLY valid JSON
- No markdown
- Include triggers and actions
- Preserve logic
- Use Azure best practices`;

export function buildPrompt(xml) {
  return `Convert MuleSoft XML to Logic Apps JSON:

${xml}

Return only JSON.`;
}
