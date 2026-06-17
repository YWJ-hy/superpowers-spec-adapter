#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
TARGETS_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" --all "$TARGET_INPUT")"
mapfile -t TARGET_DIRS < <(python3 - <<'PY' "$TARGETS_JSON"
import json, sys
for item in json.loads(sys.argv[1])['targets']:
    print(item['target'])
PY
)
HOOK_PATCHER="$SCRIPT_DIR/lib/hook_patch.py"
NATIVE_SKILL_PATCHER="$SCRIPT_DIR/lib/native_skill_patch.py"
MARKER="$(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import generated_marker
print(generated_marker(Path(sys.argv[1])))
PY
)"

uninstall_target() {
  local target_dir="$1"
  printf 'Uninstalling superpower-adapter from %s\n' "$target_dir"

  remove_managed_file() {
    local relative="$1"
    local target="$target_dir/$relative"
    if [[ -f "$target" ]] && grep -Fq "$MARKER" "$target"; then
      rm -f "$target"
      printf 'Removed %s\n' "$relative"
    fi
  }

  while IFS= read -r relative; do
    relative="${relative%$'\r'}"
    [[ -z "$relative" ]] && continue
    remove_managed_file "$relative"
  done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import installed_paths, removed_paths
for item in [*installed_paths(Path(sys.argv[1])), *removed_paths(Path(sys.argv[1]))]:
    print(item)
PY
  )
  python3 "$HOOK_PATCHER" uninstall "$target_dir"
  python3 "$NATIVE_SKILL_PATCHER" uninstall "$target_dir"
}

for target_dir in "${TARGET_DIRS[@]}"; do
  target_dir="${target_dir%$'\r'}"
  uninstall_target "$target_dir"
done

printf 'superpower-adapter uninstall complete (%s target(s))\n' "${#TARGET_DIRS[@]}"
