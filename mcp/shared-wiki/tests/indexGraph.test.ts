import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { SharedWikiConfig } from '../src/config.js';
import { indexedFiles, validateIndexGraph } from '../src/wiki/indexGraph.js';

function config(root: string): SharedWikiConfig {
  return {
    repoUrl: 'local',
    baseBranch: 'main',
    remote: 'origin',
    wikiRoot: '.',
    displayRoot: '.shared-superpowers/wiki',
    cacheDir: root,
    cloneDir: root,
    draftPr: true,
  };
}

describe('index graph', () => {
  it('follows markdown links from index', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'shared-wiki-index-'));
    mkdirSync(path.join(root, 'contracts'));
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- [API](contracts/api.md)\n');
    writeFileSync(path.join(root, 'contracts/api.md'), '# API\n');
    writeFileSync(path.join(root, 'unindexed.md'), '# Hidden\n');
    expect([...indexedFiles(config(root))].sort()).toEqual(['contracts/api.md', 'index.md']);
  });

  it('reports missing linked files', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'shared-wiki-missing-'));
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- [Missing](missing.md)\n');
    expect(validateIndexGraph(config(root))[0]).toMatch(/missing wiki page/);
  });
});
