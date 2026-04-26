#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"

json_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_update_check.py" --json)"
python3 - <<'PY' "${json_output}"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get('status') not in {'valid', 'warning', 'invalid'}:
    raise SystemExit(f"Unexpected status: {payload.get('status')}")
for key in ['filesChecked', 'warnings', 'errors', 'mechanicalOnly']:
    if key not in payload:
        raise SystemExit(f"Missing key: {key}")
if payload.get('mechanicalOnly') is not True:
    raise SystemExit('Expected mechanicalOnly=true')
for forbidden in ['nextSteps', 'signals']:
    if forbidden in payload:
        raise SystemExit(f"Unexpected semantic recommendation key: {forbidden}")
PY

text_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_update_check.py" --summary "normalize api error contract" --changed-file "src/api/error_handler.py")"
case "${text_output}" in
  *"SPEC_UPDATE_CHECK_"* ) : ;;
  *) printf 'Expected mechanical status output from spec_update_check\n' >&2; exit 1 ;;
esac
python3 - <<'PY' "${text_output}"
import sys
text = sys.argv[1]
for forbidden in ['nextSteps', 'signals', 'one-shot update runner']:
    if forbidden in text:
        raise SystemExit(f'Unexpected semantic recommendation output: {forbidden}')
PY

candidate_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_target.py" --json)"
python3 - <<'PY' "${candidate_output}"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get('decisionMade') is not False:
    raise SystemExit('Expected candidate listing to make no target decision')
if 'candidates' not in payload:
    raise SystemExit('Expected candidates list')
PY

printf 'spec-update-check smoke test complete\n'
