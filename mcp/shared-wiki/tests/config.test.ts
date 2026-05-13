import { describe, expect, it } from 'vitest';
import { loadConfig } from '../src/config.js';

describe('loadConfig', () => {
  it('requires a repo URL', () => {
    expect(() => loadConfig({})).toThrow(/Missing shared wiki repo URL/);
  });

  it('loads environment config', () => {
    const config = loadConfig({
      SHARED_WIKI_MCP_REPO_URL: 'https://github.com/YWJ-hy/shared-wiki.git',
      SHARED_WIKI_MCP_BASE_BRANCH: 'main',
    });
    expect(config.repoUrl).toBe('https://github.com/YWJ-hy/shared-wiki.git');
    expect(config.baseBranch).toBe('main');
    expect(config.displayRoot).toBe('.shared-superpowers/wiki');
  });

  it('rejects absolute wiki roots', () => {
    expect(() => loadConfig({
      SHARED_WIKI_MCP_REPO_URL: 'x',
      SHARED_WIKI_MCP_WIKI_ROOT: '/tmp/wiki',
    })).toThrow(/wikiRoot must be a relative path/);
  });
});
