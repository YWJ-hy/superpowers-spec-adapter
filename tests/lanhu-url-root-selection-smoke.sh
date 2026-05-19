#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"

LANHU_FRONTEND_AGENT="${TARGET_INPUT}/agents/lanhu-frontend-requirements-analyst.md"
LANHU_FRONTEND_HTML_AGENT="${TARGET_INPUT}/agents/lanhu-frontend-html-requirements-analyst.md"
LANHU_BACKEND_AGENT="${TARGET_INPUT}/agents/lanhu-backend-requirements-analyst.md"
LANHU_COMMAND="${TARGET_INPUT}/commands/lanhu-requirements.md"
BRAINSTORMING_SKILL="${TARGET_INPUT}/skills/brainstorming/SKILL.md"

for file in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT" "$LANHU_COMMAND" "$BRAINSTORMING_SKILL"; do
  if [[ ! -f "$file" ]]; then
    printf 'Expected installed Lanhu URL-root selection target: %s\n' "$file" >&2
    exit 1
  fi
done

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain Lanhu URL-root selection text: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

forbid_in_file() {
  local file="$1"
  local text="$2"
  if grep -Fq "$text" "$file"; then
    printf 'Expected %s to omit outdated Lanhu URL-root selection text: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

for orchestrator in "$LANHU_COMMAND" "$BRAINSTORMING_SKILL"; do
  for required in \
    'rootScopeUrl' \
    'rootPageId' \
    'rootScopeTree' \
    'selectedTargetPages' \
    'lightweight URL-rooted page' \
    'main session must not call `lanhu_get_prd_scoped_evidence`' \
    'matchingRestrictedToRootTree' \
    'mainAgentReadFullPageEvidenceBeforeDispatch: false' \
    'childPagePolicy: exclude' \
    'one selected role-and-format analyst per selected page' \
    'include_child_pages: false' \
    'confirmed_child_page_ids: []' \
    'optional cross-package synthesis' \
    'after per-page PRD' \
    'must not replace them'
  do
    require_in_file "$orchestrator" "$required"
  done

  forbid_in_file "$orchestrator" 'target page is always included'
  forbid_in_file "$orchestrator" 'If child pages exist, ask the user whether to include them before reading page content'
  forbid_in_file "$orchestrator" 'use `include_child_pages: true`'
done

for agent in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT"; do
  for required in \
    'rootScopeContext' \
    'selectedFromRootTree' \
    'selectedPage' \
    'selectionTreeBoundary' \
    'matchingRestrictedToRootTree: true' \
    'mainAgentReadFullPageEvidenceBeforeDispatch: false' \
    "selected page's metadata check" \
    'must not choose additional target pages from the original root tree' \
    'childPagePolicy` as `exclude`' \
    'include_child_pages: false' \
    'confirmed_child_page_ids: []' \
    'selected target page only' \
    'separately selected and dispatched as their own analyst calls'
  do
    require_in_file "$agent" "$required"
  done

  forbid_in_file "$agent" 'If `needsChildConfirmation: true` and `childPagePolicy: ask-when-present`'
  forbid_in_file "$agent" 'include_child_pages: true | false'
  forbid_in_file "$agent" 'confirmed_child_page_ids: [] | [user-selected child pageIds]'
done

printf 'Lanhu URL-root selection smoke OK\n'
