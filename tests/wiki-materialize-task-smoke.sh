#!/usr/bin/env bash
set -euo pipefail

# Exercises wiki_materialize_task.py: the single fixed fetcher that materializes a task's
# hard-constraint full-section rereads from BOTH local wiki (filesystem) and github_mcp shared
# wiki (via a faked read-sections CLI), plus its fail-closed drift handling. The MCP CLI itself
# is covered by mcp/shared-wiki vitest; here we stub it to keep the smoke node-free.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
SCRIPT="${TARGET_INPUT}/scripts/wiki_materialize_task.py"

if [[ ! -f "$SCRIPT" ]]; then
  printf 'Missing materialize orchestrator: %s\n' "$SCRIPT" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PROJECT="$TMP/project"
WIKI="$PROJECT/.superpowers/wiki"
mkdir -p "$WIKI"

REPO_URL="https://github.com/YWJ-hy/shared-wiki.git"
REVISION="47a929320ac726eac7c10a56288035dcca382cd2"

cat > "$WIKI/directory-structure.md" <<'MD'
# Directory Structure

<!-- wiki-section:service-layer -->
## 服务层结构 (service2/)

消费端必须从 adapter.ts 导入，禁止直接引用 index.ts 中的原始请求函数。
<!-- /wiki-section:service-layer -->
MD

cat > "$WIKI/directory-structure.index.md" <<'MD'
# Directory Structure

> Project layout and service-layer boundaries.

| section | 描述 | 约束强度 |
|---|---|---|
| service-layer | 服务层结构 | hard |
MD

