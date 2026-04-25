#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-}"
PROJECT_ROOT="${2:-}"
if [[ -z "$TARGET_DIR" || -z "$PROJECT_ROOT" ]]; then
  printf 'Usage: %s <installed-superpowers-target> <project-root>\n' "$0" >&2
  exit 1
fi

mkdir -p "$PROJECT_ROOT/spec/source"
printf '# Imported Command Path Smoke\n\nOriginal detail must be preserved.\n' > "$PROJECT_ROOT/spec/source/path-smoke.md"

(cd "$PROJECT_ROOT" && python3 "$TARGET_DIR/scripts/spec_import.py" spec/source --hint "command path smoke" --target imported-command-path-smoke --merge-existing)

TARGET_FILE="$PROJECT_ROOT/.superpowers/spec/imported-command-path-smoke/path-smoke.md"
if [[ ! -f "$TARGET_FILE" ]]; then
  printf 'Expected imported target file: %s\n' "$TARGET_FILE" >&2
  exit 1
fi
if ! grep -Fq 'Original detail must be preserved.' "$TARGET_FILE"; then
  printf 'Expected imported source content to be preserved\n' >&2
  exit 1
fi
if [[ ! -f "$PROJECT_ROOT/.superpowers/spec/imported-command-path-smoke/index.md" ]]; then
  printf 'Expected imported subdirectory index to be refreshed\n' >&2
  exit 1
fi

printf 'spec import command path smoke complete\n'
