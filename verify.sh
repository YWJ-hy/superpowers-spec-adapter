#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
TARGET_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" "$TARGET_INPUT")"
TARGET_DIR="$(python3 - <<'PY' "$TARGET_JSON"
import json, sys
print(json.loads(sys.argv[1])['target'])
PY
)"
HOOK_PATCHER="$SCRIPT_DIR/lib/hook_patch.py"
NATIVE_SKILL_PATCHER="$SCRIPT_DIR/lib/native_skill_patch.py"
MARKER="$(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import generated_marker
print(generated_marker(Path(sys.argv[1])))
PY
)"

check_file() {
  local relative="$1"
  local target="$TARGET_DIR/$relative"
  if [[ ! -f "$target" ]]; then
    printf 'Missing file: %s\n' "$target" >&2
    exit 1
  fi
  if ! grep -Fq "$MARKER" "$target"; then
    printf 'Missing adapter marker: %s\n' "$target" >&2
    exit 1
  fi
  case "$relative" in
    commands/*.md|skills/*/SKILL.md)
      if grep -Fq 'python3 superpowers/scripts/' "$target"; then
        printf 'Invalid project-relative script path in installed file: %s\n' "$target" >&2
        exit 1
      fi
      if grep -Fq '__SUPERPOWER_ADAPTER_PLUGIN_ROOT__' "$target"; then
        printf 'Unresolved adapter plugin root placeholder in installed file: %s\n' "$target" >&2
        exit 1
      fi
      ;;
  esac
  printf 'OK %s\n' "$relative"
}

check_optional_integration_overlays() {
  local lanhu_agent="$TARGET_DIR/agents/lanhu-requirements-analyst.md"
  local lanhu_command="$TARGET_DIR/commands/lanhu-requirements.md"
  local graphify_agent="$TARGET_DIR/agents/graphify-researcher.md"
  if grep -Fq '### 不包含' "$lanhu_agent"; then
    printf 'Lanhu analyst should not render a standard 不包含 subsection\n' >&2
    exit 1
  fi
  if grep -Fq 'included and excluded scope' "$lanhu_command"; then
    printf 'Lanhu command still implies a fixed excluded-scope PRD section\n' >&2
    exit 1
  fi
  for required in \
    'test cases' \
    'acceptance criteria' \
    'frontend components' \
    'backend API' \
    'database' \
    'file impact' \
    '.superpowers/wiki/' \
    'graphify' \
    'hasDesignContent' \
    'designArtifacts' \
    '.lanhu/MM-DD-需求命名.md' \
    '.lanhu/MM-DD-需求命名/prd.md' \
    '.lanhu/MM-DD-需求命名/design/' \
    'explicitPageId' \
    'pageid-tree-gated' \
    'childPagePolicy' \
    'lanhu_get_pages' \
    'lanhu_get_ai_analyze_page_result' \
    'page_names: all' \
    '__AI_INSTRUCTION__' \
    'ai_suggestion'
  do
    if ! grep -Fq "$required" "$lanhu_agent"; then
      printf 'Missing Lanhu analyst guardrail: %s\n' "$required" >&2
      exit 1
    fi
  done
  for required in \
    '.lanhu/MM-DD-需求命名.md' \
    '.lanhu/MM-DD-需求命名/prd.md' \
    '.lanhu/MM-DD-需求命名/design/' \
    'hasDesignContent' \
    'designArtifacts' \
    'Do not require Lanhu MCP to be installed' \
    'Always ask the user to review and confirm' \
    'Do not write `.superpowers/wiki/`' \
    'Do not invoke graphify' \
    'explicitPageId' \
    'pageid-tree-gated' \
    'childPagePolicy' \
    'page_names: all'
  do
    if ! grep -Fq "$required" "$lanhu_command"; then
      printf 'Missing Lanhu command requirement: %s\n' "$required" >&2
      exit 1
    fi
  done
  for required in \
    'Graphify is optional' \
    'must never block Superpowers' \
    'mustVerifyInSource: true' \
    'must not:' \
    'Run `graphify`' \
    'Decide final implementation files'
  do
    if ! grep -Fq "$required" "$graphify_agent"; then
      printf 'Missing graphify researcher guardrail: %s\n' "$required" >&2
      exit 1
    fi
  done
  printf 'Optional integration overlay checks OK\n'
}