CONTEXT="$TMP/plan.wiki-context.json"
cat > "$CONTEXT" <<JSON
{
  "schemaVersion": 4,
  "kind": "superpower-adapter.wiki-context",
  "generatedBy": "superpower-adapter",
  "sharedWiki": {"source": "github_mcp", "repoUrl": "${REPO_URL}", "revision": {"commitSha": "${REVISION}"}},
  "taskRouting": {"status": "confirmed", "planTaskFormat": "superpower-adapter-plan-task-heading-v1", "fingerprintAlgorithm": "sha256:superpower-adapter-task-text-v1", "selectedSectionsFrozen": true, "refreshPolicy": "refresh-taskWikiRefs-and-fingerprints-only"},
  "wikiPages": [
    {
      "root": "project", "source": "local", "displayPath": "directory-structure.md", "localPath": "directory-structure.md", "wikiPath": "directory-structure.md",
      "documentContext": {"title": "Directory Structure", "overview": "Project layout.", "contextSource": "directory-structure.index.md"},
      "sections": [
        {"sectionId": "service-layer", "hardConstraint": true, "relevance": "direct", "reason": "service boundary", "relevanceTo": "service2 consumers",
         "constraints": {"implementation": ["consume via adapter.ts, never index.ts"]},
         "destination": {"kind": "global", "reason": "global service boundary"},
         "reread": {"root": "project", "source": "local", "localPath": "directory-structure.md", "sectionId": "service-layer", "includeDocumentContext": true}}
      ]
    },
    {
      "root": "shared", "source": "github_mcp", "displayPath": ".shared-superpowers/wiki/frontend/quality.md", "wikiPath": "frontend/quality.md", "revision": {"commitSha": "${REVISION}"},
      "documentContext": {"title": "Quality Guidelines", "overview": "Quality gates."},
      "sections": [
        {"sectionId": "required-quality-patterns", "hardConstraint": true, "relevance": "supporting", "reason": "quality gate", "relevanceTo": "overall quality",
         "constraints": {"implementation": ["pass TS checks"]},
         "destination": {"kind": "task-bound", "reason": "task 1 only", "tasks": ["1"]},
         "reread": {"root": "shared", "source": "github_mcp", "wikiPath": "frontend/quality.md", "sectionId": "required-quality-patterns", "includeDocumentContext": true}}
      ]
    }
  ],
  "taskWikiRefs": [
    {"taskId": "1", "taskTitle": "First task", "taskFingerprint": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"},
    {"taskId": "2", "taskTitle": "Second task", "taskFingerprint": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"}
  ],
  "caveats": []
}
JSON

# Fake shared-wiki read-sections CLI: echoes one ok result per requested section, with repoUrl
# and revision taken from FAKE_REPO_URL / FAKE_REVISION so the smoke can drive drift handling.
FAKE="$TMP/fake_mcp.py"
cat > "$FAKE" <<'PY'
import json, os, sys
req = json.load(sys.stdin)
repo = os.environ.get("FAKE_REPO_URL", "https://github.com/YWJ-hy/shared-wiki.git")
rev = os.environ.get("FAKE_REVISION", "47a929320ac726eac7c10a56288035dcca382cd2")
results = []
for i, s in enumerate(req["sections"]):
    results.append({
        "index": i, "status": "ok", "path": s["path"], "section": s["section"],
        "displayPath": ".shared-superpowers/wiki/" + s["path"],
        "revision": {"commitSha": rev, "shortSha": rev[:12], "ref": "HEAD"},
        "content": "SHARED FULL TEXT: new code must pass TypeScript checks (" + s["section"] + ")",
        "documentContext": {"title": "Quality Guidelines", "overview": "Frontend quality gates.",
                            "contextSource": "frontend/quality.index.md",
                            "displayPath": ".shared-superpowers/wiki/frontend/quality.index.md"},
    })
print(json.dumps({"status": "ok", "repoUrl": repo,
                  "revision": {"commitSha": rev, "shortSha": rev[:12], "ref": "HEAD"},
                  "requestedCount": len(results), "results": results, "errors": []}))
PY

# The orchestrator (Python) spawns this CLI directly, so the path must be resolvable by the
# Python that runs it. Under Git-Bash/MSYS the orchestrator is a native Windows Python that does
# not understand POSIX `/tmp/...`, so convert to a forward-slash Windows path when cygpath exists.
if command -v cygpath >/dev/null 2>&1; then
  FAKE_ARG="$(cygpath -m "$FAKE")"
else
  FAKE_ARG="$FAKE"
fi
FAKE_CMD="python3 $FAKE_ARG"

run_materialize() {
  python3 "$SCRIPT" "$CONTEXT" --project-root "$PROJECT" --strict --execution-ready "$@"
}

# --- Case 1: task 1 = local + github_mcp, both materialized in order ---
OUT1="$TMP/task-1-wiki.md"
printf '## Wiki Constraints\n\n(rendered constraints placeholder)\n' > "$OUT1"
run_materialize --task-id 1 --role implementer --shared-wiki-cmd "$FAKE_CMD" --append-to "$OUT1"

for required in \
  '## Hard Wiki Constraint Rereads' \
  '### Reread: `directory-structure.md` # `service-layer`' \
  '消费端必须从 adapter.ts 导入' \
  '### Reread: `.shared-superpowers/wiki/frontend/quality.md` # `required-quality-patterns`' \
  'SHARED FULL TEXT: new code must pass TypeScript checks' \
  "- Revision: \`${REVISION}\`" \
  '#### Full section text'
do
  if ! grep -Fq -- "$required" "$OUT1"; then
    printf 'Case 1: materialized task-1 file missing: %s\n' "$required" >&2
    exit 1
  fi
done

# Local block must precede the github_mcp block (page order preserved).
if [[ "$(grep -n 'service-layer' "$OUT1" | head -1 | cut -d: -f1)" -ge "$(grep -n 'required-quality-patterns' "$OUT1" | head -1 | cut -d: -f1)" ]]; then
  printf 'Case 1: expected local reread before github_mcp reread\n' >&2
  exit 1
fi

# --- Case 2: rebinding drift (repoUrl mismatch) must fail closed ---
OUT2="$TMP/task-1-drift.md"
: > "$OUT2"
if FAKE_REPO_URL="https://github.com/other/repo.git" run_materialize --task-id 1 --shared-wiki-cmd "$FAKE_CMD" --append-to "$OUT2" 2> "$TMP/err2"; then
  printf 'Case 2: expected rebinding drift to fail\n' >&2
  exit 1
fi
if ! grep -Fq 'rebinding drift' "$TMP/err2"; then
  printf 'Case 2: expected rebinding drift error, got: %s\n' "$(cat "$TMP/err2")" >&2
  exit 1
fi

# --- Case 3: revision drift fails closed by default, proceeds with caveat under override ---
OUT3="$TMP/task-1-revdrift.md"
: > "$OUT3"
if FAKE_REVISION="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" run_materialize --task-id 1 --shared-wiki-cmd "$FAKE_CMD" --append-to "$OUT3" 2> "$TMP/err3"; then
  printf 'Case 3: expected revision drift to fail without override\n' >&2
  exit 1
fi
if ! grep -Fq 'revision drift' "$TMP/err3"; then
  printf 'Case 3: expected revision drift error, got: %s\n' "$(cat "$TMP/err3")" >&2
  exit 1
fi

OUT3B="$TMP/task-1-revdrift-allowed.md"
: > "$OUT3B"
FAKE_REVISION="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" run_materialize --task-id 1 --shared-wiki-cmd "$FAKE_CMD" --allow-revision-drift --append-to "$OUT3B"
if ! grep -Fq 'allow-revision-drift' "$OUT3B"; then
  printf 'Case 3: expected revision-drift caveat under --allow-revision-drift\n' >&2
  exit 1
fi

# --- Case 4: task 2 = local-only, no shared-wiki CLI required ---
OUT4="$TMP/task-2-wiki.md"
: > "$OUT4"
run_materialize --task-id 2 --append-to "$OUT4"
if ! grep -Fq '消费端必须从 adapter.ts 导入' "$OUT4"; then
  printf 'Case 4: expected local reread for task 2\n' >&2
  exit 1
fi
if grep -Fq 'SHARED FULL TEXT' "$OUT4"; then
  printf 'Case 4: task 2 must not include the task-1-bound github_mcp reread\n' >&2
  exit 1
fi

# --- Case 5: unresolved github_mcp CLI fails closed (never silently drops a hard constraint) ---
# Point HOME and USERPROFILE (Windows Path.home() uses USERPROFILE) at an empty dir so registration
# discovery finds nothing; the temp project has no .mcp.json either.
mkdir -p "$TMP/empty-home"
OUT5="$TMP/task-1-nocli.md"
: > "$OUT5"
if HOME="$TMP/empty-home" USERPROFILE="$TMP/empty-home" run_materialize --task-id 1 --append-to "$OUT5" 2> "$TMP/err5"; then
  printf 'Case 5: expected failure when github_mcp CLI is unresolved\n' >&2
  exit 1
fi
if ! grep -Fq 'could not be resolved' "$TMP/err5"; then
  printf 'Case 5: expected unresolved-CLI error, got: %s\n' "$(cat "$TMP/err5")" >&2
  exit 1
fi

printf 'wiki-materialize-task smoke passed\n'
