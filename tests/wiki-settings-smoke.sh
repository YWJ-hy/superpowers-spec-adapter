#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
SCRIPT="${TARGET_INPUT}/scripts/wiki_settings.py"

if [[ ! -f "$SCRIPT" ]]; then
  printf 'Missing wiki settings inspector: %s\n' "$SCRIPT" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/.superpowers"

assert_contains() {
  local label="$1"
  local needle="$2"
  local file="$3"
  if ! grep -Fq -- "$needle" "$file"; then
    printf 'Expected %s to contain %s\n' "$label" "$needle" >&2
    cat "$file" >&2
    exit 1
  fi
}

python3 "$SCRIPT" "$TMP_DIR" --show-policy >"$TMP_DIR/defaults.json"
assert_contains "defaults" '"status": "not_configured"' "$TMP_DIR/defaults.json"
assert_contains "defaults" '"brainstorm": {' "$TMP_DIR/defaults.json"
assert_contains "defaults" '"maxWikiPages": 3' "$TMP_DIR/defaults.json"
assert_contains "defaults" '"maxWikiPages": 5' "$TMP_DIR/defaults.json"
assert_contains "defaults" '"maxWikiPages": 2' "$TMP_DIR/defaults.json"
assert_contains "defaults" '"unlimited": true' "$TMP_DIR/defaults.json"

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "research": {
      "maxWikiPages": {
        "brainstorm": 4,
        "plan": null,
        "debug": "no_limit",
        "implement": "none",
        "review": "unlimited"
      }
    }
  }
}
JSON
python3 "$SCRIPT" "$TMP_DIR" --phase brainstorm >"$TMP_DIR/brainstorm.json"
assert_contains "brainstorm override" '"status": "configured"' "$TMP_DIR/brainstorm.json"
assert_contains "brainstorm override" '"phase": "brainstorm"' "$TMP_DIR/brainstorm.json"
assert_contains "brainstorm override" '"maxWikiPages": 4' "$TMP_DIR/brainstorm.json"
assert_contains "brainstorm override" '"unlimited": false' "$TMP_DIR/brainstorm.json"
python3 "$SCRIPT" "$TMP_DIR" --phase plan >"$TMP_DIR/plan.json"
assert_contains "plan unlimited" '"maxWikiPages": null' "$TMP_DIR/plan.json"
assert_contains "plan unlimited" '"unlimited": true' "$TMP_DIR/plan.json"
python3 "$SCRIPT" "$TMP_DIR" --phase debug >"$TMP_DIR/debug.json"
assert_contains "debug unlimited alias" '"maxWikiPages": null' "$TMP_DIR/debug.json"

for invalid in zero negative boolean string; do
  case "$invalid" in
    zero)
      value='0'
      ;;
    negative)
      value='-1'
      ;;
    boolean)
      value='true'
      ;;
    string)
      value='"many"'
      ;;
  esac
  cat >"$TMP_DIR/.superpowers/settings.json" <<JSON
{"wiki":{"research":{"maxWikiPages":{"plan":${value}}}}}
JSON
  if python3 "$SCRIPT" "$TMP_DIR" --phase plan >"$TMP_DIR/invalid-$invalid.out" 2>&1; then
    printf 'Expected invalid %s maxWikiPages to fail\n' "$invalid" >&2
    exit 1
  fi
  assert_contains "invalid $invalid" 'wiki.research.maxWikiPages.plan' "$TMP_DIR/invalid-$invalid.out"
done

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{"wiki":{"research":{"maxWikiPages":5}}}
JSON
if python3 "$SCRIPT" "$TMP_DIR" --phase plan >"$TMP_DIR/invalid-object.out" 2>&1; then
  printf 'Expected non-object maxWikiPages to fail\n' >&2
  exit 1
fi
assert_contains "invalid object" 'wiki.research.maxWikiPages must be an object' "$TMP_DIR/invalid-object.out"

printf 'wiki settings smoke OK\n'
