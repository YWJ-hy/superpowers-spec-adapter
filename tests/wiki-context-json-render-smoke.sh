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

CONTEXT="$TMP/plan.wiki-context.json"
cat > "$CONTEXT" <<'JSON'
{
  "schemaVersion": 3,
  "kind": "superpower-adapter.wiki-context",
  "generatedBy": "superpower-adapter",
  "planPath": "docs/superpowers/plans/example.md",
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
          "appliesTo": ["Task 1"],
          "readDepth": "full",
          "relevance": "direct",
          "confidence": "high",
          "reason": "Field updates are in scope.",
          "hardConstraint": true,
          "constraints": {
            "implementation": ["Use updateByPath(path, value) for all field updates."],
            "test": ["Verify nested path updates preserve change tracking."],
            "review": ["Reject direct props.model mutation."],
            "general": ["Keep path strings stable across adapter layers."]
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
          ]
        },
        {
          "sectionId": "deep-path",
          "section_name": "deep-path",
          "appliesTo": ["Task 2"],
          "readDepth": "full",
          "relevance": "supporting",
          "confidence": "medium",
          "reason": "Nested paths are nearby but not Task 1.",
          "hardConstraint": false,
          "constraints": {
            "implementation": ["Use dot-notation for nested object paths."],
            "test": [],
            "review": [],
            "general": []
          },
          "sourceAnchors": [
            {"heading": "Deep Path Handling", "excerpt": "Use dot-notation paths like user.address.city."}
          ]
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
          "appliesTo": ["Task 1", "Task 3"],
          "readDepth": "full",
          "relevance": "direct",
          "confidence": "high",
          "reason": "Task touches shared contract shape.",
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
          ]
        }
      ]
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

OUT="$(python3 "$SCRIPT" "$CONTEXT" --task "Task 1" --role implementer --strict)"
assert_contains "implementer render" 'Hook Guidelines' "$OUT"
assert_contains "implementer render" 'Shared Frontend Contracts' "$OUT"
assert_contains "implementer render" 'Use updateByPath(path, value)' "$OUT"
assert_contains "implementer render" 'Verify nested path updates preserve change tracking' "$OUT"
assert_contains "implementer render" 'Keep path strings stable' "$OUT"
assert_contains "implementer render" 'Hard constraint: `true`' "$OUT"
assert_contains "implementer render" 'frontend/contracts.md' "$OUT"
assert_contains "implementer render" 'abcdef1234567890' "$OUT"
assert_not_contains "implementer render" 'Reject direct props.model mutation' "$OUT"
assert_not_contains "implementer render" 'Deep Path Handling' "$OUT"
COUNT="$(python3 - <<'PY' "$OUT"
import sys
print(sys.argv[1].count('Project-private hook rules'))
PY
)"
if [[ "$COUNT" != "1" ]]; then
  printf 'Expected documentContext overview once, got %s\n%s\n' "$COUNT" "$OUT" >&2
  exit 1
fi

REVIEW_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task "Task 1" --role reviewer --strict)"
assert_contains "reviewer render" 'Reject direct props.model mutation' "$REVIEW_OUT"
assert_contains "reviewer render" 'Check that no project-specific environment names leak into shared docs' "$REVIEW_OUT"

EMPTY_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task "Task 99" --role implementer --strict)"
assert_contains "empty render" 'No applicable wiki constraints for this task/role.' "$EMPTY_OUT"

REREAD_OUT="$(python3 "$SCRIPT" "$CONTEXT" --task "Task 1" --role implementer --reread-list --strict)"
assert_contains "reread list" 'path-based-update' "$REREAD_OUT"
assert_contains "reread list" 'contract-review' "$REREAD_OUT"
assert_contains "reread list" 'includeDocumentContext' "$REREAD_OUT"

python3 "$SCRIPT" "$CONTEXT" --validate-only --strict >/dev/null

LEGACY="$TMP/plan.wiki-context.md"
printf '# Legacy\n' > "$LEGACY"
if python3 "$SCRIPT" "$LEGACY" --task "Task 1" --role implementer >/tmp/wiki-context-legacy.out 2>&1; then
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
if python3 "$SCRIPT" "$BAD_CATEGORY" --task "Task 1" --role implementer --strict >/tmp/wiki-context-bad-category.out 2>&1; then
  printf 'Expected unknown category to fail in strict mode\n' >&2
  exit 1
fi
assert_contains "bad category failure" 'unsupported categories: security' "$(cat /tmp/wiki-context-bad-category.out)"

BAD_SECTION_CONTEXT="$TMP/bad-section-context.wiki-context.json"
python3 - <<'PY' "$CONTEXT" "$BAD_SECTION_CONTEXT"
import json, sys
src, dst = sys.argv[1:3]
data = json.load(open(src, encoding='utf-8'))
data['wikiPages'][0]['sections'][0]['documentContext'] = {'title': 'duplicated'}
open(dst, 'w', encoding='utf-8').write(json.dumps(data))
PY
if python3 "$SCRIPT" "$BAD_SECTION_CONTEXT" --task "Task 1" --role implementer --strict >/tmp/wiki-context-bad-section-context.out 2>&1; then
  printf 'Expected section-level documentContext to fail in strict mode\n' >&2
  exit 1
fi
assert_contains "bad section context failure" 'documentContext is not allowed' "$(cat /tmp/wiki-context-bad-section-context.out)"

printf 'wiki-context-json-render smoke test complete\n'
