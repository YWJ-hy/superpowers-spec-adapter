#!/usr/bin/env bash
set -euo pipefail

# Smoke test for the mechanical wiki-context sidecar generator:
#   wiki-researcher selection JSON --scaffold--> complete-shaped sidecar
#   plan headings            --scaffold-tasks--> taskWikiRefs scaffold (idempotent)
#   author edits routing -> --bind-fingerprints --execution-ready -> --fingerprint-preflight
# Proves the generate-then-edit chain so the planning agent edits a complete structure instead of
# hand-authoring deep JSON (which dropped fields like reread/destination and failed validation late).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
SCRIPT="${TARGET_INPUT}/scripts/wiki_context_render.py"
SELECTION_EXAMPLE="${TARGET_INPUT}/contracts/wiki-selection-v1.example.jsonc"

if [[ ! -f "$SCRIPT" ]]; then
  printf 'Missing wiki context renderer: %s\n' "$SCRIPT" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'Expected %s to contain %s\n%s\n' "$label" "$needle" "$haystack" >&2
    exit 1
  fi
}

assert_not_contains() {
  local label="$1" needle="$2" haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    printf 'Expected %s not to contain %s\n%s\n' "$label" "$needle" "$haystack" >&2
    exit 1
  fi
}

# --- The shipped selection contract documents the researcher OUTPUT shape. ---
if [[ ! -f "$SELECTION_EXAMPLE" ]]; then
  printf 'Missing wiki selection example contract: %s\n' "$SELECTION_EXAMPLE" >&2
  exit 1
fi
SELECTION_TEXT="$(python3 - <<'PY' "$SELECTION_EXAMPLE"
from pathlib import Path
import sys
print(Path(sys.argv[1]).read_text(encoding='utf-8'))
PY
)"
assert_contains "selection contract" 'wiki-researcher OUTPUT contract' "$SELECTION_TEXT"
assert_contains "selection contract" '--scaffold' "$SELECTION_TEXT"
# The generator fills these mechanically, so the selection contract must NOT model them as inputs.
assert_not_contains "selection contract" '"taskWikiRefs"' "$SELECTION_TEXT"
assert_not_contains "selection contract" '"taskFingerprint"' "$SELECTION_TEXT"
assert_not_contains "selection contract" '"reread"' "$SELECTION_TEXT"

PLAN="$TMP/plan.md"
SEL="$TMP/plan.wiki-selection.json"
CTX="$TMP/plan.wiki-context.json"

cat > "$PLAN" <<'MD'
# Example Plan

### Task T1: Implement path-based form updates
Update field writes to use path-based updates.

### Task T2: Add contract coverage
Cover the shared payload contract.
MD

# A wiki-researcher selection: one local hard section, one local soft section, one github_mcp hard
# section, plus the github_mcp shared wiki identity.
cat > "$SEL" <<'JSON'
{
  "status": "ok",
  "phase": "plan",
  "sharedWikiSource": {
    "kind": "github_mcp",
    "displayRoot": ".shared-superpowers/wiki",
    "repoUrl": "https://github.com/acme/platform-wiki.git",
    "baseBranch": "master",
    "revision": { "ref": "master", "commitSha": "abcdef1234567890", "shortSha": "abcdef1" }
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
          "readDepth": "full",
          "relevance": "direct",
          "confidence": "high",
          "reason": "Field updates are in scope.",
          "relevanceTo": "form field updates",
          "hardConstraint": true,
          "constraints": {
            "implementation": ["Use updateByPath(path, value) for all field updates."],
            "test": ["Verify nested path updates preserve change tracking."],
            "review": ["Reject direct props.model mutation."],
            "general": []
          },
          "sourceAnchors": [
            {"heading": "Path-Based Update", "excerpt": "All field updates MUST use updateByPath(path, value)."}
          ]
        },
        {
          "sectionId": "deep-path",
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
          }
        }
      ]
    },
    {
      "root": "shared",
      "source": "github_mcp",
      "displayPath": ".shared-superpowers/wiki/frontend/contracts.md",
      "wikiPath": "frontend/contracts.md",
      "revision": { "ref": "main", "commitSha": "abcdef1234567890", "shortSha": "abcdef1" },
      "documentContext": {
        "title": "Shared Frontend Contracts",
        "overview": "Portable shared contract rules.",
        "contextSource": "frontend/contracts.index.md"
      },
      "sections": [
        {
          "sectionId": "contract-review",
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
          }
        }
      ]
    }
  ],
  "caveats": []
}
JSON

