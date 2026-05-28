#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
SCRIPT="${TARGET_INPUT}/scripts/wiki_context_render.py"

if [[ ! -f "$SCRIPT" ]]; then
  printf 'Missing wiki context renderer: %s\n' "$SCRIPT" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PLAN="$TMP/plan.md"
CONTEXT="$TMP/plan.wiki-context.json"
cat > "$PLAN" <<'MD'
# Example Plan

### Task T1: Implement path-based form updates
Update field writes to use path-based updates.

### Task T2: Add contract coverage
Cover the shared payload contract.
MD

read -r T1_HASH T2_HASH <<<"$(python3 - <<'PY' "$PLAN"
from pathlib import Path
import hashlib
import re
import sys

plan_path = Path(sys.argv[1])
text = plan_path.read_text(encoding='utf-8').replace('\r\n', '\n').replace('\r', '\n')
lines = text.split('\n')
task_re = re.compile(r'^### Task\s+([A-Za-z0-9][A-Za-z0-9_-]*):\s*(.+?)\s*$')
heading_re = re.compile(r'^#{1,3}\s+')

hashes = {}
idx = 0
while idx < len(lines):
    match = task_re.match(lines[idx])
    if not match:
        idx += 1
        continue
    task_id = match.group(1)
    start = idx
    idx += 1
    while idx < len(lines) and not task_re.match(lines[idx]) and not heading_re.match(lines[idx]):
        idx += 1
    block = lines[start:idx]
    while block and not block[0].strip():
        block.pop(0)
    while block and not block[-1].strip():
        block.pop()
    normalized = '\n'.join(line.rstrip() for line in block) + '\n'
    hashes[task_id] = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

print(hashes['T1'], hashes['T2'])
PY
)"

