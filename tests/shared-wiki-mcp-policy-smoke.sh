#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

REMOTE="$TMP_DIR/remote.git"
WORK="$TMP_DIR/work"
CACHE="$TMP_DIR/cache"
CONFIG="$TMP_DIR/config.json"

git init --bare "$REMOTE" >/dev/null
git clone "$REMOTE" "$WORK" >/dev/null
cat > "$WORK/index.md" <<'MD'
# Shared Wiki

- [Guide](guide.md)
MD
cat > "$WORK/guide.md" <<'MD'
# Guide

Reusable shared rule.
MD
mkdir -p "$WORK/.shared-superpowers"
cat > "$WORK/.shared-superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "updateExistingPage": "ask",
      "createNewDocument": "ask"
    },
    "sharedNeutrality": {
      "blockedTerms": ["internal-system"],
      "blockedPatterns": ["prod-[a-z]+"]
    }
  }
}
JSON
git -C "$WORK" add .
git -C "$WORK" commit -m "Seed shared wiki" >/dev/null
git -C "$WORK" branch -M main
git -C "$WORK" push origin main >/dev/null

cat > "$CONFIG" <<JSON
{
  "repoUrl": "$REMOTE",
  "baseBranch": "main",
  "cacheDir": "$CACHE"
}
JSON

npm run build --prefix "$ROOT_DIR/mcp/shared-wiki" >/dev/null

SHARED_WIKI_MCP_CONFIG="$CONFIG" node --input-type=module <<'JS'
import { loadConfig } from './mcp/shared-wiki/dist/config.js';
import { treeTool } from './mcp/shared-wiki/dist/tools/tree.js';
import { validatePatchTool } from './mcp/shared-wiki/dist/tools/validatePatch.js';
const config = loadConfig(process.env);
const tree = await treeTool(config);
if (!tree.files.some((file) => file.path === 'guide.md')) throw new Error('missing indexed guide');
const patch = `diff --git a/guide.md b/guide.md
index 3b155d1..af0d0e1 100644
--- a/guide.md
+++ b/guide.md
@@ -1,3 +1,5 @@
 # Guide

 Reusable shared rule.
+
+internal-system should not be here.
`;
const result = await validatePatchTool(config, { patch, authorizedUpdate: true });
if (result.ok) throw new Error('neutrality violation was not rejected');
if (!result.errors.some((error) => error.includes('blocked shared-wiki term'))) throw new Error(`unexpected errors: ${result.errors.join('\n')}`);
JS

printf 'shared-wiki MCP policy smoke passed\n'
