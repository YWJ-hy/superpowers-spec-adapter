#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  printf 'Usage:\n' >&2
  printf '  %s <superpowers-source-or-url> <out>\n' "$0" >&2
  printf '  %s <superpowers-source-or-url> <adapter-root> <out>\n' "$0" >&2
  exit 1
}

if [[ "$#" -eq 2 ]]; then
  SUPERPOWERS_SOURCE="$1"
  ADAPTER_ROOT="$SCRIPT_DIR"
  OUT="$2"
elif [[ "$#" -eq 3 ]]; then
  SUPERPOWERS_SOURCE="$1"
  ADAPTER_ROOT="$2"
  OUT="$3"
else
  usage
fi

exec python3 "$SCRIPT_DIR/lib/multica_runtime_builder.py" "$SUPERPOWERS_SOURCE" "$ADAPTER_ROOT" "$OUT"
