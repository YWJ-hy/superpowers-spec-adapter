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
MARKER="$(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import generated_marker
print(generated_marker(Path(sys.argv[1])))
PY
)"

status_target() {
  local target_dir="$1"
  printf 'Status for %s\n' "$target_dir"
  while IFS= read -r relative
  do
    relative="${relative%$'\r'}"
    target="$target_dir/$relative"
    if [[ -f "$target" ]] && grep -Fq "$MARKER" "$target"; then
      printf '[managed] %s\n' "$relative"
    elif [[ -f "$target" ]]; then
      printf '[present-unmanaged] %s\n' "$relative"
    else
      printf '[missing] %s\n' "$relative"
    fi
  done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import installed_paths
for item in installed_paths(Path(sys.argv[1])):
    print(item)
PY
  )
}

for target_dir in "${TARGET_DIRS[@]}"; do
  target_dir="${target_dir%$'\r'}"
  status_target "$target_dir"
done
