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
OVERLAY_DIR="$SCRIPT_DIR/overlays"
PATCHER="$SCRIPT_DIR/lib/hook_patch.py"
MARKER="$(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import generated_marker
print(generated_marker(Path(sys.argv[1])))
PY
)"

if [[ ! -d "$TARGET_DIR" ]]; then
  printf 'Missing superpowers target: %s\n' "$TARGET_DIR" >&2
  exit 1
fi

copy_overlay() {
  local source_rel="$1"
  local target_rel="$2"
  local source="$OVERLAY_DIR/$source_rel"
  local target="$TARGET_DIR/$target_rel"

  if [[ ! -f "$source" ]]; then
    printf 'Missing overlay source: %s\n' "$source" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$target")"

  if [[ -f "$target" ]] && ! grep -Fq "$MARKER" "$target"; then
    printf 'Refusing to overwrite unmanaged file: %s\n' "$target" >&2
    exit 1
  fi

  cp "$source" "$target"
  printf 'Installed %s\n' "$target_rel"
}

while IFS= read -r relative; do
  relative="${relative%$'\r'}"
  [[ -z "$relative" ]] && continue
  copy_overlay "$relative" "$relative"
done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import installed_paths
for item in installed_paths(Path(sys.argv[1])):
    print(item)
PY
)

while IFS= read -r relative; do
  relative="${relative%$'\r'}"
  [[ -z "$relative" ]] && continue
  target="$TARGET_DIR/$relative"
  if [[ -f "$target" ]] && grep -Fq "$MARKER" "$target"; then
    rm -f "$target"
    printf 'Removed deprecated %s\n' "$relative"
  fi
done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import removed_paths
for item in removed_paths(Path(sys.argv[1])):
    print(item)
PY
)

chmod +x \
  "$TARGET_DIR/scripts/update-spec.py" \
  "$TARGET_DIR/scripts/spec-context.py" \
  "$TARGET_DIR/scripts/spec_import.py" \
  "$TARGET_DIR/scripts/plan-context.py" \
  "$TARGET_DIR/scripts/workflow-gate.py" \
  "$TARGET_DIR/scripts/spec_select_context.py" \
  "$TARGET_DIR/scripts/spec_update_check.py" \
  "$TARGET_DIR/hooks/session-spec-index" \
  "$TARGET_DIR/hooks/session-plan-context"
python3 "$PATCHER" install "$TARGET_DIR"

printf 'superpower-adapter install complete\n'