check_native_skill_residuals() {
  if grep -Eq 'spec-researcher|update-spec|init-spec|import-spec|spec-progressive-disclosure|Referenced Project Specs|\.superpowers/spec' "$TARGET_DIR/skills/brainstorming/SKILL.md" "$TARGET_DIR/skills/systematic-debugging/SKILL.md" "$TARGET_DIR/skills/writing-plans/SKILL.md" "$TARGET_DIR/skills/executing-plans/SKILL.md" "$TARGET_DIR/skills/subagent-driven-development/SKILL.md"; then
    printf 'Deprecated adapter spec terminology remains in native skill patches\n' >&2
    exit 1
  fi
  if grep -Fq 'wiki-progressive-disclosure' "$TARGET_DIR/skills/brainstorming/SKILL.md"; then
    printf 'Invalid default wiki-progressive-disclosure dependency in brainstorming patch\n' >&2
    exit 1
  fi
  if grep -Fq 'wiki-progressive-disclosure' "$TARGET_DIR/skills/writing-plans/SKILL.md"; then
    printf 'Invalid default wiki-progressive-disclosure dependency in writing-plans patch\n' >&2
    exit 1
  fi
  if grep -Fq 'workflow-gate.py" implement' "$TARGET_DIR/skills/executing-plans/SKILL.md"; then
    printf 'Deprecated workflow-gate implement path remains in executing-plans patch\n' >&2
    exit 1
  fi
  if grep -Fq 'plan-context.py" render --phase implement' "$TARGET_DIR/skills/subagent-driven-development/SKILL.md"; then
    printf 'Deprecated plan-context render path remains in subagent-driven-development patch\n' >&2
    exit 1
  fi
  if grep -Eq 'must install (lanhu-mcp|graphify)|requires (lanhu-mcp|graphify)|required dependency.*(lanhu-mcp|graphify)' "$TARGET_DIR/skills/brainstorming/SKILL.md" "$TARGET_DIR/skills/writing-plans/SKILL.md" "$TARGET_DIR/skills/systematic-debugging/SKILL.md"; then
    printf 'Invalid required external dependency language in native skill patches\n' >&2
    exit 1
  fi
  local brainstorming_skill="$TARGET_DIR/skills/brainstorming/SKILL.md"
  for required in \
    'lanhu-requirements-analyst' \
    '.lanhu/MM-DD-需求命名.md' \
    '.lanhu/MM-DD-需求命名/prd.md' \
    '.lanhu/MM-DD-需求命名/design/' \
    'Lanhu MCP is optional' \
    'do not block brainstorming' \
    'test cases' \
    'acceptance criteria' \
    'frontend components' \
    'backend APIs' \
    'database impacts' \
    'file impacts' \
    'explicitPageId' \
    'pageid-tree-gated' \
    'childPagePolicy' \
    'lanhu_get_pages' \
    'lanhu_get_ai_analyze_page_result' \
    'page_names: all' \
    '__AI_INSTRUCTION__' \
    'ai_suggestion'
  do
    if ! grep -Fq "$required" "$brainstorming_skill"; then
      printf 'Missing optional Lanhu brainstorming requirement: %s\n' "$required" >&2
      exit 1
    fi
  done
  local writing_skill="$TARGET_DIR/skills/writing-plans/SKILL.md"
  for required in \
    'graphify-researcher' \
    'Graphify is optional' \
    'candidate hints' \
    'Every useful hint must be verified against current source' \
    'not graphify alone'
  do
    if ! grep -Fq "$required" "$writing_skill"; then
      printf 'Missing optional graphify planning requirement: %s\n' "$required" >&2
      exit 1
    fi
  done
  local systematic_skill="$TARGET_DIR/skills/systematic-debugging/SKILL.md"
  for required in \
    'wiki-researcher' \
    'phase: debug' \
    'maxWikiPages: 2' \
    'Do not call `wiki-researcher` at the start of debugging' \
    'graphify-researcher' \
    'Do not call `graphify-researcher` at the start of debugging' \
    'Phase 1 evidence has narrowed' \
    'candidate-hint research' \
    'not root-cause evidence' \
    'continue systematic debugging' \
    'do not write `.wiki-context.md`' \
    'break-loop'
  do
    if ! grep -Fq "$required" "$systematic_skill"; then
      printf 'Missing systematic-debugging low-noise wiki requirement: %s\n' "$required" >&2
      exit 1
    fi
  done
  if grep -Fq 'planPath:' "$systematic_skill"; then
    printf 'Invalid planning path input in systematic-debugging patch\n' >&2
    exit 1
  fi
  if grep -Fq 'docs/superpowers/plans/<plan-stem>.wiki-context.md' "$systematic_skill"; then
    printf 'Invalid planning wiki context sidecar generation in systematic-debugging patch\n' >&2
    exit 1
  fi
  local worktree_skill="$TARGET_DIR/skills/using-git-worktrees/SKILL.md"
  local finishing_skill="$TARGET_DIR/skills/finishing-a-development-branch/SKILL.md"
  for required in 'worktree-origin.json' 'originalBranch' 'originalWorktree' 'originalHead' 'rev-parse --absolute-git-dir'; do
    if ! grep -Fq "$required" "$worktree_skill"; then
      printf 'Missing worktree origin metadata requirement in using-git-worktrees patch: %s\n' "$required" >&2
      exit 1
    fi
  done
  for required in 'worktree-origin.json' 'Merge back to original branch' 'originalWorktree'; do
    if ! grep -Fq "$required" "$finishing_skill"; then
      printf 'Missing original branch finishing requirement in finishing-a-development-branch patch: %s\n' "$required" >&2
      exit 1
    fi
  done
  printf 'Native skill residual checks OK\n'
}

while IFS= read -r relative; do
  relative="${relative%$'\r'}"
  [[ -z "$relative" ]] && continue
  check_file "$relative"
done < <(python3 - <<'PY' "$SCRIPT_DIR"
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'lib'))
from adapter_manifest import installed_paths
for item in installed_paths(Path(sys.argv[1])):
    print(item)
PY
)
python3 "$HOOK_PATCHER" verify "$TARGET_DIR"
python3 "$NATIVE_SKILL_PATCHER" verify "$TARGET_DIR"
check_optional_integration_overlays
check_native_skill_residuals

printf 'superpower-adapter verify complete\n'