cat > "$CONTEXT" <<JSON
{
  "schemaVersion": 3,
  "kind": "superpower-adapter.wiki-context",
  "generatedBy": "superpower-adapter",
  "planPath": "${PLAN}",
  "taskRouting": {
    "status": "confirmed",
    "planTaskFormat": "superpower-adapter-plan-task-heading-v1",
    "fingerprintAlgorithm": "sha256:superpower-adapter-task-text-v1",
    "selectedSectionsFrozen": true,
    "refreshPolicy": "refresh-taskWikiRefs-and-fingerprints-only"
  },
  "wikiPages": [
    {
      "root": "project",
      "source": "local",
      "displayPath": ".superpowers/wiki/frontend/hook-guidelines.md",
      "localPath": "frontend/hook-guidelines.md",
      "documentContext": {
        "title": "Hook Guidelines",
        "overview": "Project-private hook rules for generated form adapters.",
        "contextSource": ".superpowers/wiki/frontend/hook-guidelines.index.md"
      },
      "sections": [
        {
          "sectionId": "path-based-update",
          "section_name": "path-based-update",
          "readDepth": "full",
          "relevance": "direct",
          "confidence": "high",
          "reason": "Field updates are in scope.",
          "relevanceTo": "form field updates and adapter state writes",
          "hardConstraint": true,
          "constraints": {
            "implementation": ["Use updateByPath(path, value) for all field updates."],
            "test": ["Verify nested path updates preserve change tracking."],
            "review": ["Reject direct props.model mutation."],
            "general": ["Keep path strings stable across adapter layers.", "Preserve Unicode sentinel  in rendered constraints."]
          },
          "reread": {
            "root": "project",
            "source": "local",
            "localPath": "frontend/hook-guidelines.md",
            "sectionId": "path-based-update",
            "includeDocumentContext": true
          },
          "sourceAnchors": [
            {"heading": "Path-Based Update", "excerpt": "All field updates MUST use updateByPath(path, value)."}
          ],
          "destination": {
            "kind": "task-bound",
            "reason": "This hard constraint applies to the task that changes field update behavior."
          }
        },
        {
          "sectionId": "deep-path",
          "section_name": "deep-path",
          "readDepth": "full",
          "relevance": "supporting",
          "confidence": "medium",
          "reason": "Nested paths are nearby selected context.",
          "relevanceTo": "nested object paths",
          "hardConstraint": false,
          "constraints": {
            "implementation": ["Use dot-notation for nested object paths."],
            "test": [],
            "review": [],
            "general": []
          },
          "sourceAnchors": [
            {"heading": "Deep Path Handling", "excerpt": "Use dot-notation paths like user.address.city."}
          ],
          "destination": {
            "kind": "planning-only",
            "reason": "This section shapes task design but does not need execution prompt injection."
          }
        }
      ]
    },
    {
      "root": "shared",
      "source": "github_mcp",
      "displayPath": ".shared-superpowers/wiki/frontend/contracts.md",
      "wikiPath": "frontend/contracts.md",
      "revision": {
        "ref": "main",
        "commitSha": "abcdef1234567890",
        "shortSha": "abcdef1"
      },
      "documentContext": {
        "title": "Shared Frontend Contracts",
        "overview": "Portable shared contract rules.",
        "contextSource": "frontend/contracts.index.md"
      },
      "sections": [
        {
          "sectionId": "contract-review",
          "section_name": "contract-review",
          "readDepth": "full",
          "relevance": "direct",
          "confidence": "high",
          "reason": "Task touches shared contract shape.",
          "relevanceTo": "shared contract payload naming",
          "hardConstraint": true,
          "constraints": {
            "implementation": ["Keep shared payload names portable."],
            "test": ["Add contract coverage for shared payload names."],
            "review": ["Check that no project-specific environment names leak into shared docs."],
            "general": []
          },
          "reread": {
            "root": "shared",
            "source": "github_mcp",
            "wikiPath": "frontend/contracts.md",
            "sectionId": "contract-review",
            "includeDocumentContext": true
          },
          "sourceAnchors": [
            {"heading": "Contract Review", "excerpt": "Shared payload names must stay portable."}
          ],
          "destination": {
            "kind": "global",
            "reason": "Portable shared contract naming must be visible to every implementation and review task."
          }
        }
      ]
    }
  ],
  "globalWikiRefs": [
    {
      "sectionRef": {
        "root": "shared",
        "source": "github_mcp",
        "displayPath": ".shared-superpowers/wiki/frontend/contracts.md",
        "wikiPath": "frontend/contracts.md",
        "sectionId": "contract-review"
      },
      "reason": "This shared contract applies to every task and reviewer prompt."
    }
  ],
  "taskWikiRefs": [
    {
      "taskId": "T1",
      "taskTitle": "Implement path-based form updates",
      "taskFingerprint": {
        "algorithm": "sha256",
        "normalization": "superpower-adapter-task-text-v1",
        "source": "${PLAN}#T1",
        "hash": "${T1_HASH}"
      },
      "wikiRefs": [
        {
          "sectionRef": {
            "root": "project",
            "source": "local",
            "displayPath": ".superpowers/wiki/frontend/hook-guidelines.md",
            "localPath": "frontend/hook-guidelines.md",
            "sectionId": "path-based-update"
          },
          "reason": "T1 changes form adapter state writes and must follow the path update rule."
        }
      ],
      "caveats": []
    },
    {
      "taskId": "T2",
      "taskTitle": "Add contract coverage",
      "taskFingerprint": {
        "algorithm": "sha256",
        "normalization": "superpower-adapter-task-text-v1",
        "source": "${PLAN}#T2",
        "hash": "${T2_HASH}"
      },
      "wikiRefs": [],
      "caveats": []
    }
  ],
  "caveats": []
}
JSON

assert_contains() {
  local label="$1"
  local needle="$2"
  local haystack="$3"
  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'Expected %s to contain %s\n%s\n' "$label" "$needle" "$haystack" >&2
    exit 1
  fi
}

assert_not_contains() {
  local label="$1"
  local needle="$2"
  local haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    printf 'Expected %s not to contain %s\n%s\n' "$label" "$needle" "$haystack" >&2
    exit 1
  fi
}

EXAMPLE="${TARGET_INPUT}/contracts/wiki-context-v3.example.jsonc"
if [[ ! -f "$EXAMPLE" ]]; then
  printf 'Missing wiki context example contract: %s\n' "$EXAMPLE" >&2
  exit 1
fi
EXAMPLE_TEXT="$(python3 - <<'PY' "$EXAMPLE"
from pathlib import Path
import sys
print(Path(sys.argv[1]).read_text(encoding='utf-8'))
PY
)"
assert_contains "example contract" 'AI-facing authoring contract' "$EXAMPLE_TEXT"
assert_contains "example contract" 'Do not inspect scripts/wiki_context_render.py to infer this format' "$EXAMPLE_TEXT"
assert_contains "example contract" '--validate-only --strict' "$EXAMPLE_TEXT"
assert_contains "example contract" '--execution-ready --plan-path' "$EXAMPLE_TEXT"
assert_contains "example contract" '--fingerprint-preflight' "$EXAMPLE_TEXT"

