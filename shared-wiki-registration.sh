#!/usr/bin/env bash
set -euo pipefail

# Emit a ready-to-paste, repo-less ("generic") Claude Code MCP registration for the
# shared-wiki server. Register it ONCE at user level. The server reads
# CLAUDE_PROJECT_DIR (injected by Claude Code) at runtime and self-configures from
# each project's .shared-superpowers/settings.json -> wiki.sharedMcp, so a single
# registration serves every project and different projects can target different
# shared wikis. A project that declares no wiki.sharedMcp gets no MCP shared wiki
# (fail-closed). stdout is clean JSON; guidance goes to stderr.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ENTRY="$SCRIPT_DIR/mcp/shared-wiki/dist/index.js"

if [[ ! -f "$SERVER_ENTRY" ]]; then
  printf 'Shared-wiki MCP server is not built yet: %s\n' "$SERVER_ENTRY" >&2
  printf 'Build it first:\n  (cd %s/mcp/shared-wiki && npm install && npm run build)\n' "$SCRIPT_DIR" >&2
  exit 1
fi

printf 'Generic shared-wiki MCP registration (register once, user level):\n' >&2
printf '  - Do NOT add SHARED_WIKI_MCP_* env here; those override per-project settings.\n' >&2
printf '  - Per-project shared wiki is configured in each project'"'"'s\n' >&2
printf '    .shared-superpowers/settings.json under wiki.sharedMcp (see examples/).\n' >&2

python3 - "$SERVER_ENTRY" <<'PY'
import json
import sys

entry = sys.argv[1]
print(json.dumps({
    "mcpServers": {
        "shared-wiki": {
            "command": "node",
            "args": [entry],
        }
    }
}, indent=2))
PY
