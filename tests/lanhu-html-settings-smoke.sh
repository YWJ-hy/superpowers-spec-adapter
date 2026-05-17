#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
TARGET_DIR="$(cd "${TARGET_INPUT}" && pwd)"
TMP_PARENT="${CLAUDE_JOB_DIR:-${TMPDIR:-/tmp}}"
PROJECT_ROOT="$(mktemp -d "${TMP_PARENT%/}/lanhu-html-settings.XXXXXX")"
trap 'rm -rf "${PROJECT_ROOT}"' EXIT

mkdir -p "${PROJECT_ROOT}/.superpowers"

assert_json_field() {
  local file="$1"
  local expression="$2"
  python3 - "$file" "$expression" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expression = sys.argv[2]
if not eval(expression, {"payload": payload}):
    raise SystemExit(f"Assertion failed: {expression}; payload={payload!r}")
PY
}

python3 "${TARGET_DIR}/scripts/lanhu_settings.py" frontend "${PROJECT_ROOT}" > "${PROJECT_ROOT}/default-frontend.json"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['format'] == 'markdown'"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['settingsPath'] is None"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['primaryOutput']['kind'] == 'markdown_prd'"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['primaryOutput']['filename'] == 'prd.md'"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['htmlPrd']['enabled'] is False"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['htmlPrd']['filename'] == 'index.html'"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['htmlPrd']['prototypeFilename'] is None"
assert_json_field "${PROJECT_ROOT}/default-frontend.json" "payload['htmlPrd']['companionFiles'] == []"

python3 - "${PROJECT_ROOT}/.superpowers/settings.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(json.dumps({
    "lanhu": {
        "frontend": {
            "output": {
                "format": "html"
            }
        }
    }
}, indent=2) + "\n", encoding="utf-8")
PY

python3 "${TARGET_DIR}/scripts/lanhu_settings.py" frontend "${PROJECT_ROOT}" > "${PROJECT_ROOT}/html-frontend.json"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['format'] == 'html'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['settingsPath'] == '.superpowers/settings.json'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['source'] == '.superpowers/settings.json'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['primaryOutput']['kind'] == 'html_prd'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['primaryOutput']['filename'] == 'index.html'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['htmlPrd']['enabled'] is True"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['htmlPrd']['prototypeFilename'] == 'prototype/index.html'"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['htmlPrd']['companionFiles'] == ['prototype/index.html']"
assert_json_field "${PROJECT_ROOT}/html-frontend.json" "payload['htmlPrd']['fallbackToMarkdownWhenTextOnly'] is True"

python3 "${TARGET_DIR}/scripts/lanhu_settings.py" backend "${PROJECT_ROOT}" > "${PROJECT_ROOT}/html-backend.json"
assert_json_field "${PROJECT_ROOT}/html-backend.json" "payload['format'] == 'markdown'"
assert_json_field "${PROJECT_ROOT}/html-backend.json" "payload['htmlPrd']['enabled'] is False"
assert_json_field "${PROJECT_ROOT}/html-backend.json" "payload['htmlPrd']['prototypeFilename'] is None"
assert_json_field "${PROJECT_ROOT}/html-backend.json" "payload['htmlPrd']['companionFiles'] == []"
assert_json_field "${PROJECT_ROOT}/html-backend.json" "'frontend-only' in payload['warnings'][0]"

python3 - "${PROJECT_ROOT}/.superpowers/settings.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(json.dumps({
    "lanhu": {
        "frontend": {
            "output": {
                "format": "markdown+html"
            }
        }
    }
}, indent=2) + "\n", encoding="utf-8")
PY
if python3 "${TARGET_DIR}/scripts/lanhu_settings.py" frontend "${PROJECT_ROOT}" > "${PROJECT_ROOT}/invalid.out" 2>&1; then
  printf 'Expected invalid lanhu.frontend.output.format to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'Invalid lanhu.frontend.output.format' "${PROJECT_ROOT}/invalid.out"; then
  printf 'Expected invalid format error message\n' >&2
  exit 1
fi

printf '{ invalid json' > "${PROJECT_ROOT}/.superpowers/settings.json"
if python3 "${TARGET_DIR}/scripts/lanhu_settings.py" frontend "${PROJECT_ROOT}" > "${PROJECT_ROOT}/malformed.out" 2>&1; then
  printf 'Expected malformed settings JSON to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'Invalid JSON' "${PROJECT_ROOT}/malformed.out"; then
  printf 'Expected malformed JSON error message\n' >&2
  exit 1
fi

printf 'Lanhu HTML settings smoke OK\n'