python3 "$SCRIPT" "$CONTEXT" --validate-only --strict --execution-ready --plan-path "$PLAN" >/dev/null
python3 "$SCRIPT" "$CONTEXT" --fingerprint-preflight --strict --execution-ready --plan-path "$PLAN" >/dev/null

T1_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task-id T1 --role implementer --strict --execution-ready)"
assert_contains "T1 render" 'Hook Guidelines' "$T1_OUT"
assert_contains "T1 render" 'Shared Frontend Contracts' "$T1_OUT"
assert_contains "T1 render" 'Use updateByPath(path, value)' "$T1_OUT"
assert_contains "T1 render" 'Keep shared payload names portable' "$T1_OUT"
assert_contains "T1 render" 'Preserve Unicode sentinel  in rendered constraints.' "$T1_OUT"
CP936_OUT="$(PYTHONIOENCODING=cp936:strict python3 "$SCRIPT" "$CONTEXT" --task-id T1 --role implementer --strict --execution-ready)"
assert_contains "cp936 render" 'Preserve Unicode sentinel  in rendered constraints.' "$CP936_OUT"
assert_not_contains "T1 render" 'Use dot-notation for nested object paths' "$T1_OUT"
assert_not_contains "T1 render" 'No selected wiki constraints for this role.' "$T1_OUT"
assert_not_contains "T1 render" 'planning-only' "$T1_OUT"

T2_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task-id T2 --role implementer --strict --execution-ready)"
assert_contains "T2 render" 'Shared Frontend Contracts' "$T2_OUT"
assert_contains "T2 render" 'Keep shared payload names portable' "$T2_OUT"
assert_not_contains "T2 render" 'Use updateByPath(path, value)' "$T2_OUT"
assert_not_contains "T2 render" 'Use dot-notation for nested object paths' "$T2_OUT"

REVIEW_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task-id T1 --role reviewer --strict --execution-ready)"
assert_contains "reviewer render" 'Reject direct props.model mutation' "$REVIEW_OUT"
assert_contains "reviewer render" 'Check that no project-specific environment names leak into shared docs' "$REVIEW_OUT"

REREAD_T1="$(python3 "$SCRIPT" "$CONTEXT" --task-id T1 --reread-list --strict --execution-ready)"
assert_contains "T1 reread list" 'path-based-update' "$REREAD_T1"
assert_contains "T1 reread list" 'contract-review' "$REREAD_T1"
assert_not_contains "T1 reread list" 'deep-path' "$REREAD_T1"

REREAD_T2="$(python3 "$SCRIPT" "$CONTEXT" --task-id T2 --reread-list --strict --execution-ready)"
assert_contains "T2 reread list" 'contract-review' "$REREAD_T2"
assert_not_contains "T2 reread list" 'path-based-update' "$REREAD_T2"

EMPTY_CONTEXT="$TMP/empty.wiki-context.json"
printf '{"schemaVersion":3,"kind":"superpower-adapter.wiki-context","wikiPages":[]}' > "$EMPTY_CONTEXT"
EMPTY_OUT="$(python3 "$SCRIPT" "$EMPTY_CONTEXT" --role implementer --strict)"
assert_contains "empty render" 'No selected wiki constraints for this role.' "$EMPTY_OUT"

UNKNOWN_TASK_OUT="$TMP/unknown-task.out"
if python3 "$SCRIPT" "$CONTEXT" --task-id T99 --role implementer --strict --execution-ready >"$UNKNOWN_TASK_OUT" 2>&1; then
  printf 'Expected unknown task-id to fail\n' >&2
  exit 1
fi
assert_contains "unknown task failure" 'taskWikiRefs must contain exactly one entry for taskId T99' "$(cat "$UNKNOWN_TASK_OUT")"

LEGACY="$TMP/plan.wiki-context.md"
printf '# Legacy\n' > "$LEGACY"
if python3 "$SCRIPT" "$LEGACY" --role implementer >/tmp/wiki-context-legacy.out 2>&1; then
  printf 'Expected legacy markdown sidecar to fail\n' >&2
  exit 1
fi
assert_contains "legacy failure" 'Legacy .wiki-context.md is not supported' "$(cat /tmp/wiki-context-legacy.out)"

BAD_SCHEMA="$TMP/bad-schema.wiki-context.json"
printf '{"schemaVersion":2,"kind":"superpower-adapter.wiki-context","wikiPages":[]}' > "$BAD_SCHEMA"
if python3 "$SCRIPT" "$BAD_SCHEMA" --validate-only >/tmp/wiki-context-bad-schema.out 2>&1; then
  printf 'Expected bad schema to fail\n' >&2
  exit 1
