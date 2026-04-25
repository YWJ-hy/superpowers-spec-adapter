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
SPEC_ROOT="${PROJECT_ROOT}/.superpowers/spec"
SPEC_PATH="${SPEC_ROOT}/quality/error-rules.md"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans" "${SPEC_ROOT}/quality" "${SPEC_ROOT}/unindexed"
cat > "${SPEC_ROOT}/index.md" <<'EOF'
# Project Specs

<!-- superpower-adapter:auto:start -->
- `quality/error-rules.md`
<!-- superpower-adapter:auto:end -->
EOF
printf '# Error Rules\n\nStable error handling behavior.\n' > "${SPEC_PATH}"
printf '# Hidden Error Rules\n\nShould not be discovered.\n' > "${SPEC_ROOT}/unindexed/hidden-error.md"
printf '# Spec Select Context Smoke Test\n\n- [ ] Verify selector output and sidecar writes\n' > "${PLAN_ABS}"
rm -rf "${CONTEXT_DIR}"
rm -f "${CURRENT_PLAN}"

cleanup() {
  rm -rf "${CONTEXT_DIR}"
  rm -f "${PLAN_ABS}"
  rm -f "${CURRENT_PLAN}"
}
trap cleanup EXIT

(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" init "${PLAN_PATH}" --set-current > /dev/null)

selector_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 3)"
case "${selector_output}" in
  *".superpowers/spec/quality/error-rules.md"* ) : ;;
  *) printf 'Expected selector output to include indexed error rules\n' >&2; exit 1 ;;
esac
case "${selector_output}" in
  *"unindexed/hidden-error.md"*) printf 'Expected selector output to exclude unindexed file\n' >&2; exit 1 ;;
  *) : ;;
esac

selector_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 3 --json)"
python3 - <<'PY' "${selector_json}"
import json, sys
payload = json.loads(sys.argv[1])
paths = [item.get('path') for item in payload.get('candidates', [])]
if '.superpowers/spec/quality/error-rules.md' not in paths:
    raise SystemExit(f'Expected indexed error rules in candidates, got {paths}')
if any('unindexed/hidden-error.md' in path for path in paths):
    raise SystemExit(f'Expected unindexed file to be excluded, got {paths}')
PY

selector_write_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" "error handling" --phase implement --limit 2 --write-sidecar --plan "${PLAN_PATH}" --json)"
python3 - <<'PY' "${selector_write_json}" "${CONTEXT_DIR}/implement.jsonl"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get('wroteCount', 0) <= 0:
    raise SystemExit(f"Expected wroteCount > 0, got {payload.get('wroteCount')}")
rows = [json.loads(line) for line in open(sys.argv[2], encoding='utf-8') if line.strip()]
paths = [row.get('path') for row in rows]
if '.superpowers/spec/quality/error-rules.md' not in paths:
    raise SystemExit(f'Expected indexed error rules in implement.jsonl, got {paths}')
if any(row.get('selectedBy') != 'selector' for row in rows):
    raise SystemExit('Expected selector-written rows to use selectedBy=selector')
PY

printf 'spec-select-context smoke test complete\n'
