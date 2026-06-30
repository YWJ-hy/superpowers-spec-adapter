#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# First non-flag arg is the wiki repo root; any --flags pass through to the
# exporter (e.g. --no-graph-ci to skip the graph-rebuild GitHub Action).
REPO_ROOT_INPUT=""
EXTRA_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --*) EXTRA_ARGS+=("$arg") ;;
    *)
      if [[ -z "$REPO_ROOT_INPUT" ]]; then
        REPO_ROOT_INPUT="$arg"
      else
        EXTRA_ARGS+=("$arg")
      fi
      ;;
  esac
done

if [[ -z "$REPO_ROOT_INPUT" ]]; then
  printf 'Missing required wiki repository root.\n' >&2
  printf 'Usage: %s <wiki-repo-root> [--no-graph-ci]\n' "$0" >&2
  exit 1
fi

if [[ ! -d "$REPO_ROOT_INPUT" ]]; then
  printf 'Wiki repository root not found: %s\n' "$REPO_ROOT_INPUT" >&2
  exit 1
fi

REPO_ROOT="$(cd "$REPO_ROOT_INPUT" && pwd)"

exec python3 "$SCRIPT_DIR/lib/export_wiki_skills.py" "$SCRIPT_DIR" "$REPO_ROOT" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
