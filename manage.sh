#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-}"

usage() {
  local exit_code="${1:-1}"
  printf 'Usage:\n' >&2
  printf '  %s <command> [target-dir]\n' "$0" >&2
  printf '\nCommands:\n' >&2
  printf '  install [repo-root]\n' >&2
  printf '  uninstall [repo-root]\n' >&2
  printf '  verify [repo-root]\n' >&2
  printf '  status [repo-root]\n' >&2
  printf '  doctor [repo-root]\n' >&2
  printf '  export-manifest [repo-root] [output-path]\n' >&2
  printf '  bootstrap-spec [repo-root] [--preset web|backend|fullstack] [categories...]\n' >&2
  printf '  self-test [repo-root]\n' >&2
  printf '  release-check [repo-root]\n' >&2
  printf '  help\n' >&2
  exit "$exit_code"
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
  doctor)
    exec "$SCRIPT_DIR/doctor.sh" "$@"
    ;;
  export-manifest)
    exec "$SCRIPT_DIR/export-manifest.sh" "$@"
    ;;
  bootstrap-spec)
    exec "$SCRIPT_DIR/bootstrap-spec.sh" "$@"
    ;;
  self-test)
    exec "$SCRIPT_DIR/self-test.sh" "$@"
    ;;
  release-check)
    exec "$SCRIPT_DIR/release-check.sh" "$@"
    ;;
  help|-h|--help)
    usage 0
    ;;
  *)
    printf 'Unknown command: %s\n\n' "$COMMAND" >&2
    usage 1
    ;;
esac
