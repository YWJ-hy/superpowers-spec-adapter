#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"
PLAN_PATH="docs/superpowers/plans/plan-context-smoke.md"
PLAN_ABS="${PROJECT_ROOT}/${PLAN_PATH}"

mkdir -p "${PROJECT_ROOT}/docs/superpowers/plans"
printf '# Plan Context Smoke Test\n\n- [ ] Verify sidecar context lifecycle\n' > "${PLAN_ABS}"

(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" init "${PLAN_PATH}" --set-current)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" add --phase plan --plan "${PLAN_PATH}" --spec "${PROJECT_ROOT}/.superpowers/spec/index.md" --reason "Smoke test planning context")
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase implement > /dev/null)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" render --phase review > /dev/null)
(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/plan-context.py" verify --current)

printf 'plan-context smoke test complete\n'
