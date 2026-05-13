#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -R "$ROOT_DIR/mcp/shared-wiki" "$TMP_DIR/shared-wiki-mcp"
rm -rf "$TMP_DIR/shared-wiki-mcp/node_modules" "$TMP_DIR/shared-wiki-mcp/dist"

npm install --prefix "$TMP_DIR/shared-wiki-mcp" >/dev/null
npm test --prefix "$TMP_DIR/shared-wiki-mcp" >/dev/null
npm run build --prefix "$TMP_DIR/shared-wiki-mcp" >/dev/null

test -x "$TMP_DIR/shared-wiki-mcp/dist/index.js" || test -f "$TMP_DIR/shared-wiki-mcp/dist/index.js"
printf 'shared-wiki MCP copyable smoke passed\n'
