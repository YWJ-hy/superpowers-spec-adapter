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
PATCHER="$SCRIPT_DIR/lib/hook_patch.py"
MARKER="$(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import generated_marker
print(generated_marker(Path(sys.argv[1])))
PY
)"

check_file() {
  local relative="$1"
  local target="$TARGET_DIR/$relative"
  if [[ ! -f "$target" ]]; then
    printf 'Missing file: %s\n' "$target" >&2
    exit 1
  fi
  if ! grep -Fq "$MARKER" "$target"; then
    printf 'Missing adapter marker: %s\n' "$target" >&2
    exit 1
  fi
  printf 'OK %s\n' "$relative"
}

while IFS= read -r relative; do
  relative="${relative%$'\r'}"
  [[ -z "$relative" ]] && continue
  check_file "$relative"
done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import installed_paths
for item in installed_paths(Path(sys.argv[1])):
    print(item)
PY
)
python3 "$PATCHER" verify "$TARGET_DIR"

printf 'superpower-adapter verify complete\n'
