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
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/wiki_apply_update.py" --authorized-create "updates/adapter-self-test.md" "Adapter Self Test" "Validate mechanical wiki writes." "Self-test rule")
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/wiki_apply_update.py" "updates/adapter-self-test.md" "Adapter Self Test" "Validate mechanical wiki writes again." "Self-test rule updated")
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/update-wiki.py" --authorized-update)
if [[ ! -f "$REPO_ROOT/.superpowers/wiki/updates/adapter-self-test.md" ]]; then
  printf 'Expected mechanical update target to exist\n' >&2
  exit 1
fi
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/init-wiki.py" . "self-test" --json >/dev/null)
python3 - <<'PY' "$REPO_ROOT"
from pathlib import Path
import sys
path = Path(sys.argv[1]) / '.superpowers' / 'tmp-import-source.md'
path.write_text('# External Import Self Test\n\nOriginal detail must be preserved.\n', encoding='utf-8')
PY
rm -f "$REPO_ROOT/.superpowers/wiki/imported/external-import-self-test.md"
(cd "$REPO_ROOT" && python3 "$TARGET_DIR/scripts/wiki_import.py" .superpowers/tmp-import-source.md --target imported/external-import-self-test.md --merge-existing --authorized-create)
if [[ ! -f "$REPO_ROOT/.superpowers/wiki/imported/external-import-self-test.md" ]]; then
  printf 'Expected single-file import target to be used as a file path\n' >&2
  exit 1
fi
rm -f "$REPO_ROOT/.superpowers/tmp-import-source.md"
bash "$SCRIPT_DIR/tests/wiki-authorization-policy-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/shared-wiki-neutrality-smoke.sh"
bash "$SCRIPT_DIR/tests/native-wiki-patch-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/lanhu-html-settings-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/lanhu-tree-prd-guardrails-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/lanhu-confirmation-gate-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/native-worktree-origin-patch-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/wiki-update-check-smoke.sh" "$TARGET_DIR" "$REPO_ROOT"
bash "$SCRIPT_DIR/tests/init-wiki-inventory-smoke.sh" "$TARGET_DIR" "$REPO_ROOT"
bash "$SCRIPT_DIR/tests/wiki-index-graph-smoke.sh" "$TARGET_DIR" "$REPO_ROOT"
bash "$SCRIPT_DIR/tests/wiki-import-command-path-smoke.sh" "$TARGET_DIR" "$REPO_ROOT"
bash "$SCRIPT_DIR/tests/shared-wiki-submodule-smoke.sh"
bash "$SCRIPT_DIR/tests/shared-wiki-mcp-policy-smoke.sh"
bash "$SCRIPT_DIR/tests/shared-wiki-mcp-pr-smoke.sh"
bash "$SCRIPT_DIR/tests/install-version-warning-smoke.sh" "$TARGET_DIR"
bash "$SCRIPT_DIR/tests/subagent-model-config-smoke.sh" "$TARGET_DIR"
python3 "$SCRIPT_DIR/lib/hook_patch.py" verify "$TARGET_DIR"
"$SCRIPT_DIR/status.sh" "$TARGET_INPUT"

printf 'superpower-adapter self-test complete\n'
