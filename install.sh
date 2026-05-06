#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
TARGETS_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" --all "$TARGET_INPUT")"
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

TARGET_DIRS=()
while IFS= read -r target_dir; do
  [[ -z "$target_dir" ]] && continue
  TARGET_DIRS+=("$target_dir")
done < <(python3 - <<'PY' "$TARGETS_JSON"
import json, sys
for item in json.loads(sys.argv[1])['targets']:
    print(item['target'])
PY
)

python3 "$SCRIPT_DIR/lib/sync_role_prd.py" sync "$SCRIPT_DIR"

install_target() {
  local target_dir="$1"

  if [[ ! -d "$target_dir" ]]; then
    printf 'Missing superpowers target: %s\n' "$target_dir" >&2
    exit 1
  fi

  printf 'Installing superpower-adapter to %s\n' "$target_dir"

  copy_overlay() {
    local source_rel="$1"
    local target_rel="$2"
    local source="$OVERLAY_DIR/$source_rel"
    local target="$target_dir/$target_rel"

    if [[ ! -f "$source" ]]; then
      printf 'Missing overlay source: %s\n' "$source" >&2
      exit 1
    fi

    mkdir -p "$(dirname "$target")"

    if [[ -f "$target" ]] && ! grep -Fq "$MARKER" "$target"; then
      printf 'Refusing to overwrite unmanaged file: %s\n' "$target" >&2
      exit 1
    fi

    python3 - <<'PY' "$source" "$target" "$target_dir"
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
    target="$target_dir/$relative"
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
    "$target_dir/scripts/update-wiki.py" \
    "$target_dir/scripts/wiki-context.py" \
    "$target_dir/scripts/wiki_import.py" \
    "$target_dir/scripts/init-wiki.py" \
    "$target_dir/scripts/wiki_update_check.py" \
    "$target_dir/scripts/wiki_select_target.py" \
    "$target_dir/scripts/wiki_apply_update.py"
  python3 "$HOOK_PATCHER" install "$target_dir"
  python3 "$NATIVE_SKILL_PATCHER" install "$target_dir"
}

for target_dir in "${TARGET_DIRS[@]}"; do
  target_dir="${target_dir%$'\r'}"
  install_target "$target_dir"
done

printf 'superpower-adapter install complete (%s target(s))\n' "${#TARGET_DIRS[@]}"
