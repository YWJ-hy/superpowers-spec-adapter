import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import * as z from 'zod/v4';
import type { SharedWikiConfig } from './config.js';
import { statusTool } from './tools/status.js';
import { treeTool } from './tools/tree.js';
import { readTool } from './tools/read.js';
import { searchTool } from './tools/search.js';
import { validatePatchTool } from './tools/validatePatch.js';
import { createPatchPrTool } from './tools/createPatchPr.js';

export function createServer(config: SharedWikiConfig): McpServer {
  const server = new McpServer({ name: 'shared-wiki-mcp', version: '0.1.0' });

  server.registerTool('shared_wiki_status', {
    description: 'Check shared wiki MCP configuration, clone state, tool availability, policy, and wiki validation summary.',
    inputSchema: z.object({}),
    annotations: { readOnlyHint: true, idempotentHint: true },
  }, async () => toResult(await statusTool(config)));

  server.registerTool('shared_wiki_tree', {
    description: 'Return the index-driven shared wiki tree.',
    inputSchema: z.object({}),
    annotations: { readOnlyHint: true, idempotentHint: true },
  }, async () => toResult(await treeTool(config)));

  server.registerTool('shared_wiki_read', {
    description: 'Read one indexed shared wiki markdown page.',
    inputSchema: z.object({ path: z.string().min(1) }),
    annotations: { readOnlyHint: true, idempotentHint: true },
  }, async (input) => toResult(await readTool(config, input)));

  server.registerTool('shared_wiki_search', {
    description: 'Search indexed shared wiki markdown pages with bounded snippets.',
    inputSchema: z.object({ query: z.string().min(1), maxResults: z.number().int().min(1).max(50).optional() }),
    annotations: { readOnlyHint: true, idempotentHint: true },
  }, async (input) => toResult(await searchTool(config, input)));

  server.registerTool('shared_wiki_validate_patch', {
    description: 'Validate a unified diff against shared wiki policy without pushing or opening a PR.',
    inputSchema: z.object({
      patch: z.string().min(1),
      authorizedCreate: z.boolean().optional(),
      authorizedUpdate: z.boolean().optional(),
    }),
  }, async (input) => toResult(await validatePatchTool(config, input)));

  server.registerTool('shared_wiki_create_patch_pr', {
    description: 'Apply a validated shared wiki patch on a new branch, push it, and open a GitHub PR. Never merges.',
    inputSchema: z.object({
      patch: z.string().min(1),
      branchName: z.string().min(1).optional(),
      commitMessage: z.string().min(1),
      prTitle: z.string().min(1),
      prBody: z.string().min(1),
      authorizedCreate: z.boolean().optional(),
      authorizedUpdate: z.boolean().optional(),
      draft: z.boolean().optional(),
    }),
  }, async (input) => toResult(await createPatchPrTool(config, input)));

  return server;
}

function toResult(value: unknown) {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(value, null, 2) }],
    structuredContent: value as Record<string, unknown>,
  };
}
