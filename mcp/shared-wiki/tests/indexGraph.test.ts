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

function tempRoot(prefix: string): string {
  return mkdtempSync(path.join(tmpdir(), prefix));
}

describe('index graph', () => {
  it('follows markdown links from index', () => {
    const root = tempRoot('shared-wiki-index-');
    mkdirSync(path.join(root, 'contracts'));
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- [API](contracts/api.md)\n');
    writeFileSync(path.join(root, 'contracts/api.md'), '# API\n');
    writeFileSync(path.join(root, 'unindexed.md'), '# Hidden\n');
    expect([...indexedFiles(config(root))].sort()).toEqual(['contracts/api.md', 'index.md']);
  });

  it('follows backtick refs, bullet refs, and directory refs', () => {
    const root = tempRoot('shared-wiki-refs-');
    mkdirSync(path.join(root, 'contracts'));
    mkdirSync(path.join(root, 'guides'));
    writeFileSync(path.join(root, 'index.md'), [
      '# Index',
      '',
      '- `contracts/api.md`',
      '- guides/',
      '- contracts/events.md',
      '',
    ].join('\n'));
    writeFileSync(path.join(root, 'contracts/api.md'), '# API\n');
    writeFileSync(path.join(root, 'contracts/events.md'), '# Events\n');
    writeFileSync(path.join(root, 'guides/index.md'), '# Guides\n\n- [Review](review.md#checklist)\n');
    writeFileSync(path.join(root, 'guides/review.md'), '# Review\n');

    expect([...indexedFiles(config(root))].sort()).toEqual([
      'contracts/api.md',
      'contracts/events.md',
      'guides/index.md',
      'guides/review.md',
      'index.md',
    ]);
  });

  it('does not follow references from leaf page prose', () => {
    const root = tempRoot('shared-wiki-leaf-prose-');
    mkdirSync(path.join(root, 'frontend'));
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- frontend/hook-guidelines.md\n');
    writeFileSync(path.join(root, 'frontend/hook-guidelines.md'), [
      '# Hook Guidelines',
      '',
      'Place related files near `hooks/` or sibling feature directories.',
      'See [Missing](missing.md) only as prose in this leaf page.',
      '',
    ].join('\n'));

    expect([...indexedFiles(config(root))].sort()).toEqual(['frontend/hook-guidelines.md', 'index.md']);
    expect(validateIndexGraph(config(root))).toEqual([]);
  });

  it('ignores refs inside fenced code blocks', () => {
    const root = tempRoot('shared-wiki-fenced-');
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n```\n- hidden.md\n```\n');
    writeFileSync(path.join(root, 'hidden.md'), '# Hidden\n');

    expect([...indexedFiles(config(root))].sort()).toEqual(['index.md']);
  });

  it('reports missing linked files', () => {
    const root = tempRoot('shared-wiki-missing-');
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- [Missing](missing.md)\n');
    expect(validateIndexGraph(config(root))[0]).toMatch(/missing wiki page/);
  });

  it('reports unsafe linked files', () => {
    const root = tempRoot('shared-wiki-unsafe-');
    writeFileSync(path.join(root, 'index.md'), '# Index\n\n- ../secret.md\n- .hidden.md\n- examples/demo.md\n');
    const errors = validateIndexGraph(config(root));
    expect(errors.some((error) => error.includes('inside wiki root'))).toBe(true);
    expect(errors.some((error) => error.includes('hidden path segments'))).toBe(true);
    expect(errors.some((error) => error.includes('ignored directory'))).toBe(true);
  });
});
