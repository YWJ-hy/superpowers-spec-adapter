#!/usr/bin/env bash
set -euo pipefail

# Adapter-native agent model config smoke. The adapter only sets the model on its
# own overlay agents (wiki-researcher + lanhu analysts); it does NOT patch upstream
# Superpowers prompt templates (those carry a native `model:` slot since 6.0.0).

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
  local status=$?
  if [[ "$HAD_CONFIG" == "1" ]]; then
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    rm -f "$BACKUP_FILE"
  else
    rm -f "$CONFIG_FILE"
  fi
  if ! "$ROOT/install.sh" "$TARGET_INPUT" >/dev/null 2>/tmp/subagent-model-restore.out; then
    printf 'Warning: restored adapter.config.json is not installable; leaving target at last test-installed state. See /tmp/subagent-model-restore.out\n' >&2
  fi
  exit "$status"
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

assert_agent_model() {
  local agent="$1"
  local model="$2"
  require_in_file "$TARGET_INPUT/agents/${agent}.md" "model: ${model}"
}

# Empty config -> adapter agents inherit.
write_config <<'JSON'
{}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
assert_agent_model wiki-researcher inherit
assert_agent_model lanhu-frontend-requirements-analyst inherit
assert_agent_model lanhu-backend-requirements-analyst inherit

# Regression guard: the adapter must never reintroduce the removed upstream
# subagent-model patch markers into native Superpowers skills/prompt templates.
if grep -rIlF 'superpower-adapter:subagent-model' "$TARGET_INPUT/skills" >/dev/null 2>&1; then
  printf 'Removed B2 subagent-model markers reappeared in native skills\n' >&2
  exit 1
fi

# Custom agent models apply; a non-standard model string warns but installs.
write_config <<'JSON'
{
  "subagentModels": {
    "agents": {
      "wiki-researcher": "deepseek-v4-pro[1m]",
      "lanhu-frontend-requirements-analyst": "opus",
      "lanhu-backend-requirements-analyst": "sonnet"
    }
  }
}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/tmp/subagent-model-agent-warning.out 2>&1
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
require_in_file /tmp/subagent-model-agent-warning.out 'Warning: adapter.config.json: subagentModels.agents.wiki-researcher uses non-standard model'
require_in_file /tmp/subagent-model-agent-warning.out 'deepseek-v4-pro[1m]'
assert_agent_model wiki-researcher 'deepseek-v4-pro[1m]'
assert_agent_model lanhu-frontend-requirements-analyst opus
assert_agent_model lanhu-backend-requirements-analyst sonnet

# Unknown agent key fails install.
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

# A removed agent id is rejected as an unknown key.
write_config <<'JSON'
{
  "subagentModels": {
    "agents": {
      "lanhu-frontend-html-requirements-analyst": "opus"
    }
  }
}
JSON
if "$ROOT/install.sh" "$TARGET_INPUT" >/tmp/subagent-model-removed-agent.out 2>&1; then
  printf 'Expected removed frontend HTML Lanhu agent config to fail install\n' >&2
  exit 1
fi
require_in_file /tmp/subagent-model-removed-agent.out 'unknown subagentModels.agents key'
require_in_file /tmp/subagent-model-removed-agent.out 'lanhu-frontend-html-requirements-analyst'

# The removed top-level upstreamPromptTemplates key is rejected.
write_config <<'JSON'
{
  "subagentModels": {
    "upstreamPromptTemplates": {
      "implementer": "sonnet"
    }
  }
}
JSON
if "$ROOT/install.sh" "$TARGET_INPUT" >/tmp/subagent-model-removed-upstream.out 2>&1; then
  printf 'Expected removed upstreamPromptTemplates key to fail install\n' >&2
  exit 1
fi
require_in_file /tmp/subagent-model-removed-upstream.out 'unknown subagentModels key'
require_in_file /tmp/subagent-model-removed-upstream.out 'upstreamPromptTemplates'

# An invalid model string fails install.
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

write_config <<'JSON'
{}
JSON
"$ROOT/install.sh" "$TARGET_INPUT" >/dev/null
"$ROOT/verify.sh" "$TARGET_INPUT" >/dev/null
assert_agent_model wiki-researcher inherit

rm -f \
  /tmp/subagent-model-agent-warning.out \
  /tmp/subagent-model-invalid.out \
  /tmp/subagent-model-removed-agent.out \
  /tmp/subagent-model-removed-upstream.out \
  /tmp/subagent-model-invalid-model.out \
  /tmp/subagent-model-restore.out

printf 'subagent model config smoke OK\n'
