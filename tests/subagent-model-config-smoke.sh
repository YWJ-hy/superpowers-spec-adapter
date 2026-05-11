#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"
CONFIG_FILE="$ROOT/adapter.config.json"
BACKUP_FILE=""
HAD_CONFIG=0

if [[ -f "$CONFIG_FILE" ]]; then
  HAD_CONFIG=1
  BACKUP_FILE="$(mktemp)"
  cp "$CONFIG_FILE" "$BACKUP_FILE"
fi

cleanup() {
  if [[ "$HAD_CONFIG" == "1" ]]; then
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    rm -f "$BACKUP_FILE"
  else
    rm -f "$CONFIG_FILE"
  fi
  "$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
}
trap cleanup EXIT

write_config() {
  cat >"$CONFIG_FILE"
}

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

forbid_in_file() {
  local file="$1"
  local text="$2"
  if grep -Fq "$text" "$file"; then
    printf 'Expected %s to omit: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

assert_agent_model() {
  local agent="$1"
  local model="$2"
  require_in_file "$TARGET_INPUT/agents/${agent}.md" "model: ${model}"
}

UPSTREAM_FILES=(
  "$TARGET_INPUT/skills/brainstorming/spec-document-reviewer-prompt.md"
  "$TARGET_INPUT/skills/writing-plans/plan-document-reviewer-prompt.md"
  "$TARGET_INPUT/skills/requesting-code-review/code-reviewer.md"
  "$TARGET_INPUT/skills/subagent-driven-development/implementer-prompt.md"
  "$TARGET_INPUT/skills/subagent-driven-development/spec-reviewer-prompt.md"
  "$TARGET_INPUT/skills/subagent-driven-development/code-quality-reviewer-prompt.md"
  "$TARGET_INPUT/skills/subagent-driven-development/SKILL.md"
)

write_config <<'JSON'
{}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
assert_agent_model wiki-researcher inherit
assert_agent_model graphify-researcher inherit
assert_agent_model lanhu-frontend-requirements-analyst inherit
assert_agent_model lanhu-backend-requirements-analyst inherit
for file in "${UPSTREAM_FILES[@]}"; do
  forbid_in_file "$file" 'superpower-adapter:subagent-model'
done

write_config <<'JSON'
{
  "subagentModels": {
    "agents": {
      "wiki-researcher": "deepseek-v4-pro[1m]",
      "graphify-researcher": "haiku",
      "lanhu-frontend-requirements-analyst": "opus",
      "lanhu-backend-requirements-analyst": "sonnet"
    },
    "upstreamPromptTemplates": {
      "spec-document-reviewer": "haiku",
      "plan-document-reviewer": "sonnet",
      "code-reviewer": "haiku",
      "final-code-reviewer": "opus",
      "implementer": "sonnet",
      "spec-compliance-reviewer": "haiku",
      "code-quality-reviewer": "sonnet"
    }
  }
}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
assert_agent_model wiki-researcher 'deepseek-v4-pro[1m]'
assert_agent_model graphify-researcher haiku
assert_agent_model lanhu-frontend-requirements-analyst opus
assert_agent_model lanhu-backend-requirements-analyst sonnet
require_in_file "$TARGET_INPUT/skills/brainstorming/spec-document-reviewer-prompt.md" 'superpower-adapter:subagent-model:spec-document-reviewer'
require_in_file "$TARGET_INPUT/skills/brainstorming/spec-document-reviewer-prompt.md" 'model: haiku'
require_in_file "$TARGET_INPUT/skills/writing-plans/plan-document-reviewer-prompt.md" 'model: sonnet'
require_in_file "$TARGET_INPUT/skills/requesting-code-review/code-reviewer.md" 'superpower-adapter:subagent-model:code-reviewer'
require_in_file "$TARGET_INPUT/skills/requesting-code-review/code-reviewer.md" 'model: haiku'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/implementer-prompt.md" 'model: sonnet'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/spec-reviewer-prompt.md" 'model: haiku'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/code-quality-reviewer-prompt.md" 'model: sonnet'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/SKILL.md" 'superpower-adapter:subagent-model:final-code-reviewer'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/SKILL.md" 'model: opus'

write_config <<'JSON'
{
  "subagentModels": {
    "upstreamPromptTemplates": {
      "code-reviewer": "haiku"
    }
  }
}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
require_in_file "$TARGET_INPUT/skills/requesting-code-review/code-reviewer.md" 'superpower-adapter:subagent-model:code-reviewer'
require_in_file "$TARGET_INPUT/skills/requesting-code-review/code-reviewer.md" 'model: haiku'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/SKILL.md" 'superpower-adapter:subagent-model:final-code-reviewer'
require_in_file "$TARGET_INPUT/skills/subagent-driven-development/SKILL.md" 'model: haiku'

write_config <<'JSON'
{}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
assert_agent_model wiki-researcher inherit
assert_agent_model graphify-researcher inherit
assert_agent_model lanhu-frontend-requirements-analyst inherit
assert_agent_model lanhu-backend-requirements-analyst inherit
for file in "${UPSTREAM_FILES[@]}"; do
  forbid_in_file "$file" 'superpower-adapter:subagent-model'
done

write_config <<'JSON'
{
  "subagentModels": {
    "agents": {
      "unknown-agent": "sonnet"
    }
  }
}
JSON
if "$ROOT/install.sh" "$TARGET_INPUT" >/tmp/subagent-model-invalid.out 2>&1; then
  printf 'Expected invalid subagent id to fail install\n' >&2
  exit 1
fi
require_in_file /tmp/subagent-model-invalid.out 'unknown subagentModels.agents key'

write_config <<'JSON'
{
  "subagentModels": {
    "agents": {
      "wiki-researcher": "bad model"
    }
  }
}
JSON
if "$ROOT/install.sh" "$TARGET_INPUT" >/tmp/subagent-model-invalid-model.out 2>&1; then
  printf 'Expected invalid model string to fail install\n' >&2
  exit 1
fi
require_in_file /tmp/subagent-model-invalid-model.out 'contains unsupported characters'

TEMP_TARGET="$(mktemp -d)"
cp -R "$TARGET_INPUT"/. "$TEMP_TARGET"/
write_config <<'JSON'
{
  "subagentModels": {
    "upstreamPromptTemplates": {
      "implementer": "sonnet",
      "code-reviewer": "opus",
      "final-code-reviewer": "haiku"
    }
  }
}
JSON
python3 - "$TEMP_TARGET" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for relative in [
    'skills/subagent-driven-development/implementer-prompt.md',
    'skills/requesting-code-review/code-reviewer.md',
]:
    path = root / relative
    text = path.read_text(encoding='utf-8')
    text = text.replace('Task tool', 'removed-task-tool', 1)
    path.write_text(text, encoding='utf-8')
path = root / 'skills/subagent-driven-development/SKILL.md'
text = path.read_text(encoding='utf-8')
text = text.replace('Dispatch final code reviewer subagent for entire implementation', 'removed final reviewer dispatch')
path.write_text(text, encoding='utf-8')
PY
if "$ROOT/install.sh" "$TEMP_TARGET" >/tmp/subagent-model-compat.out 2>&1; then
  printf 'Expected broken configured upstream templates to fail install\n' >&2
  exit 1
fi
require_in_file /tmp/subagent-model-compat.out 'implementer model=sonnet'
require_in_file /tmp/subagent-model-compat.out 'code-reviewer model=opus'
require_in_file /tmp/subagent-model-compat.out 'final-code-reviewer model=haiku'

write_config <<'JSON'
{}
JSON
"$ROOT/install.sh" "$TEMP_TARGET" >/dev/null
rm -rf "$TEMP_TARGET"
rm -f /tmp/subagent-model-invalid.out /tmp/subagent-model-invalid-model.out /tmp/subagent-model-compat.out

printf 'subagent model config smoke OK\n'
