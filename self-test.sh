#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
TARGET_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" "$TARGET_INPUT")"
TARGET_DIR="$(python3 - <<'PY' "$TARGET_JSON"
import json, sys
print(json.loads(sys.argv[1])['target'])
PY
)"
REPO_ROOT="$(cd "${2:-$(pwd)}" && pwd)"

"$SCRIPT_DIR/install.sh" "$TARGET_INPUT"
"$SCRIPT_DIR/verify.sh" "$TARGET_INPUT"
python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Adapter Self Test" "Validate one-shot spec updates." "Self-test rule"
python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Adapter Self Test" "Validate one-shot spec updates again." "Self-test rule updated"
python3 "$SCRIPT_DIR/lib/hook_patch.py" verify "$TARGET_DIR"
"$SCRIPT_DIR/status.sh" "$TARGET_INPUT"

printf 'superpower-adapter self-test complete\n'
