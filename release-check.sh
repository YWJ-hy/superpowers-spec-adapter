#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
REPO_ROOT_INPUT="${2:-}"
if [[ -z "$REPO_ROOT_INPUT" ]]; then
  printf 'Missing required project root.\n' >&2
  printf 'Usage: %s [superpowers-target] <project-root>\n' "$0" >&2
  exit 1
fi
REPO_ROOT="$(cd "$REPO_ROOT_INPUT" && pwd)"
MANIFEST_OUTPUT="$SCRIPT_DIR/manifest-output.json"

printf 'Release check: verify\n'
"$SCRIPT_DIR/verify.sh" "$TARGET_INPUT"

printf '\nRelease check: doctor\n'
"$SCRIPT_DIR/doctor.sh" "$TARGET_INPUT" "$REPO_ROOT"

printf '\nRelease check: self-test\n'
"$SCRIPT_DIR/self-test.sh" "$TARGET_INPUT" "$REPO_ROOT"

printf '\nRelease check: export-manifest\n'
"$SCRIPT_DIR/export-manifest.sh" "$TARGET_INPUT" "$REPO_ROOT" "$MANIFEST_OUTPUT"

printf '\nRelease check completed successfully\n'
