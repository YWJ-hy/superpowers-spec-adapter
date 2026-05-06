#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cp -R "$TARGET_INPUT" "$TMP_DIR/superpowers"
python3 - <<'PY' "$TMP_DIR/superpowers/package.json"
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding='utf-8'))
data['version'] = '99.0.0'
path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
PY

STDOUT_FILE="$TMP_DIR/install.stdout"
STDERR_FILE="$TMP_DIR/install.stderr"
if ! "${ROOT}/manage.sh" install "$TMP_DIR/superpowers" >"$STDOUT_FILE" 2>"$STDERR_FILE"; then
  printf 'Expected install to continue even when the target Superpowers version is newer\n' >&2
  exit 1
fi

if ! grep -Fq 'Warning: detected Superpowers 99.0.0' "$STDERR_FILE"; then
  printf 'Expected compatibility warning for newer Superpowers version\n' >&2
  exit 1
fi

if ! grep -Fq 'superpower-adapter install complete (1 target(s))' "$STDOUT_FILE"; then
  printf 'Expected install to complete successfully\n' >&2
  exit 1
fi

printf 'install version warning smoke test complete\n'
