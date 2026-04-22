#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-}"

usage() {
  local exit_code="${1:-1}"
  printf 'Usage:\n' >&2
  printf '  %s install [superpowers-target]\n' "$0" >&2
  printf '  %s uninstall [superpowers-target]\n' "$0" >&2
  printf '  %s verify [superpowers-target]\n' "$0" >&2
  printf '  %s status [superpowers-target]\n' "$0" >&2
  printf '  %s bootstrap-spec <project-root> [--preset web|backend|fullstack] [categories...]\n' "$0" >&2
  printf '  %s doctor <project-root> [superpowers-target]\n' "$0" >&2
  printf '  %s export-manifest <project-root> [output-path] [superpowers-target]\n' "$0" >&2
  printf '  %s self-test <project-root> [superpowers-target]\n' "$0" >&2
  printf '  %s release-check <project-root> [superpowers-target]\n' "$0" >&2
  printf '  %s help\n' "$0" >&2
  exit "$exit_code"
}

require_project_root() {
  local project_root="${1:-}"
  if [[ -z "$project_root" ]]; then
    printf 'Missing required project root.\n\n' >&2
    usage 1
  fi
}

if [[ -z "$COMMAND" ]]; then
  usage 1
fi
shift

case "$COMMAND" in
  install)
    exec "$SCRIPT_DIR/install.sh" "$@"
    ;;
  uninstall)
    exec "$SCRIPT_DIR/uninstall.sh" "$@"
    ;;
  verify)
    exec "$SCRIPT_DIR/verify.sh" "$@"
    ;;
  status)
    exec "$SCRIPT_DIR/status.sh" "$@"
    ;;
  bootstrap-spec)
    require_project_root "${1:-}"
    exec "$SCRIPT_DIR/bootstrap-spec.sh" "$@"
    ;;
  doctor)
    require_project_root "${1:-}"
    PROJECT_ROOT="$1"
    TARGET_INPUT="${2:-}"
    exec "$SCRIPT_DIR/doctor.sh" "$TARGET_INPUT" "$PROJECT_ROOT"
    ;;
  export-manifest)
    require_project_root "${1:-}"
    PROJECT_ROOT="$1"
    OUTPUT_PATH="${2:-}"
    TARGET_INPUT="${3:-}"
    exec "$SCRIPT_DIR/export-manifest.sh" "$TARGET_INPUT" "$PROJECT_ROOT" "$OUTPUT_PATH"
    ;;
  self-test)
    require_project_root "${1:-}"
    PROJECT_ROOT="$1"
    TARGET_INPUT="${2:-}"
    exec "$SCRIPT_DIR/self-test.sh" "$TARGET_INPUT" "$PROJECT_ROOT"
    ;;
  release-check)
    require_project_root "${1:-}"
    PROJECT_ROOT="$1"
    TARGET_INPUT="${2:-}"
    exec "$SCRIPT_DIR/release-check.sh" "$TARGET_INPUT" "$PROJECT_ROOT"
    ;;
  help|-h|--help)
    usage 0
    ;;
  *)
    printf 'Unknown command: %s\n\n' "$COMMAND" >&2
    usage 1
    ;;
esac
