import { readFileSync } from 'node:fs';
import type { SharedWikiConfig } from '../config.js';
import { prepareBase } from '../git.js';
import { indexedFiles } from '../wiki/indexGraph.js';
import { absoluteWikiFilePath, displayPath, normalizeWikiRelativePath } from '../wiki/paths.js';

export async function readTool(config: SharedWikiConfig, input: { path: string }) {
  await prepareBase(config);
  const wikiPath = normalizeWikiRelativePath(input.path);
  if (!indexedFiles(config).has(wikiPath)) {
    throw new Error(`Wiki page is not indexed: ${input.path}`);
  }
  return {
    path: wikiPath,
    displayPath: displayPath(config, wikiPath),
    content: readFileSync(absoluteWikiFilePath(config, wikiPath), 'utf8'),
  };
}
