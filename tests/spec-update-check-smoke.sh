#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"

recommend_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_update_check.py" --summary "normalize backend error contract" --changed-file "src/backend/api/error_handler.py")"
case "${recommend_output}" in
  *"STRONGLY_RECOMMEND_UPDATE"* ) : ;;
  *) printf 'Expected strong recommend output from spec_update_check\n' >&2; exit 1 ;;
esac

json_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_update_check.py" --summary "normalize backend error contract" --changed-file "src/backend/api/error_handler.py" --json)"
python3 - <<'PY' "${json_output}"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get('status') != 'strongly_recommend_update':
    raise SystemExit(f"Expected strongly_recommend_update, got {payload.get('status')}")
if len(payload.get('signals', [])) < 2:
    raise SystemExit(f"Expected at least 2 signals, got {payload.get('signals')}")
if not payload.get('nextSteps'):
    raise SystemExit('Expected nextSteps to be present for recommend result')
PY

no_update_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_update_check.py" --summary "small ui tweak")"
case "${no_update_output}" in
  *"NO_UPDATE_NEEDED"* ) : ;;
  *) printf 'Expected no-update output from spec_update_check\n' >&2; exit 1 ;;
esac

printf 'spec-update-check smoke test complete\n'
