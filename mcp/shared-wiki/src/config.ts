import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import * as z from 'zod/v4';

const ConfigFileSchema = z.object({
  repoUrl: z.string().min(1).optional(),
  baseBranch: z.string().min(1).optional(),
  remote: z.string().min(1).optional(),
  wikiRoot: z.string().min(1).optional(),
  displayRoot: z.string().min(1).optional(),
  cacheDir: z.string().min(1).optional(),
  draftPr: z.boolean().optional(),
});

export type SharedWikiConfig = {
  repoUrl: string;
  baseBranch: string;
  remote: string;
  wikiRoot: string;
  displayRoot: string;
  cacheDir: string;
  cloneDir: string;
  draftPr: boolean;
};

function expandHome(input: string): string {
  if (input === '~') return homedir();
  if (input.startsWith('~/')) return path.join(homedir(), input.slice(2));
  return input;
}

function readConfigFile(configPath: string | undefined): Partial<z.infer<typeof ConfigFileSchema>> {
  if (!configPath) return {};
  const absolutePath = path.resolve(expandHome(configPath));
  if (!existsSync(absolutePath)) {
    throw new Error(`Config file not found: ${absolutePath}`);
  }
  const parsed = JSON.parse(readFileSync(absolutePath, 'utf8')) as unknown;
  return ConfigFileSchema.parse(parsed);
}

function repoCacheName(repoUrl: string): string {
  const digest = createHash('sha256').update(repoUrl).digest('hex').slice(0, 16);
  return `repo-${digest}`;
}

function normalizeRelativeRoot(value: string, field: string): string {
  if (path.isAbsolute(value)) {
    throw new Error(`${field} must be a relative path`);
  }
  const normalized = path.posix.normalize(value.replaceAll('\\', '/'));
  if (normalized === '..' || normalized.startsWith('../')) {
    throw new Error(`${field} must stay inside the shared wiki repository`);
  }
  return normalized === '.' ? '.' : normalized.replace(/^\.\//, '');
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): SharedWikiConfig {
  const fileConfig = readConfigFile(env.SHARED_WIKI_MCP_CONFIG);
  const repoUrl = env.SHARED_WIKI_MCP_REPO_URL ?? fileConfig.repoUrl;
  if (!repoUrl) {
    throw new Error('Missing shared wiki repo URL. Set SHARED_WIKI_MCP_REPO_URL or repoUrl in SHARED_WIKI_MCP_CONFIG.');
  }

  const baseCacheDir = expandHome(env.SHARED_WIKI_MCP_CACHE_DIR ?? fileConfig.cacheDir ?? '~/.cache/superpower-adapter/shared-wiki-mcp');
  const cacheDir = path.resolve(baseCacheDir);
  const wikiRoot = normalizeRelativeRoot(env.SHARED_WIKI_MCP_WIKI_ROOT ?? fileConfig.wikiRoot ?? '.', 'wikiRoot');
  const displayRoot = normalizeRelativeRoot(env.SHARED_WIKI_MCP_DISPLAY_ROOT ?? fileConfig.displayRoot ?? '.shared-superpowers/wiki', 'displayRoot');

  return {
    repoUrl,
    baseBranch: env.SHARED_WIKI_MCP_BASE_BRANCH ?? fileConfig.baseBranch ?? 'main',
    remote: env.SHARED_WIKI_MCP_REMOTE ?? fileConfig.remote ?? 'origin',
    wikiRoot,
    displayRoot,
    cacheDir,
    cloneDir: path.join(cacheDir, repoCacheName(repoUrl)),
    draftPr: fileConfig.draftPr ?? true,
  };
}
