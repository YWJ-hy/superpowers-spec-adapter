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
TARGET_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" "$TARGET_INPUT")"
TARGET_DIR="$(python3 - <<'PY' "$TARGET_JSON"
import json, sys
print(json.loads(sys.argv[1])['target'])
PY
)"
REPO_ROOT="$(cd "$REPO_ROOT_INPUT" && pwd)"

"$SCRIPT_DIR/install.sh" "$TARGET_INPUT"
"$SCRIPT_DIR/verify.sh" "$TARGET_INPUT"
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Adapter Self Test" "Validate one-shot spec updates." "Self-test rule")
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Adapter Self Test" "Validate one-shot spec updates again." "Self-test rule updated")
bash "$SCRIPT_DIR/tests/plan-context-smoke.sh" "$TARGET_DIR" "$REPO_ROOT"
python3 "$SCRIPT_DIR/lib/hook_patch.py" verify "$TARGET_DIR"
"$SCRIPT_DIR/status.sh" "$TARGET_INPUT"

printf 'superpower-adapter self-test complete\n'
