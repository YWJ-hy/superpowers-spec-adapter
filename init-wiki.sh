#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s <project-root> [analysis-hint]\n' "$0" >&2
  exit 1
}

if [[ $# -lt 1 || -z "${1:-}" ]]; then
  printf 'Missing required project root.\n' >&2
  usage
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$1" && pwd)"
shift
ANALYSIS_HINT="${*:-}"

if [[ ! -f "$PROJECT_ROOT/.superpowers/wiki/index.md" ]]; then
  printf 'Missing %s\n' "$PROJECT_ROOT/.superpowers/wiki/index.md" >&2
  printf 'Run bootstrap-wiki first: %s/manage.sh bootstrap-wiki %s\n' "$SCRIPT_DIR" "$PROJECT_ROOT" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/overlays/scripts/init-wiki.py" "$PROJECT_ROOT" "$ANALYSIS_HINT"

printf 'init-wiki complete\n'
