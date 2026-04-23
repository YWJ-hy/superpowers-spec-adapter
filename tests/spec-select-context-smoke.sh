#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"
PLAN_PATH="docs/superpowers/plans/spec-select-context-smoke.md"
PLAN_ABS="${PROJECT_ROOT}/${PLAN_PATH}"
CONTEXT_DIR="${PROJECT_ROOT}/docs/superpowers/plans/spec-select-context-smoke.context"
CURRENT_PLAN="${PROJECT_ROOT}/.superpowers/current-plan"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans"
printf '# Spec Select Context Smoke Test\n\n- [ ] Verify selector output and sidecar writes\n' > "${PLAN_ABS}"
rm -rf "${CONTEXT_DIR}"
rm -f "${CURRENT_PLAN}"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
  rm -f "${PLAN_ABS}"
  rm -f "${CURRENT_PLAN}"
}
trap cleanup EXIT

python3 "${TARGET_INPUT}/scripts/plan-context.py" init "${PLAN_ABS}" --set-current > /dev/null

selector_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 3)"
case "${selector_output}" in
  *".superpowers/spec/backend/error-handling.md"* ) : ;;
  *) printf 'Expected selector output to include backend/error-handling.md\n' >&2; exit 1 ;;
esac

selector_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 3 --json)"
python3 - <<'PY' "${selector_json}"
import json, sys
payload = json.loads(sys.argv[1])
candidates = payload.get('candidates', [])
if not candidates:
    raise SystemExit('Expected selector JSON to include candidates')
paths = [item.get('path') for item in candidates]
if '.superpowers/spec/backend/error-handling.md' not in paths:
    raise SystemExit(f'Expected error-handling.md in candidates, got {paths}')
PY

selector_write_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 2 --write-sidecar --plan "${PLAN_PATH}" --json)"
python3 - <<'PY' "${selector_write_json}" "${CONTEXT_DIR}/implement.jsonl"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get('wroteCount', 0) <= 0:
    raise SystemExit(f"Expected wroteCount > 0, got {payload.get('wroteCount')}")
rows = [json.loads(line) for line in open(sys.argv[2], encoding='utf-8') if line.strip()]
if not rows:
    raise SystemExit('Expected implement.jsonl to contain selector-written rows')
paths = [row.get('path') for row in rows]
if '.superpowers/spec/backend/error-handling.md' not in paths:
    raise SystemExit(f'Expected error-handling.md in implement.jsonl, got {paths}')
if any(row.get('selectedBy') != 'selector' for row in rows):
    raise SystemExit('Expected selector-written rows to use selectedBy=selector')
PY

printf 'spec-select-context smoke test complete\n'
