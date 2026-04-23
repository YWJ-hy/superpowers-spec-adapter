#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"
PLAN_PATH="docs/superpowers/plans/plan-context-regression.md"
PLAN_ABS="${PROJECT_ROOT}/${PLAN_PATH}"
CONTEXT_DIR="${PROJECT_ROOT}/docs/superpowers/plans/plan-context-regression.context"
CURRENT_PLAN="${PROJECT_ROOT}/.superpowers/current-plan"
SPEC_PATH="${PROJECT_ROOT}/.superpowers/spec/backend/error-handling.md"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans"
printf '# Plan Context Regression Test\n\n- [ ] Verify dedupe, render budget, and workflow gate\n' > "${PLAN_ABS}"
rm -rf "${CONTEXT_DIR}"
rm -f "${CURRENT_PLAN}"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
  rm -f "${PLAN_ABS}"
  rm -f "${CURRENT_PLAN}"
}
trap cleanup EXIT

python3 "${TARGET_INPUT}/scripts/plan-context.py" init "${PLAN_ABS}" --set-current
python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_ABS}" --spec "${SPEC_PATH}" --reason "Initial regression context" --mode summary
python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_ABS}" --spec "${SPEC_PATH}" --reason "Upgraded regression context" --mode full

python3 - <<'PY' "${CONTEXT_DIR}/plan.jsonl"
import json, sys
path = sys.argv[1]
rows = [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
if len(rows) != 1:
    raise SystemExit(f'Expected 1 deduped row, got {len(rows)}')
row = rows[0]
if row.get('mode') != 'full':
    raise SystemExit(f"Expected merged mode full, got {row.get('mode')}")
if row.get('reason') != 'Upgraded regression context':
    raise SystemExit(f"Expected merged reason, got {row.get('reason')}")
PY

python3 "${TARGET_INPUT}/scripts/workflow-gate.py" implement --plan "${PLAN_ABS}" > /dev/null

render_output="$(python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement --plan "${PLAN_ABS}" --max-full 0)"
case "${render_output}" in
  *"Downgraded to summary"*) : ;;
  *) printf 'Expected render output to mention downgrade to summary\n' >&2; exit 1 ;;
esac

render_json="$(python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement --plan "${PLAN_ABS}" --json --max-full 0)"
python3 - <<'PY' "${render_json}"
import json, sys
payload = json.loads(sys.argv[1])
records = payload.get('records', [])
if len(records) != 1:
    raise SystemExit(f'Expected 1 record in JSON render, got {len(records)}')
record = records[0]
if record.get('mode') != 'summary':
    raise SystemExit(f"Expected downgraded summary mode, got {record.get('mode')}")
if 'summary' not in record:
    raise SystemExit('Expected summary field in JSON render output')
budget = payload.get('budget', {})
if budget.get('usedFull') != 0:
    raise SystemExit(f"Expected usedFull 0 after downgrade, got {budget.get('usedFull')}")
if not budget.get('downgraded'):
    raise SystemExit('Expected downgraded list to be non-empty')
PY

completion_output="$(python3 "${TARGET_INPUT}/scripts/workflow-gate.py" completion --plan "${PLAN_ABS}" --summary "normalize backend error contract" || true)"
case "${completion_output}" in
  *"Status: WARN"* ) : ;;
  *) printf 'Expected completion gate to warn about durable knowledge\n' >&2; exit 1 ;;
esac

printf 'plan-context regression test complete\n'
