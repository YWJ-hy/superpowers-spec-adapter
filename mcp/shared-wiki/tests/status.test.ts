import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { SharedWikiConfig } from '../src/config.js';
import { spawnFile } from '../src/process.js';
import { readTool } from '../src/tools/read.js';
import { searchTool } from '../src/tools/search.js';
import { statusTool } from '../src/tools/status.js';
import { treeTool } from '../src/tools/tree.js';

function config(repoUrl: string, cacheDir: string): SharedWikiConfig {
  return {
    repoUrl,
    baseBranch: 'main',
    remote: 'origin',
    wikiRoot: '.',
    displayRoot: '.shared-superpowers/wiki',
    cacheDir,
    cloneDir: path.join(cacheDir, 'clone'),
    draftPr: true,
  };
}

async function createRemoteRepo(): Promise<{ repoUrl: string; commitSha: string }> {
  const repoUrl = mkdtempSync(path.join(tmpdir(), 'shared-wiki-remote-'));
  await spawnFile('git', ['init', '-b', 'main'], { cwd: repoUrl });
  await spawnFile('git', ['config', 'user.email', 'test@example.com'], { cwd: repoUrl });
  await spawnFile('git', ['config', 'user.name', 'Test User'], { cwd: repoUrl });
  writeFileSync(path.join(repoUrl, 'index.md'), '# Index\n\n- [API](api.md)\n');
  writeFileSync(path.join(repoUrl, 'api.md'), '# API\n\nReusable API contract.\n');
  await spawnFile('git', ['add', '.'], { cwd: repoUrl });
  await spawnFile('git', ['commit', '-m', 'Initial shared wiki'], { cwd: repoUrl });
  const output = await spawnFile('git', ['rev-parse', 'HEAD'], { cwd: repoUrl });
  return { repoUrl, commitSha: output.stdout.trim() };
}

describe('shared wiki tool revisions', () => {
  it('returns revision from status, tree, read, and search tools', async () => {
    const { repoUrl, commitSha } = await createRemoteRepo();
    const cacheDir = mkdtempSync(path.join(tmpdir(), 'shared-wiki-cache-'));
    mkdirSync(cacheDir, { recursive: true });
    const sharedConfig = config(repoUrl, cacheDir);

    const status = await statusTool(sharedConfig);
    expect(status.revision?.ref).toBe('origin/main');
    expect(status.revision?.commitSha).toBe(commitSha);
    expect(status.revision?.shortSha).toBe(commitSha.slice(0, 12));

    const tree = await treeTool(sharedConfig);
    expect(tree.revision.commitSha).toBe(commitSha);
    expect(tree.files.map((file) => file.path)).toContain('api.md');

    const read = await readTool(sharedConfig, { path: 'api.md' });
    expect(read.revision.commitSha).toBe(commitSha);
    expect(read.content).toContain('Reusable API contract');

    const search = await searchTool(sharedConfig, { query: 'contract' });
    expect(search.revision.commitSha).toBe(commitSha);
    expect(search.results[0]?.path).toBe('api.md');
  });
});
