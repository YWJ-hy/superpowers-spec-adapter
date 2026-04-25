#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"
PLAN_PATH="docs/superpowers/plans/plan-context-smoke.md"
PLAN_ABS="${PROJECT_ROOT}/${PLAN_PATH}"
CONTEXT_DIR="${PROJECT_ROOT}/docs/superpowers/plans/plan-context-smoke.context"
SPEC_ROOT="${PROJECT_ROOT}/.superpowers/spec"
SPEC_PATH="${SPEC_ROOT}/quality/error-rules.md"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans" "${SPEC_ROOT}/quality"
cat > "${SPEC_ROOT}/index.md" <<'EOF'
# Project Specs

<!-- superpower-adapter:auto:start -->
- `quality/error-rules.md`
<!-- superpower-adapter:auto:end -->
EOF
printf '# Error Rules\n\nStable error handling behavior.\n' > "${SPEC_PATH}"
printf '# Plan Context Smoke Test\n\n- [ ] Verify sidecar context lifecycle\n' > "${PLAN_ABS}"
rm -rf "${CONTEXT_DIR}"

(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/workflow-gate.py" planning --plan "${PLAN_PATH}" --hint "error handling")
python3 - <<'PY' "${CONTEXT_DIR}/plan.jsonl"
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8') if line.strip()]
paths = [row.get('path') for row in rows]
if '.superpowers/spec/quality/error-rules.md' not in paths:
    raise SystemExit(f'Expected auto-selected error rules in plan.jsonl, got {paths}')
if any(row.get('selectedBy') != 'workflow-gate' for row in rows):
    raise SystemExit('Expected workflow-gate-written planning records')
PY
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement > /dev/null)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase review > /dev/null)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" verify --current)

printf 'plan-context smoke test complete\n'
