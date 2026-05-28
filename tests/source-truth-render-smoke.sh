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

reject_text() {
  local text="$1"
  local file="$2"
  if grep -Fq -- "$text" "$file"; then
    printf 'Expected %s to omit: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

cat >"$TMP_DIR/plan.md" <<'MD'
# Example Plan

### Task T1: Implement generated client usage

Use the generated client without modifying it.

### Task T2: Add permission coverage

Add tests for permission handling.
MD

python3 - "$TMP_DIR/plan.md" "$TMP_DIR/constraints-v2.json" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

plan_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
TASK_HEADING_RE = re.compile(r"^### Task\s+([A-Za-z0-9][A-Za-z0-9_-]*):\s*(.+?)\s*$")
TASK_OR_HIGHER_HEADING_RE = re.compile(r"^#{1,3}\s+")

def normalize(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"

lines = plan_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
starts = []
for index, line in enumerate(lines):
    match = TASK_HEADING_RE.match(line)
    if match:
        starts.append((index, match.group(1), match.group(2)))

tasks = []
for position, (start, task_id, title) in enumerate(starts):
    end = len(lines)
    next_task_start = starts[position + 1][0] if position + 1 < len(starts) else None
    for index in range(start + 1, len(lines)):
        if next_task_start is not None and index == next_task_start:
            end = index
            break
        if TASK_OR_HIGHER_HEADING_RE.match(lines[index]) and not lines[index].startswith("####"):
            end = index
            break
    text = "\n".join(lines[start:end])
    tasks.append({
        "taskId": task_id,
        "taskTitle": title,
        "taskFingerprint": {
            "algorithm": "sha256",
            "normalization": "superpower-adapter-task-text-v1",
            "source": f"docs/superpowers/plans/example.md#{task_id}",
            "hash": hashlib.sha256(normalize(text).encode("utf-8")).hexdigest(),
        },
        "constraintRefs": ([{"constraintRef": "STC2", "reason": "T1 wires generated client usage."}] if task_id == "T1" else []),
        "caveats": [],
    })

payload = {
    "schemaVersion": 2,
    "kind": "superpower-adapter.source-truth-constraints",
    "generatedBy": "superpower-adapter",
    "planPath": "docs/superpowers/plans/example.md",
    "sourceTruthReportPath": "docs/superpowers/plans/example.source-truth-report.json",
    "status": "passed",
    "taskRouting": {
        "status": "confirmed",
        "planTaskFormat": "superpower-adapter-plan-task-heading-v1",
        "fingerprintAlgorithm": "sha256:superpower-adapter-task-text-v1",
        "selectedConstraintsFrozen": True,
        "refreshPolicy": "refresh-taskConstraintRefs-and-fingerprints-only",
    },
    "constraintSets": [
        {
            "constraintId": "STC1",
            "title": "Generated service clients are authoritative",
            "destination": {"kind": "global", "reason": "Generated clients must not be edited by any task."},
            "hardConstraint": True,
            "sourceRefs": [{"path": "src/services/generated/client.ts", "role": "truth", "edit": "never"}],
            "constraints": {
                "implementation": ["Do not edit generated service clients."],
                "test": ["Test against the generated client shape."],
                "review": ["Confirm generated clients were not modified."],
                "general": ["Backend contract is the authority for service fields."],
            },
            "caveats": [],
        },
        {
            "constraintId": "STC2",
            "title": "Permission keys must already exist",
            "destination": {"kind": "task-bound", "reason": "Only T1 wires permission checks."},
            "hardConstraint": True,
            "constraints": {
                "implementation": ["Use existing permission keys only."],
                "test": [],
                "review": ["Reject newly invented permission keys."],
                "general": [],
            },
            "caveats": [],
        },
    ],
    "globalConstraintRefs": [{"constraintRef": "STC1", "reason": "Visible to every implementation and review task."}],
    "taskConstraintRefs": tasks,
    "caveats": ["Full report is planning/audit only."],
}
out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --validate-only --strict --execution-ready --plan-path "$TMP_DIR/plan.md"
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --fingerprint-preflight --strict --execution-ready --plan-path "$TMP_DIR/plan.md"

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --task-id T1 --role implementer --strict --execution-ready >"$TMP_DIR/t1-implementer.md"
require_text '## Source-of-Truth Constraints' "$TMP_DIR/t1-implementer.md"
require_text 'Task ID: `T1`' "$TMP_DIR/t1-implementer.md"
require_text 'Do not edit generated service clients.' "$TMP_DIR/t1-implementer.md"
require_text 'Test against the generated client shape.' "$TMP_DIR/t1-implementer.md"
require_text 'Backend contract is the authority' "$TMP_DIR/t1-implementer.md"
require_text 'Use existing permission keys only.' "$TMP_DIR/t1-implementer.md"
reject_text 'Confirm generated clients were not modified.' "$TMP_DIR/t1-implementer.md"
reject_text 'Applies to:' "$TMP_DIR/t1-implementer.md"

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --task-id T1 --role reviewer --strict --execution-ready >"$TMP_DIR/t1-reviewer.md"
require_text 'Confirm generated clients were not modified.' "$TMP_DIR/t1-reviewer.md"
require_text 'Reject newly invented permission keys.' "$TMP_DIR/t1-reviewer.md"

python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --task-id T2 --role implementer --strict --execution-ready >"$TMP_DIR/t2-implementer.md"
require_text 'Do not edit generated service clients.' "$TMP_DIR/t2-implementer.md"
reject_text 'Use existing permission keys only.' "$TMP_DIR/t2-implementer.md"

if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --task-id T404 --role implementer --strict --execution-ready >"$TMP_DIR/unknown-task.out" 2>&1; then
  printf 'Expected unknown task-id to fail\n' >&2
  exit 1
fi
require_text 'taskConstraintRefs must contain exactly one entry for taskId T404' "$TMP_DIR/unknown-task.out"

cp "$TMP_DIR/plan.md" "$TMP_DIR/changed-plan.md"
printf '\nManual edit after review.\n' >>"$TMP_DIR/changed-plan.md"
if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --fingerprint-preflight --strict --execution-ready --plan-path "$TMP_DIR/changed-plan.md" >"$TMP_DIR/fingerprint-fail.out" 2>&1; then
  printf 'Expected changed plan fingerprint preflight to fail\n' >&2
  exit 1
fi
require_text 'fingerprint mismatch' "$TMP_DIR/fingerprint-fail.out"

if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v2.json" --task 'Task 1' --role implementer >"$TMP_DIR/v2-legacy-task.out" 2>&1; then
  printf 'Expected schemaVersion 2 legacy --task routing to fail\n' >&2
  exit 1
fi
require_text 'schemaVersion 2 source-truth constraints require --task-id' "$TMP_DIR/v2-legacy-task.out"

python3 - "$TMP_DIR/constraints-v2.json" "$TMP_DIR/unknown-category-v2.json" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
payload["constraintSets"][0]["constraints"]["unknown"] = ["bad"]
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/unknown-category-v2.json" --validate-only --strict --execution-ready >"$TMP_DIR/unknown-category-v2.out" 2>&1; then
  printf 'Expected strict unknown category to fail\n' >&2
  exit 1
fi
require_text 'unsupported categories' "$TMP_DIR/unknown-category-v2.out"

cat >"$TMP_DIR/not-configured-v2.json" <<'JSON'
{
  "schemaVersion": 2,
  "kind": "superpower-adapter.source-truth-constraints",
  "planPath": "docs/superpowers/plans/example.md",
  "status": "not_configured",
  "constraintSets": [],
  "taskRouting": {
    "status": "confirmed",
    "selectedConstraintsFrozen": true
  },
  "globalConstraintRefs": [],
  "taskConstraintRefs": []
}
JSON
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/not-configured-v2.json" --task-id T1 --role implementer >"$TMP_DIR/not-configured-v2.md"
require_text 'No configured source-of-truth constraints' "$TMP_DIR/not-configured-v2.md"

cat >"$TMP_DIR/blocked-v2.json" <<'JSON'
{
  "schemaVersion": 2,
  "kind": "superpower-adapter.source-truth-constraints",
  "planPath": "docs/superpowers/plans/example.md",
  "status": "blocked",
  "constraintSets": [],
  "taskRouting": {
    "status": "confirmed",
    "selectedConstraintsFrozen": true
  },
  "globalConstraintRefs": [],
  "taskConstraintRefs": []
}
JSON
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/blocked-v2.json" --task-id T1 --role implementer >"$TMP_DIR/blocked-v2.md"
require_text 'blocked; stop and return to planning' "$TMP_DIR/blocked-v2.md"

cat >"$TMP_DIR/constraints-v1.json" <<'JSON'
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
      "constraints": {
        "implementation": ["Legacy implementation constraint."],
        "review": ["Legacy review constraint."],
        "test": [],
        "general": []
      }
    }
  ],
  "caveats": ["Legacy v1 compatibility only."]
}
JSON
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v1.json" --validate-only --strict
python3 "$ROOT/overlays/scripts/source_truth_render.py" "$TMP_DIR/constraints-v1.json" --task 'Task 1' --role implementer >"$TMP_DIR/v1-implementer.md"
require_text 'Legacy implementation constraint.' "$TMP_DIR/v1-implementer.md"
reject_text 'Legacy review constraint.' "$TMP_DIR/v1-implementer.md"

printf 'source-truth render smoke OK\n'
