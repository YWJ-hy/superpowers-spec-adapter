#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadConfig } from './config.js';
import { createServer } from './server.js';
import { runReadSectionsCliFromStdin } from './cli.js';

async function startServer(): Promise<void> {
  const config = loadConfig();
  const server = createServer(config);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

async function main(): Promise<void> {
  // No subcommand: Claude Code launches `node dist/index.js` with no args -> stdio MCP server.
  // `read-sections`: same binary invoked as a CLI (`node dist/index.js read-sections`) that reuses
  // the server's loadConfig + readSectionsTool so a non-MCP caller shares one shared-wiki reader.
  const subcommand = process.argv[2];
  if (subcommand === 'read-sections') {
    await runReadSectionsCliFromStdin();
    return;
  }
  if (subcommand !== undefined) {
    throw new Error(
      `Unknown subcommand: ${subcommand}. Run with no arguments to start the MCP stdio server, ` +
        "or 'read-sections' to read sections from a JSON request on stdin.",
    );
  }
  await startServer();
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
