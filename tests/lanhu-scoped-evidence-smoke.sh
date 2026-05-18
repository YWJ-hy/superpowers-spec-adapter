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

for file in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT" "$LANHU_COMMAND"; do
  if [[ ! -f "$file" ]]; then
    printf 'Expected installed Lanhu scoped evidence target: %s\n' "$file" >&2
    exit 1
  fi
done

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain Lanhu scoped evidence text: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

for agent in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT"; do
  for required in \
    'Allowed Lanhu MCP tools' \
    'lanhu_resolve_invite_link' \
    'lanhu_get_prd_page_scope' \
    'lanhu_get_prd_scoped_evidence' \
    'scope_policy: pageid_children_only' \
    'include_child_pages' \
    'confirmed_child_page_ids' \
    'output_mode: evidence_only' \
    'scopeValidation' \
    'returnedOutOfScopePages' \
    'scopedEvidenceContract' \
    'arbitraryLanhuToolsUsed: false' \
    'deliveryBoundaryPlan' \
    'possibleOverMerge' \
    'possibleOverSplit' \
    'confirmationGate.phase' \
    'targetPage' \
    'only mandatory scope' \
    'do not silently fall back to `lanhu_get_pages`' \
    'Do not call any other Lanhu MCP tool'
  do
    require_in_file "$agent" "$required"
  done
done

for required in \
  'allowedLanhuMcpTools' \
  'lanhu_resolve_invite_link' \
  'lanhu_get_prd_page_scope' \
  'lanhu_get_prd_scoped_evidence' \
  'scopePolicy: pageid_children_only' \
  'scope_policy: pageid_children_only' \
  'include_child_pages' \
  'confirmed_child_page_ids' \
  'output_mode: evidence_only' \
  'scopeValidation.returnedOutOfScopePages == 0' \
  'scopedEvidenceContract.arbitraryLanhuToolsUsed == false' \
  'deliveryBoundaryPlan' \
  'confirmationGate.phase: delivery_boundary' \
  'Do not silently fall back to old broad Lanhu MCP tools'
do
  require_in_file "$LANHU_COMMAND" "$required"
done

printf 'Lanhu scoped evidence smoke OK\n'
