#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/.superpowers" "$TMP_DIR/src/services/generated" "$TMP_DIR/openapi" "$TMP_DIR/src/mocks" "$TMP_DIR/dist"

grep_json() {
  local text="$1"
  local file="$2"
  if ! grep -Fq -- "$text" "$file"; then
    printf 'Expected %s to contain: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

python3 "$ROOT/overlays/scripts/source_truth_settings.py" "$TMP_DIR" --show-policy >"$TMP_DIR/no-config.json"
grep_json '"status": "not_configured"' "$TMP_DIR/no-config.json"
grep_json '"heuristics": false' "$TMP_DIR/no-config.json"

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{
  "sourceOfTruth": {
    "sources": [
      {"paths": ["src/services/generated/**"], "role": "truth", "edit": "never"},
      {"paths": ["/openapi/**", "!openapi/draft/**"], "role": "truth", "edit": "ask"},
      {"paths": ["src/mocks/**", "**/*.mock.ts", "**/*.fixture.ts"], "role": "evidence"},
      {"paths": ["dist/", "node_modules/**"], "role": "ignore"},
      {"paths": ["src/services/generated/experimental/**"], "role": "evidence"}
    ]
  }
}
JSON
python3 "$ROOT/overlays/scripts/source_truth_settings.py" "$TMP_DIR" --show-policy \
  --classify src/services/generated/client.ts \
  --classify src/services/generated/experimental/client.ts \
  --classify openapi/current.yaml \
  --classify openapi/draft/current.yaml \
  --classify src/mocks/user.mock.ts \
  --classify dist/app.js >"$TMP_DIR/classified.json"
grep_json '"status": "configured"' "$TMP_DIR/classified.json"
grep_json '"heuristics": false' "$TMP_DIR/classified.json"
grep_json '"role": "truth"' "$TMP_DIR/classified.json"
grep_json '"edit": "never"' "$TMP_DIR/classified.json"
grep_json '"edit": "ask"' "$TMP_DIR/classified.json"
grep_json '"role": "evidence"' "$TMP_DIR/classified.json"
grep_json '"role": "ignore"' "$TMP_DIR/classified.json"
grep_json '"role": "unconfigured"' "$TMP_DIR/classified.json"

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{"sourceOfTruth": {"sources": [{"paths": ["src/**"], "role": "contract", "edit": "never"}]}}
JSON
if python3 "$ROOT/overlays/scripts/source_truth_settings.py" "$TMP_DIR" --show-policy >"$TMP_DIR/invalid-role.out" 2>&1; then
  printf 'Expected invalid role to fail\n' >&2
  exit 1
fi
grep_json 'expected one of' "$TMP_DIR/invalid-role.out"

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{"sourceOfTruth": {"sources": [{"paths": ["src/**"], "role": "truth"}]}}
JSON
if python3 "$ROOT/overlays/scripts/source_truth_settings.py" "$TMP_DIR" --show-policy >"$TMP_DIR/missing-edit.out" 2>&1; then
  printf 'Expected truth without edit to fail\n' >&2
  exit 1
fi
grep_json "edit is required for role 'truth'" "$TMP_DIR/missing-edit.out"

cat >"$TMP_DIR/.superpowers/settings.json" <<'JSON'
{"sourceOfTruth": {"heuristics": true, "sources": [{"paths": ["src/mocks/**"], "role": "evidence"}, {"paths": ["dist/**"], "role": "ignore"}]}}
JSON
python3 "$ROOT/overlays/scripts/source_truth_settings.py" "$TMP_DIR" --show-policy >"$TMP_DIR/evidence-ignore.json"
grep_json '"heuristics": true' "$TMP_DIR/evidence-ignore.json"
grep_json '"role": "evidence"' "$TMP_DIR/evidence-ignore.json"
grep_json '"role": "ignore"' "$TMP_DIR/evidence-ignore.json"

printf 'source-truth settings smoke OK\n'
