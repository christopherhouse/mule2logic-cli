import { readFile } from 'fs/promises';

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf-8");
}

export async function readInput(filePath) {
  let content;

  if (filePath) {
    try {
      content = await readFile(filePath, 'utf-8');
    } catch (err) {
      if (err.code === 'ENOENT') {
        throw new Error(`File not found: ${filePath}`);
      }
      throw err;
    }
  } else {
    content = await readStdin();
  }

  if (!content || content.trim().length === 0) {
    throw new Error('Input is empty');
  }

  return content;
}