# Preserve a pristine copy: --scaffold now consumes (removes) the selection it reads on success, and the
# negative cases below build their malformed selections from this source.
SEL_SRC="$TMP/selection-src.json"
cp "$SEL" "$SEL_SRC"

# --- Pass 0: --keep-selection opts out of removal (tests/debugging/regenerate from an edited selection). ---
KEEP_CTX="$TMP/keep.wiki-context.json"
KEEP_SEL="$TMP/keep.wiki-selection.json"
cp "$SEL_SRC" "$KEEP_SEL"
python3 "$SCRIPT" "$KEEP_CTX" --scaffold "$KEEP_SEL" --plan-path "$PLAN" --strict --keep-selection >/dev/null
if [[ ! -f "$KEEP_SEL" ]]; then
  printf 'Expected --keep-selection to preserve the selection %s\n' "$KEEP_SEL" >&2
  exit 1
fi

# --- Pass 1: --scaffold builds a complete-shaped sidecar from the selection. ---
SCAFFOLD_OUT="$(python3 "$SCRIPT" "$CTX" --scaffold "$SEL" --plan-path "$PLAN" --strict)"
assert_contains "scaffold output" 'scaffolded wiki context with 2 page(s)' "$SCAFFOLD_OUT"
# The selection is a transient intermediate: scaffolding consumes and removes it on success, leaving only
# the plan and its generated .wiki-context.json.
assert_contains "scaffold output" 'removed consumed selection' "$SCAFFOLD_OUT"
if [[ -f "$SEL" ]]; then
  printf 'Expected --scaffold to remove the consumed selection %s\n' "$SEL" >&2
  exit 1
fi
# The freshly scaffolded skeleton must already pass structural validation (no dropped fields).
python3 "$SCRIPT" "$CTX" --validate-only --strict >/dev/null

python3 - "$CTX" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
assert d['schemaVersion'] == 3 and d['kind'] == 'superpower-adapter.wiki-context'
assert d['generatedBy'] == 'superpower-adapter', d.get('generatedBy')
# taskRouting block is fully present and pre-confirmation.
tr = d['taskRouting']
assert tr['status'] == 'candidate_sections_only', tr['status']
assert tr['selectedSectionsFrozen'] is False
assert tr['planTaskFormat'] == 'superpower-adapter-plan-task-heading-v1'
assert tr['fingerprintAlgorithm'] == 'sha256:superpower-adapter-task-text-v1'
# Shared wiki identity captured because a github_mcp page was selected.
assert d['sharedWiki']['repoUrl'] == 'https://github.com/acme/platform-wiki.git'
assert d['sharedWiki']['baseBranch'] == 'master'
pages = d['wikiPages']
# Local hard section: reread auto-derived with localPath; destination defaulted task-bound, reason empty.
s0 = pages[0]['sections'][0]
assert s0['hardConstraint'] is True
assert s0['reread']['localPath'] == 'frontend/hook-guidelines.md'
assert s0['reread']['includeDocumentContext'] is True
assert 'wikiPath' not in s0['reread']
assert s0['destination'] == {'kind': 'task-bound', 'reason': ''}, s0['destination']
# Soft section: no reread, planning-only default.
s1 = pages[0]['sections'][1]
assert s1['hardConstraint'] is False
assert 'reread' not in s1
assert s1['destination']['kind'] == 'planning-only'
# Constraints normalized to exactly the four categories.
assert set(s1['constraints']) == {'implementation', 'test', 'review', 'general'}
# github_mcp hard section: reread uses wikiPath, never localPath.
sc = pages[1]['sections'][0]
assert sc['reread']['wikiPath'] == 'frontend/contracts.md'
assert 'localPath' not in sc['reread']
# Routing collections seeded empty for the author / --scaffold-tasks to fill.
assert d['taskWikiRefs'] == []
assert d['globalWikiRefs'] == []
print('scaffold structure ok')
PY

