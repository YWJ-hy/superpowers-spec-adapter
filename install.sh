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

  python3 - <<'PY' "$source" "$target" "$TARGET_DIR"
from pathlib import Path
import shlex
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
target_dir = shlex.quote(sys.argv[3])
text = source.read_text(encoding='utf-8')
text = text.replace('__SUPERPOWER_ADAPTER_PLUGIN_ROOT__', target_dir)
target.write_text(text, encoding='utf-8')
PY
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
  "$TARGET_DIR/scripts/init-spec.py" \
  "$TARGET_DIR/scripts/spec_update_check.py"
python3 "$HOOK_PATCHER" install "$TARGET_DIR"
python3 "$NATIVE_SKILL_PATCHER" install "$TARGET_DIR"

printf 'superpower-adapter install complete\n'
