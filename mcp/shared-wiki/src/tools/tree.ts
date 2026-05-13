import type { SharedWikiConfig } from '../config.js';
import { prepareBase } from '../git.js';
import { tree } from '../wiki/indexGraph.js';

export async function treeTool(config: SharedWikiConfig) {
  await prepareBase(config);
  return { files: tree(config) };
}