# --- Pass 2: --scaffold-tasks adds one taskWikiRefs entry per stable plan task. ---
TASKS_OUT="$(python3 "$SCRIPT" "$CTX" --scaffold-tasks --plan-path "$PLAN" --strict)"
assert_contains "scaffold-tasks output" 'scaffolded 2 task(s): T1, T2' "$TASKS_OUT"
python3 - "$CTX" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
refs = {r['taskId']: r for r in d['taskWikiRefs']}
assert set(refs) == {'T1', 'T2'}
assert refs['T1']['taskTitle'] == 'Implement path-based form updates'
assert refs['T2']['taskTitle'] == 'Add contract coverage'
# wikiRefs start empty (author routing); no fingerprint stamped yet (that is --bind-fingerprints' job).
assert refs['T1']['wikiRefs'] == [] and refs['T2']['wikiRefs'] == []
assert 'taskFingerprint' not in refs['T1']
print('scaffold-tasks structure ok')
PY

# --- Author edits ONLY semantic routing in the generated sidecar. ---
python3 - "$CTX" <<'PY'
import json, sys
f = sys.argv[1]
d = json.load(open(f, encoding='utf-8'))
d['wikiPages'][0]['sections'][0]['destination']['reason'] = 'T1 changes field update behavior.'
d['wikiPages'][0]['sections'][1]['destination']['reason'] = 'Shaped task design only; not injected.'
contract = d['wikiPages'][1]['sections'][0]['destination']
contract['kind'] = 'global'  # override the task-bound default
contract['reason'] = 'Portable contract naming applies to every task and reviewer.'
d['globalWikiRefs'] = [{
    'sectionRef': {'root': 'shared', 'source': 'github_mcp',
                   'displayPath': '.shared-superpowers/wiki/frontend/contracts.md',
                   'wikiPath': 'frontend/contracts.md', 'sectionId': 'contract-review'},
    'reason': 'Global shared contract for all tasks and reviewers.'}]
for r in d['taskWikiRefs']:
    if r['taskId'] == 'T1':
        r['wikiRefs'] = [{
            'sectionRef': {'root': 'project', 'source': 'local',
                           'displayPath': '.superpowers/wiki/frontend/hook-guidelines.md',
                           'localPath': 'frontend/hook-guidelines.md', 'sectionId': 'path-based-update'},
            'reason': 'T1 must follow the path update rule.'}]
d['taskRouting']['status'] = 'confirmed'
d['taskRouting']['selectedSectionsFrozen'] = True
json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
PY

# --- Mechanical tail (existing): stamp fingerprints + gate execution readiness, then preflight. ---
BIND_OUT="$(python3 "$SCRIPT" "$CTX" --bind-fingerprints --strict --execution-ready --plan-path "$PLAN")"
assert_contains "bind output" 'bound taskFingerprint for 2 task(s)' "$BIND_OUT"
python3 "$SCRIPT" "$CTX" --fingerprint-preflight --strict --execution-ready --plan-path "$PLAN" >/dev/null
# The fully routed sidecar renders task-scoped constraints for execution.
T1_RENDER="$(python3 "$SCRIPT" "$CTX" --task-id T1 --role implementer --strict --execution-ready)"
assert_contains "T1 render" 'Use updateByPath(path, value)' "$T1_RENDER"
assert_contains "T1 render" 'Keep shared payload names portable' "$T1_RENDER"

