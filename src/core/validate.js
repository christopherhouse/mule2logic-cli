export function validateJson(output) {
  if (typeof output !== 'string' || output.trim() === '') {
    throw new Error('Output is empty or not a string');
  }

  let cleaned = output.trim();

  // Strip markdown code fences if present
  const fenceMatch = cleaned.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?\s*```$/);
  if (fenceMatch) {
    cleaned = fenceMatch[1].trim();
  }

  let parsed;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    throw new Error('Output is not valid JSON');
  }

  if (!parsed.definition || typeof parsed.definition !== 'object') {
    throw new Error('Missing required "definition" property');
  }

  if (!parsed.definition.actions || typeof parsed.definition.actions !== 'object') {
    throw new Error('Missing required "definition.actions" property');
  }

  return parsed;
}
