import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import type { SharedWikiConfig } from '../config.js';
import { absoluteWikiFilePath, displayPath, normalizeWikiRelativePath } from './paths.js';

export type WikiNode = {
  path: string;
  displayPath: string;
  title: string;
};

const LINK_RE = /\[[^\]]+\]\(([^)]+\.md)(?:#[^)]+)?\)/g;

export function indexedFiles(config: SharedWikiConfig): Set<string> {
  const visited = new Set<string>();
  const queue = ['index.md'];
  while (queue.length > 0) {
    const current = normalizeWikiRelativePath(queue.shift() ?? 'index.md');
    if (visited.has(current)) continue;
    const absolute = absoluteWikiFilePath(config, current);
    if (!existsSync(absolute)) continue;
    visited.add(current);
    const content = readFileSync(absolute, 'utf8');
    const currentDir = path.posix.dirname(current) === '.' ? '' : path.posix.dirname(current);
    for (const target of extractMarkdownLinks(content)) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith('#')) continue;
      const withoutAnchor = target.split('#')[0] ?? target;
      const next = normalizeWikiRelativePath(path.posix.normalize(path.posix.join(currentDir, withoutAnchor)));
      queue.push(next);
    }
  }
  return visited;
}

export function tree(config: SharedWikiConfig): WikiNode[] {
  return [...indexedFiles(config)].sort().map((wikiPath) => ({
    path: wikiPath,
    displayPath: displayPath(config, wikiPath),
    title: firstHeading(absoluteWikiFilePath(config, wikiPath)) ?? wikiPath,
  }));
}

export function validateIndexGraph(config: SharedWikiConfig): string[] {
  const errors: string[] = [];
  const rootIndex = absoluteWikiFilePath(config, 'index.md');
  if (!existsSync(rootIndex)) {
    return ['Shared wiki is missing index.md.'];
  }

  for (const wikiPath of indexedFiles(config)) {
    const absolute = absoluteWikiFilePath(config, wikiPath);
    const content = readFileSync(absolute, 'utf8');
    const currentDir = path.posix.dirname(wikiPath) === '.' ? '' : path.posix.dirname(wikiPath);
    for (const target of extractMarkdownLinks(content)) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith('#')) continue;
      const withoutAnchor = target.split('#')[0] ?? target;
      let next: string;
      try {
        next = normalizeWikiRelativePath(path.posix.normalize(path.posix.join(currentDir, withoutAnchor)));
      } catch (error) {
        errors.push(`${wikiPath} has unsafe markdown link: ${target}`);
        continue;
      }
      if (!existsSync(absoluteWikiFilePath(config, next))) {
        errors.push(`${wikiPath} links to missing wiki page: ${next}`);
      }
    }
  }
  return errors;
}

export function allMarkdownFiles(config: SharedWikiConfig): string[] {
  const root = path.join(config.cloneDir, config.wikiRoot);
  if (!existsSync(root)) return [];
  const results: string[] = [];
  walk(root, root, results);
  return results.sort();
}

function walk(root: string, current: string, results: string[]): void {
  for (const entry of readdirSync(current)) {
    const absolute = path.join(current, entry);
    const stat = statSync(absolute);
    if (stat.isDirectory()) {
      if (entry === '.git' || entry === 'node_modules') continue;
      walk(root, absolute, results);
    } else if (stat.isFile() && entry.endsWith('.md')) {
      results.push(path.relative(root, absolute).replaceAll('\\', '/'));
    }
  }
}

function extractMarkdownLinks(content: string): string[] {
  const links: string[] = [];
  for (const match of content.matchAll(LINK_RE)) {
    links.push(match[1] ?? '');
  }
  return links.filter(Boolean);
}

function firstHeading(absolutePath: string): string | undefined {
  const content = readFileSync(absolutePath, 'utf8');
  const line = content.split('\n').find((candidate) => candidate.startsWith('# '));
  return line?.replace(/^#\s+/, '').trim();
}
