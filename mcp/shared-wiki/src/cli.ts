import { loadConfig } from './config.js';
import { withCloneLock } from './lock.js';
import { readSectionsTool, type BatchSectionReadResult } from './tools/readSections.js';
import type { SectionReadRequest } from './tools/readSection.js';

// Synchronous CLI entry into the same shared-wiki read path the stdio MCP server exposes.
// It reuses loadConfig() (so it self-configures from CLAUDE_PROJECT_DIR exactly like the
// server) and readSectionsTool() (so revision/index/marker semantics are guaranteed
// identical — there is a single shared-wiki reader, never a second re-implementation).
// A plain orchestrator script (wiki_materialize_task.py) can therefore fetch github_mcp
// hard-constraint rereads without going through the MCP tool protocol, and still get the
// connected repo's revision + repoUrl back for drift detection.

export type CliReadSectionsInput = {
  sections: SectionReadRequest[];
  includeDocumentContext?: boolean;
  errorMode?: 'strict' | 'partial';
};

export type CliReadSectionsResult = BatchSectionReadResult & { repoUrl: string };

const USAGE =
  'read-sections expects a JSON object on stdin: ' +
  '{ "sections": [ { "path": "<wikiPath>", "section": "<sectionId>", "includeDocumentContext"?: bool } ], ' +
  '"includeDocumentContext"?: bool, "errorMode"?: "strict" | "partial" }';

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : (chunk as Buffer));
  }
  return Buffer.concat(chunks).toString('utf8');
}

export function parseReadSectionsInput(raw: string): CliReadSectionsInput {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error(`No input on stdin. ${USAGE}`);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch (error) {
    throw new Error(`stdin is not valid JSON: ${error instanceof Error ? error.message : String(error)}. ${USAGE}`);
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`stdin must be a JSON object. ${USAGE}`);
  }
  const obj = parsed as Record<string, unknown>;
  if (!Array.isArray(obj.sections)) {
    throw new Error(`stdin must include a "sections" array. ${USAGE}`);
  }
  return {
    sections: obj.sections as SectionReadRequest[],
    includeDocumentContext: obj.includeDocumentContext as boolean | undefined,
    errorMode: obj.errorMode as 'strict' | 'partial' | undefined,
  };
}

export async function runReadSectionsCli(input: CliReadSectionsInput): Promise<CliReadSectionsResult> {
  const config = loadConfig();
  const result = await withCloneLock(config, () =>
    readSectionsTool(config, {
      sections: input.sections,
      includeDocumentContext: input.includeDocumentContext,
      errorMode: input.errorMode,
    }),
  );
  // repoUrl rides along so the caller can detect shared-wiki rebinding drift (sidecar
  // sharedWiki.repoUrl vs the repo this project's wiki.sharedMcp actually resolves to).
  return { ...result, repoUrl: config.repoUrl };
}

export async function runReadSectionsCliFromStdin(): Promise<void> {
  const input = parseReadSectionsInput(await readStdin());
  const payload = await runReadSectionsCli(input);
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}
