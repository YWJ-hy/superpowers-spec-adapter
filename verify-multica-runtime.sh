#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_ROOT="${1:-}"

if [[ -z "$RUNTIME_ROOT" ]]; then
  printf 'Usage: %s <runtime-root>\n' "$0" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/lib/multica_runtime_verify.py" "$RUNTIME_ROOT" --adapter-root "$SCRIPT_DIR"
