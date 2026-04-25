#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"
PROJECT_ROOT="${2:-${ROOT}/..}"
PLAN_PATH="docs/superpowers/plans/plan-context-regression.md"
PLAN_ABS="${PROJECT_ROOT}/${PLAN_PATH}"
CONTEXT_DIR="${PROJECT_ROOT}/docs/superpowers/plans/plan-context-regression.context"
CURRENT_PLAN="${PROJECT_ROOT}/.superpowers/current-plan"
SPEC_ROOT="${PROJECT_ROOT}/.superpowers/spec"
SPEC_PATH="${SPEC_ROOT}/quality/error-rules.md"
UNINDEXED_SPEC="${SPEC_ROOT}/quality/unindexed.md"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans" "${SPEC_ROOT}/quality"
cat > "${SPEC_ROOT}/index.md" <<'EOF'
# Project Specs

<!-- superpower-adapter:auto:start -->
- `quality/error-rules.md`
<!-- superpower-adapter:auto:end -->
EOF
printf '# Error Rules\n\nStable error handling behavior.\n' > "${SPEC_PATH}"
printf '# Unindexed\n\nNot selectable.\n' > "${UNINDEXED_SPEC}"
printf '# Plan Context Regression Test\n\n- [ ] Verify dedupe, render budget, and workflow gate\n' > "${PLAN_ABS}"
rm -rf "${CONTEXT_DIR}"
rm -f "${CURRENT_PLAN}"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
  rm -f "${PLAN_ABS}"
  rm -f "${CURRENT_PLAN}"
}
trap cleanup EXIT

(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/workflow-gate.py" planning --plan "${PLAN_PATH}" --hint "error handling" > /dev/null)
python3 - <<'PY' "${CONTEXT_DIR}/plan.jsonl"
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8') if line.strip()]
if not rows:
    raise SystemExit('Expected planning gate to auto-select context records')
if any(row.get('selectedBy') != 'workflow-gate' for row in rows):
    raise SystemExit('Expected planning gate records to use selectedBy=workflow-gate')
PY
if (cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_PATH}" --spec "${UNINDEXED_SPEC}" --reason "Should fail" --mode summary 2>/dev/null); then
  printf 'Expected unindexed spec add to fail\n' >&2
  exit 1
fi
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_PATH}" --spec "${SPEC_PATH}" --reason "Initial regression context" --mode summary)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_PATH}" --spec "${SPEC_PATH}" --reason "Upgraded regression context" --mode full)

python3 - <<'PY' "${CONTEXT_DIR}/plan.jsonl"
import json, sys
path = sys.argv[1]
rows = [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
matching = [row for row in rows if row.get('path') == '.superpowers/spec/quality/error-rules.md']
if len(matching) != 1:
    raise SystemExit(f'Expected 1 deduped error-rules row, got {len(matching)} from {rows}')
row = matching[0]
if row.get('mode') != 'full':
    raise SystemExit(f"Expected merged mode full, got {row.get('mode')}")
if row.get('reason') != 'Upgraded regression context':
    raise SystemExit(f"Expected merged reason, got {row.get('reason')}")
PY

(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/workflow-gate.py" implement --plan "${PLAN_PATH}" > /dev/null)

render_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement --plan "${PLAN_PATH}" --max-full 0)"
case "${render_output}" in
  *"Downgraded to summary"*) : ;;
  *) printf 'Expected render output to mention downgrade to summary\n' >&2; exit 1 ;;
esac

render_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement --plan "${PLAN_PATH}" --json --max-full 0)"
python3 - <<'PY' "${render_json}"
import json, sys
payload = json.loads(sys.argv[1])
records = payload.get('records', [])
matching = [record for record in records if record.get('path') == '.superpowers/spec/quality/error-rules.md']
if len(matching) != 1:
    raise SystemExit(f'Expected error-rules record in JSON render, got {records}')
record = matching[0]
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

completion_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/workflow-gate.py" completion --plan "${PLAN_PATH}" --summary "normalize api error contract" || true)"
case "${completion_output}" in
  *"Status: WARN"* ) : ;;
  *) printf 'Expected completion gate to warn about durable knowledge\n' >&2; exit 1 ;;
esac

printf 'plan-context regression test complete\n'
