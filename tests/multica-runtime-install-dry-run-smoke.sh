#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUPERPOWERS_SOURCE="${1:-${ROOT}/../superpowers}"
if [[ -d "$SUPERPOWERS_SOURCE" ]]; then
  SUPERPOWERS_SOURCE="$(cd "$SUPERPOWERS_SOURCE" && pwd)"
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
RUNTIME_ROOT="$TMP/multica-superpowers-runtime"

"$ROOT/manage.sh" build-multica-runtime "$SUPERPOWERS_SOURCE" "$ROOT" "$RUNTIME_ROOT" >/dev/null
"$ROOT/manage.sh" install-multica-runtime "$RUNTIME_ROOT" --dry-run --json > "$TMP/install-plan.json"
"$ROOT/manage.sh" install-multica-runtime "$RUNTIME_ROOT" --dry-run --require-native-surfaces --json > "$TMP/install-native-surfaces.json"

python3 - <<'PY' "$TMP/install-plan.json"
from pathlib import Path
import json
import sys

result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if result.get('status') != 'planned':
    raise SystemExit(f'Runtime install dry-run should be planned: {result}')
if result.get('apply') is not False:
    raise SystemExit('Runtime install dry-run must report apply=false')
runtime = result.get('runtime', {})
for key in ('workflowCount', 'roleAgentCount', 'gateCount', 'triggerCount', 'schemaCount'):
    if not runtime.get(key):
        raise SystemExit(f'Runtime install plan missing runtime {key}: {runtime}')
commands = result.get('commands', [])
if not commands:
    raise SystemExit('Runtime install dry-run missing planned commands')
if any(command.get('executed') for command in commands):
    raise SystemExit(f'Runtime install dry-run unexpectedly executed commands: {commands}')
rendered = [' '.join(command.get('argv', [])) for command in commands]
for fragment in ('multica auth status', 'multica daemon status', 'multica runtime list'):
    if not any(fragment in command for command in rendered):
        raise SystemExit(f'Runtime install dry-run missing planned command: {fragment}\nCommands: {rendered}')
checks = {check.get('id'): check for check in result.get('checks', [])}
required_checks = [
    'runtime-verify',
    'manifest-workflows',
    'manifest-gates',
    'manifest-triggers',
    'manifest-schemas',
    'manifest-artifactContracts',
    'manifest-roleAgentContracts',
    'manifest-gateContracts',
    'manifest-issueTemplateBindings',
    'manifest-artifactNextActions',
]
missing = [check_id for check_id in required_checks if check_id not in checks]
if missing:
    raise SystemExit(f'Runtime install dry-run missing checks: {missing}')
if checks['runtime-verify'].get('status') != 'passed':
    raise SystemExit(f'Runtime verifier check should pass: {checks["runtime-verify"]}')
live_surfaces = result.get('liveSurfaces', {})
required_surfaces = [
    'runtime-install',
    'workflow-registration',
    'role-agent-registration',
    'gate-registration',
    'trigger-registration',
    'schema-registration',
    'tool-manifest-registration',
    'artifact-store-api',
    'gate-state-api',
    'role-task-api',
    'mcp-live-probing',
    'issue-metadata-state-substitute',
    'issue-run-observation-substitute',
    'issue-comment-artifact-substitute',
    'autopilot-trigger-substitute',
]
missing_surfaces = [surface for surface in required_surfaces if surface not in live_surfaces]
if missing_surfaces:
    raise SystemExit(f'Runtime install dry-run missing live surface probes: {missing_surfaces}')
for surface_id, surface in live_surfaces.items():
    if surface.get('status') not in {'supported', 'manual'}:
        raise SystemExit(f'Live surface {surface_id} has invalid status: {surface}')
    if not surface.get('candidates'):
        raise SystemExit(f'Live surface {surface_id} missing candidate commands: {surface}')
for surface_id in ('issue-metadata-state-substitute', 'issue-run-observation-substitute', 'issue-comment-artifact-substitute', 'autopilot-trigger-substitute'):
    if live_surfaces[surface_id].get('status') != 'supported':
        raise SystemExit(f'Official substitute surface should be supported: {surface_id} {live_surfaces[surface_id]}')
for surface_id in ('runtime-install', 'workflow-registration', 'gate-registration', 'trigger-registration', 'schema-registration', 'artifact-store-api', 'gate-state-api', 'mcp-live-probing'):
    if live_surfaces[surface_id].get('status') != 'manual':
        raise SystemExit(f'Native surface should remain manual unless official command exists: {surface_id} {live_surfaces[surface_id]}')
manual_steps = result.get('manualSteps', [])
if not any('MULTICA_SUPERPOWERS_RUNTIME_ROOT' in step for step in manual_steps):
    raise SystemExit(f'Runtime install plan must mention runtime env setup: {manual_steps}')
for fragment in ('workflow', 'artifact', 'gate', 'fresh role task', 'MCP'):
    if not any(fragment.lower() in step.lower() for step in manual_steps):
        raise SystemExit(f'Runtime install plan must include {fragment} manual step: {manual_steps}')
PY

python3 - <<'PY' "$TMP/install-native-surfaces.json"
from pathlib import Path
import json
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if result.get('status') != 'planned':
    raise SystemExit(f'Native surfaces run should be planned through official substitutes: {result}')
if result.get('error'):
    raise SystemExit(f'Require-native-surfaces should not fail when official substitutes cover exact native gaps: {result}')
checks = {check.get('id'): check for check in result.get('checks', [])}
for surface_id in ('runtime-install', 'workflow-registration', 'gate-registration', 'trigger-registration', 'schema-registration', 'artifact-store-api', 'gate-state-api', 'mcp-live-probing'):
    check = checks.get(f'multica-{surface_id}-substituted')
    if not check or check.get('status') != 'passed':
        raise SystemExit(f'Missing substitute coverage for {surface_id}: {checks}')
for check_id in ('multica-role-agent-materialization', 'multica-role-squad-create', 'multica-role-squad-members', 'multica-substitute-plan-issue', 'multica-substitute-metadata-store', 'multica-substitute-artifact-store', 'multica-substitute-run-observation', 'multica-substitute-autopilot-trigger'):
    check = checks.get(check_id)
    if not check or check.get('status') not in {'passed', 'warning'}:
        raise SystemExit(f'Missing substitute install check {check_id}: {checks}')
if not result.get('roleAgentIds'):
    raise SystemExit(f'Require-native-surfaces should include planned role agents: {result}')
if not result.get('squadId'):
    raise SystemExit(f'Require-native-surfaces should include planned squad id: {result}')
rendered = [' '.join(command.get('argv', [])) for command in result.get('commands', [])]
for fragment in ('multica agent create', 'multica squad create', 'multica squad member add', 'multica issue create', 'multica issue metadata set', 'multica issue comment add', 'multica issue get', 'multica issue runs'):
    if not any(fragment in command for command in rendered):
        raise SystemExit(f'Require-native-surfaces missing substitute command {fragment}: {rendered}')
PY

printf 'multica-runtime-install dry-run smoke OK\n'
