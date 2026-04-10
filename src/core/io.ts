import { readFile } from 'fs/promises';

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks).toString('utf-8');
}

export async function readInput(filePath?: string): Promise<string> {
  let content: string;

  if (filePath) {
    try {
      content = await readFile(filePath, 'utf-8');
    } catch (err: unknown) {
      if (err instanceof Error && (err as NodeJS.ErrnoException).code === 'ENOENT') {
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
