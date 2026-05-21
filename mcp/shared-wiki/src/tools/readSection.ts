import { readFileSync } from 'node:fs';
import type { SharedWikiConfig } from '../config.js';
import { currentHeadRevision, prepareBase } from '../git.js';
import { indexedFiles } from '../wiki/indexGraph.js';
import { absoluteWikiFilePath, displayPath, normalizeWikiRelativePath } from '../wiki/paths.js';
import { extractSection, listSectionIds } from '../wiki/sections.js';

export async function readSectionTool(config: SharedWikiConfig, input: { path: string; section: string }) {
  await prepareBase(config);
  const revision = await currentHeadRevision(config);
  const wikiPath = normalizeWikiRelativePath(input.path);
  if (!indexedFiles(config).has(wikiPath)) {
    throw new Error(`Wiki page is not indexed: ${input.path}`);
  }
  const content = readFileSync(absoluteWikiFilePath(config, wikiPath), 'utf8');
  const sectionContent = extractSection(content, input.section);
  if (sectionContent === null) {
    const available = listSectionIds(content);
    const hint = available.length > 0
      ? `Available sections: ${available.join(', ')}`
      : 'No section markers found in this file.';
    throw new Error(`Section '${input.section}' not found in ${wikiPath}. ${hint}`);
  }
  return {
    path: wikiPath,
    section: input.section,
    displayPath: displayPath(config, wikiPath),
    revision,
    content: sectionContent,
  };
}
