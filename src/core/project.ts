import { readFile, readdir, stat } from 'fs/promises';
import { join, relative, extname } from 'path';

const MAX_FILE_SIZE = 50 * 1024; // 50KB cap per file

const INCLUDE_PATTERNS = [
  'pom.xml',
  'mule-artifact.json',
];

const INCLUDE_DIRS = [
  'src/main/mule',
  'src/main/resources',
  'src/test/munit',
];

const INCLUDE_EXTENSIONS = new Set([
  '.xml', '.dwl', '.properties', '.yaml', '.yml',
  '.raml', '.json', '.wsdl', '.xsd',
]);

export interface ProjectContext {
  rootPath: string;
  tree: string[];
  files: Map<string, string>;
}

export async function discoverProject(rootPath: string): Promise<ProjectContext> {
  let rootStat;
  try {
    rootStat = await stat(rootPath);
  } catch {
    throw new Error(`Project path not found: ${rootPath}`);
  }
  if (!rootStat.isDirectory()) {
    throw new Error(`Project path is not a directory: ${rootPath}`);
  }

  const tree: string[] = [];
  const files = new Map<string, string>();

  // Read root-level include files
  for (const name of INCLUDE_PATTERNS) {
    const fullPath = join(rootPath, name);
    const content = await tryReadFile(fullPath);
    if (content !== null) {
      tree.push(name);
      files.set(name, content);
    }
  }

  // Recursively read include directories
  for (const dir of INCLUDE_DIRS) {
    const fullDir = join(rootPath, dir);
    try {
      await stat(fullDir);
    } catch {
      continue; // directory doesn't exist, skip
    }
    await walkDir(fullDir, rootPath, tree, files);
  }

  // Scan root for additional config files (application*.properties, application*.yaml)
  try {
    const rootEntries = await readdir(rootPath, { withFileTypes: true });
    for (const entry of rootEntries) {
      if (!entry.isFile()) continue;
      const name = entry.name.toLowerCase();
      if (
        (name.startsWith('application') && (name.endsWith('.properties') || name.endsWith('.yaml') || name.endsWith('.yml'))) ||
        name.endsWith('.raml') || name.endsWith('.wsdl') || name.endsWith('.xsd')
      ) {
        const relPath = entry.name;
        if (!files.has(relPath)) {
          const content = await tryReadFile(join(rootPath, relPath));
          if (content !== null) {
            tree.push(relPath);
            files.set(relPath, content);
          }
        }
      }
    }
  } catch {
    // ignore read errors on root
  }

  if (files.size === 0) {
    throw new Error(`No MuleSoft artifacts found in: ${rootPath}`);
  }

  tree.sort();
  return { rootPath, tree, files };
}

async function walkDir(
  dir: string,
  rootPath: string,
  tree: string[],
  files: Map<string, string>,
): Promise<void> {
  let entries;
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    const relPath = relative(rootPath, fullPath).replace(/\\/g, '/');

    if (entry.isDirectory()) {
      tree.push(relPath + '/');
      await walkDir(fullPath, rootPath, tree, files);
    } else if (entry.isFile() && INCLUDE_EXTENSIONS.has(extname(entry.name).toLowerCase())) {
      const content = await tryReadFile(fullPath);
      if (content !== null) {
        tree.push(relPath);
        files.set(relPath, content);
      }
    }
  }
}

async function tryReadFile(filePath: string): Promise<string | null> {
  try {
    const fileStat = await stat(filePath);
    if (fileStat.size > MAX_FILE_SIZE) {
      return `[File truncated — ${fileStat.size} bytes exceeds ${MAX_FILE_SIZE} byte limit]`;
    }
    return await readFile(filePath, 'utf-8');
  } catch {
    return null;
  }
}
