#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

require_text() {
  local text="$1"
  local file="$2"
  if ! grep -Fq -- "$text" "$file"; then
    printf 'Expected %s to contain: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

cat >"$TMP_DIR/constraints.json" <<'JSON'
{
  "schemaVersion": 1,
  "kind": "superpower-adapter.source-truth-constraints",
  "planPath": "docs/superpowers/plans/example.md",
  "status": "passed",
  "taskConstraints": [
    {
      "taskId": "Task 1",
      "appliesTo": ["Task 1"],
      "hardConstraint": true,
      "sourcePaths": ["src/services/generated/client.ts"],
      "constraints": {
        "implementation": ["Do not edit generated service clients."],
        "test": ["Test against the generated client shape."],
        "review": ["Confirm generated clients were not modified."],
        "general": ["Backend contract is the authority for service fields."]
      }
    },
    {
      "taskId": "Task 2",
      "appliesTo": ["Task 2"],
      "constraints": {
        "implementation": ["Use existing permission keys only."]
      }
    }
  ],
  "caveats": ["Full report is planning/audit only."]
}
JSON

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints.json" --validate-only --strict
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints.json" --task 'Task 1' --role implementer >"$TMP_DIR/implementer.md"
require_text '## Source-of-Truth Constraints' "$TMP_DIR/implementer.md"
require_text 'Do not edit generated service clients.' "$TMP_DIR/implementer.md"
require_text 'Test against the generated client shape.' "$TMP_DIR/implementer.md"
require_text 'Backend contract is the authority' "$TMP_DIR/implementer.md"
if grep -Fq 'Confirm generated clients were not modified.' "$TMP_DIR/implementer.md"; then
  printf 'Expected implementer render to omit review-only constraint\n' >&2
  exit 1
fi

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints.json" --task 'Task 1' --role reviewer >"$TMP_DIR/reviewer.md"
require_text 'Confirm generated clients were not modified.' "$TMP_DIR/reviewer.md"

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints.json" --task 'Task 2' --role implementer >"$TMP_DIR/task2.md"
require_text 'Use existing permission keys only.' "$TMP_DIR/task2.md"
if grep -Fq 'Do not edit generated service clients.' "$TMP_DIR/task2.md"; then
  printf 'Expected task filtering to omit Task 1 constraints\n' >&2
  exit 1
fi

cat >"$TMP_DIR/not-configured.json" <<'JSON'
{
  "schemaVersion": 1,
  "kind": "superpower-adapter.source-truth-constraints",
  "planPath": "docs/superpowers/plans/example.md",
  "status": "not_configured",
  "taskConstraints": []
}
JSON
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/not-configured.json" --task 'Task 1' --role implementer >"$TMP_DIR/not-configured.md"
require_text 'No configured source-of-truth constraints' "$TMP_DIR/not-configured.md"

cat >"$TMP_DIR/bad-version.json" <<'JSON'
{"schemaVersion": 2, "kind": "superpower-adapter.source-truth-constraints", "planPath": "x", "status": "passed", "taskConstraints": []}
JSON
if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/bad-version.json" --validate-only >"$TMP_DIR/bad-version.out" 2>&1; then
  printf 'Expected bad schemaVersion to fail\n' >&2
  exit 1
fi
require_text 'schemaVersion must be 1' "$TMP_DIR/bad-version.out"

cat >"$TMP_DIR/unknown-category.json" <<'JSON'
{
  "schemaVersion": 1,
  "kind": "superpower-adapter.source-truth-constraints",
  "planPath": "docs/superpowers/plans/example.md",
  "status": "passed",
  "taskConstraints": [
    {"taskId": "Task 1", "constraints": {"implementation": [], "unknown": ["bad"]}}
  ]
}
JSON
if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/unknown-category.json" --validate-only --strict >"$TMP_DIR/unknown-category.out" 2>&1; then
  printf 'Expected strict unknown category to fail\n' >&2
  exit 1
fi
require_text 'unsupported categories' "$TMP_DIR/unknown-category.out"

printf 'source-truth render smoke OK\n'