# --- Re-running --scaffold-tasks is idempotent: author-entered wikiRefs survive. ---
python3 "$SCRIPT" "$CTX" --scaffold-tasks --plan-path "$PLAN" --strict >/dev/null
python3 - "$CTX" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
t1 = next(r for r in d['taskWikiRefs'] if r['taskId'] == 'T1')
assert any(w['sectionRef']['sectionId'] == 'path-based-update' for w in t1['wikiRefs']), 'lost wikiRefs on rescaffold'
# Preserved fingerprint stays present too (bind owns it; rescaffold must not strip it).
assert 'taskFingerprint' in t1
print('idempotent rescaffold ok')
PY

# --- --scaffold-tasks drops (and reports) tasks no longer in the plan. ---
DROP_CTX="$TMP/drop.wiki-context.json"
cp "$CTX" "$DROP_CTX"
DROP_PLAN="$TMP/plan-drop.md"
printf '# P\n\n### Task T1: Implement path-based form updates\nUpdate field writes to use path-based updates.\n' > "$DROP_PLAN"
DROP_OUT="$(python3 "$SCRIPT" "$DROP_CTX" --scaffold-tasks --plan-path "$DROP_PLAN" --strict 2>&1)"
assert_contains "drop drift" 'dropped taskWikiRefs entry no longer in plan: T2' "$DROP_OUT"

# --- Negative: a malformed selection fails at the shallow input, not deep in the sidecar. ---
BAD_CAT_SEL="$TMP/bad-category.wiki-selection.json"
python3 - "$SEL_SRC" "$BAD_CAT_SEL" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
d = json.load(open(src, encoding='utf-8'))
d['wikiPages'][0]['sections'][0]['constraints']['security'] = ['unsupported category']
open(dst, 'w', encoding='utf-8').write(json.dumps(d))
PY
if python3 "$SCRIPT" "$TMP/bad.json" --scaffold "$BAD_CAT_SEL" --strict >/tmp/wiki-scaffold-bad-category.out 2>&1; then
  printf 'Expected --scaffold to reject unsupported constraint category\n' >&2
  exit 1
fi
assert_contains "bad category" 'unsupported categories: security' "$(cat /tmp/wiki-scaffold-bad-category.out)"
# A failed scaffold must not delete the selection — it stays in place for repair.
if [[ ! -f "$BAD_CAT_SEL" ]]; then
  printf 'Expected a failed --scaffold to keep the selection %s for repair\n' "$BAD_CAT_SEL" >&2
  exit 1
fi

BAD_PATH_SEL="$TMP/bad-path.wiki-selection.json"
python3 - "$SEL_SRC" "$BAD_PATH_SEL" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
d = json.load(open(src, encoding='utf-8'))
for key in ('displayPath', 'localPath', 'wikiPath', 'path'):
    d['wikiPages'][0].pop(key, None)
open(dst, 'w', encoding='utf-8').write(json.dumps(d))
PY
if python3 "$SCRIPT" "$TMP/bad2.json" --scaffold "$BAD_PATH_SEL" --strict >/tmp/wiki-scaffold-bad-path.out 2>&1; then
  printf 'Expected --scaffold to reject a page with no path field\n' >&2
  exit 1
fi
assert_contains "bad path" 'must include one of displayPath' "$(cat /tmp/wiki-scaffold-bad-path.out)"

# --- Negative: combining the two scaffold passes in one invocation is rejected. ---
if python3 "$SCRIPT" "$CTX" --scaffold "$SEL_SRC" --scaffold-tasks --plan-path "$PLAN" >/tmp/wiki-scaffold-combo.out 2>&1; then
  printf 'Expected --scaffold + --scaffold-tasks together to fail\n' >&2
  exit 1
fi
assert_contains "combo guard" 'separate invocations' "$(cat /tmp/wiki-scaffold-combo.out)"

printf 'wiki-context-scaffold smoke test complete\n'
