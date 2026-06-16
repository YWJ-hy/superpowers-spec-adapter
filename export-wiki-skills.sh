#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT_INPUT="${1:-}"

if [[ -z "$REPO_ROOT_INPUT" ]]; then
  printf 'Missing required wiki repository root.\n' >&2
  printf 'Usage: %s <wiki-repo-root>\n' "$0" >&2
  exit 1
fi

if [[ ! -d "$REPO_ROOT_INPUT" ]]; then
  printf 'Wiki repository root not found: %s\n' "$REPO_ROOT_INPUT" >&2
  exit 1
fi

REPO_ROOT="$(cd "$REPO_ROOT_INPUT" && pwd)"

exec python3 "$SCRIPT_DIR/lib/export_wiki_skills.py" "$SCRIPT_DIR" "$REPO_ROOT"