fi
assert_contains "bad schema failure" 'schemaVersion must be 3' "$(cat /tmp/wiki-context-bad-schema.out)"

BAD_CATEGORY="$TMP/bad-category.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$BAD_CATEGORY"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['wikiPages'][0]['sections'][0]['constraints']['security'] = ['unknown category']
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if PYTHONIOENCODING=cp936:strict python3 "$SCRIPT" "$BAD_CATEGORY" --role implementer --strict >/tmp/wiki-context-bad-category.out 2>&1; then
  printf 'Expected unknown category to fail in strict mode\n' >&2
  exit 1
fi
assert_contains "bad category failure" 'unsupported categories: security' "$(cat /tmp/wiki-context-bad-category.out)"
assert_not_contains "bad category failure" 'UnicodeEncodeError' "$(cat /tmp/wiki-context-bad-category.out)"

BAD_SECTION_CONTEXT="$TMP/bad-section-context.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$BAD_SECTION_CONTEXT"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['wikiPages'][0]['sections'][0]['documentContext'] = {'title': 'duplicated'}
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if python3 "$SCRIPT" "$BAD_SECTION_CONTEXT" --role implementer --strict >/tmp/wiki-context-bad-section-context.out 2>&1; then
  printf 'Expected section-level documentContext to fail in strict mode\n' >&2
  exit 1
fi
assert_contains "bad section context failure" 'documentContext is not allowed' "$(cat /tmp/wiki-context-bad-section-context.out)"

TASKBOUND_MISSING="$TMP/taskbound-missing.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$TASKBOUND_MISSING"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['wikiPages'][0]['sections'][0]['destination'] = {
    'kind': 'task-bound',
    'reason': 'legacy routing claims this applies to T1'
}
data['wikiPages'][0]['sections'][0]['appliesTo'] = ['T1']
data['taskWikiRefs'][0]['wikiRefs'] = []
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if python3 "$SCRIPT" "$TASKBOUND_MISSING" --validate-only --strict --execution-ready --plan-path "$PLAN" >/tmp/wiki-context-taskbound-missing.out 2>&1; then
  printf 'Expected missing taskWikiRefs for task-bound section to fail\n' >&2
  exit 1
fi
assert_contains "task-bound missing failure" 'task-bound' "$(cat /tmp/wiki-context-taskbound-missing.out)"

UNRESOLVED_REF="$TMP/unresolved-ref.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$UNRESOLVED_REF"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['globalWikiRefs'][0]['sectionRef']['sectionId'] = 'missing-section'
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if python3 "$SCRIPT" "$UNRESOLVED_REF" --validate-only --strict --execution-ready --plan-path "$PLAN" >/tmp/wiki-context-unresolved-ref.out 2>&1; then
  printf 'Expected unresolved sectionRef to fail\n' >&2
  exit 1
fi
assert_contains "unresolved ref failure" 'missing-section' "$(cat /tmp/wiki-context-unresolved-ref.out)"

BAD_DESTINATION="$TMP/bad-destination.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$BAD_DESTINATION"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['wikiPages'][0]['sections'][0]['destination']['kind'] = 'planning-only'
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if python3 "$SCRIPT" "$BAD_DESTINATION" --validate-only --strict --execution-ready --plan-path "$PLAN" >/tmp/wiki-context-bad-destination.out 2>&1; then
  printf 'Expected hard/direct planning-only destination to fail\n' >&2
  exit 1
fi
assert_contains "bad destination failure" 'planning-only' "$(cat /tmp/wiki-context-bad-destination.out)"

PLAN_EDITED="$TMP/plan-edited.md"
python3 - <<'PY' "$PLAN" "$PLAN_EDITED"
from pathlib import Path
import sys
src, dst = map(Path, sys.argv[1:3])
text = src.read_text(encoding='utf-8')
text = text.replace('Update field writes to use path-based updates.', 'Update field writes to use path-based updates and preserve nested change tracking.')
dst.write_text(text, encoding='utf-8')
PY
if python3 "$SCRIPT" "$CONTEXT" --fingerprint-preflight --strict --execution-ready --plan-path "$PLAN_EDITED" >/tmp/wiki-context-bad-fingerprint.out 2>&1; then
  printf 'Expected fingerprint preflight mismatch to fail\n' >&2
  exit 1
fi
assert_contains "bad fingerprint failure" 'fingerprint' "$(cat /tmp/wiki-context-bad-fingerprint.out)"

printf 'wiki-context-json-render smoke test complete\n'
