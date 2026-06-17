import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type { SharedWikiConfig } from '../config.js';
import { currentHeadRevision, prepareBase } from '../git.js';
import { isCompanionIndexForIndexedLeaf } from '../wiki/indexGraph.js';
import { wikiRootPath } from '../wiki/paths.js';

const GRAPH_FILE = '.graph.json';

type OutEdge = { to: string; type?: string; indexed: boolean };
type InEdge = { from: string; type?: string; indexed: boolean };
type Slice = { out: OutEdge[]; in: InEdge[] };

function emptyNeighbors(nodes: string[]): Record<string, Slice> {
  return Object.fromEntries(nodes.map((node) => [node, { out: [], in: [] }]));
}

function companionIndexRel(node: string): string | null {
  const page = node.split('#', 1)[0] ?? node;
  if (!page.endsWith('.md')) return null;
  return `${page.slice(0, -'.md'.length)}.index.md`;
}

// `indexed` means the neighbor is usable through this shared wiki graph: its companion
// section index exists AND its leaf is index-reachable (so a follow-up read won't be
// rejected by the read whitelist). Mirrors the local CLI's companion-existence gate.
function isIndexedNeighbor(config: SharedWikiConfig, node: string): boolean {
  const companion = companionIndexRel(node);
  if (!companion) return false;
  try {
    return isCompanionIndexForIndexedLeaf(config, companion);
  } catch {
    return false;
  }
}

export async function graphNeighborsTool(config: SharedWikiConfig, input: { nodes: string[] }) {
  await prepareBase(config);
  const revision = await currentHeadRevision(config);
  const graphPath = path.join(wikiRootPath(config), GRAPH_FILE);

  if (!existsSync(graphPath)) {
    return {
      revision,
      neighbors: emptyNeighbors(input.nodes),
      caveats: [`${GRAPH_FILE} not found at shared wiki root; no neighbors available`],
    };
  }

  let graph: unknown;
  try {
    graph = JSON.parse(readFileSync(graphPath, 'utf8'));
  } catch (error) {
    return {
      revision,
      neighbors: emptyNeighbors(input.nodes),
      caveats: [`could not parse ${GRAPH_FILE}: ${error instanceof Error ? error.message : String(error)}`],
    };
  }

  const edges = (graph as { edges?: unknown }).edges;
  const outByNode = new Map<string, Array<{ to: string; type?: string }>>();
  if (Array.isArray(edges)) {
    for (const edge of edges) {
      if (!edge || typeof edge !== 'object') continue;
      const from = (edge as { from?: unknown }).from;
      const to = (edge as { to?: unknown }).to;
      if (typeof from !== 'string' || typeof to !== 'string') continue;
      const list = outByNode.get(from) ?? [];
      list.push({ to, type: (edge as { type?: string }).type });
      outByNode.set(from, list);
    }
  }

  const backlinksRaw = (graph as { backlinks?: unknown }).backlinks;
  const backlinks = backlinksRaw && typeof backlinksRaw === 'object' ? (backlinksRaw as Record<string, unknown>) : {};

  const neighbors: Record<string, Slice> = {};
  for (const node of input.nodes) {
    const out: OutEdge[] = (outByNode.get(node) ?? []).map((edge) => ({
      to: edge.to,
      type: edge.type,
      indexed: isIndexedNeighbor(config, edge.to),
    }));
    const incomingRaw = backlinks[node];
    const incoming: InEdge[] = Array.isArray(incomingRaw)
      ? incomingRaw
          .filter(
            (src): src is { from: string; type?: string } =>
              !!src && typeof src === 'object' && typeof (src as { from?: unknown }).from === 'string',
          )
          .map((src) => ({ from: src.from, type: src.type, indexed: isIndexedNeighbor(config, src.from) }))
      : [];
    neighbors[node] = { out, in: incoming };
  }

  return { revision, neighbors };
}
