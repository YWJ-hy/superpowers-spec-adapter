#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"

LANHU_FRONTEND_AGENT="${TARGET_INPUT}/agents/lanhu-frontend-requirements-analyst.md"
LANHU_BACKEND_AGENT="${TARGET_INPUT}/agents/lanhu-backend-requirements-analyst.md"
LANHU_COMMAND="${TARGET_INPUT}/commands/lanhu-requirements.md"
BRAINSTORMING_SKILL="${TARGET_INPUT}/skills/brainstorming/SKILL.md"
USING_SUPERPOWERS_SKILL="${TARGET_INPUT}/skills/using-superpowers/SKILL.md"

for file in "$LANHU_FRONTEND_AGENT" "$LANHU_BACKEND_AGENT" "$LANHU_COMMAND" "$BRAINSTORMING_SKILL" "$USING_SUPERPOWERS_SKILL"; do
  if [[ ! -f "$file" ]]; then
    printf 'Expected installed Lanhu confirmation gate target: %s\n' "$file" >&2
    exit 1
  fi
done

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain Lanhu confirmation gate text: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

for agent in "$LANHU_FRONTEND_AGENT" "$LANHU_BACKEND_AGENT"; do
  for required in \
    'status: need_confirmation' \
    'confirmationGate' \
    'blockingQuestions' \
    'blockingQuestionCount' \
    'resolutionMode' \
    'resolve_confirmation' \
    'confirmationAnswers' \
    'Blocking confirmation classification' \
    'do not continue to Superpowers brainstorming' \
    'raw Lanhu tool-result text' \
    'full PRD markdown' \
    '是否阻塞后续 Superpowers 流程' \
    '阻塞原因'
  do
    require_in_file "$agent" "$required"
  done
done

for required in \
  'status: need_confirmation' \
  'confirmationGate' \
  'blockingQuestions' \
  'blockingQuestionCount' \
  'resolutionMode: resolve_confirmation' \
  'confirmationAnswers' \
  'compact confirmation gate' \
  'Superpowers brainstorming will not start until these are resolved' \
  'confirmationGate.status: clear' \
  'main session must not override `confirmationGate` directly'
do
  require_in_file "$LANHU_COMMAND" "$required"
done

for required in \
  'status: need_confirmation' \
  'confirmationGate' \
  'blockingQuestions' \
  'resolutionMode: resolve_confirmation' \
  'previousPackageDir' \
  'confirmationAnswers' \
  'Do not let the main session reclassify or bypass `confirmationGate`' \
  'status: ok' \
  'confirmationGate.status: clear'
do
  require_in_file "$BRAINSTORMING_SKILL" "$required"
done

for required in \
  'resolve analyst-classified blocking requirement questions' \
  'cleared confirmation gate'
do
  require_in_file "$USING_SUPERPOWERS_SKILL" "$required"
done

printf 'Lanhu confirmation gate smoke OK\n'
