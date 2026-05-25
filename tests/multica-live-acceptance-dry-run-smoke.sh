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
TARGET_REPO="$TMP/target-repo"
mkdir -p "$TARGET_REPO/.superpowers/wiki" "$TARGET_REPO/.shared-superpowers/wiki" "$TMP/fixtures"
printf '# Project Wiki\n' > "$TARGET_REPO/.superpowers/wiki/index.md"
printf '# Shared Wiki\n' > "$TARGET_REPO/.shared-superpowers/wiki/index.md"
printf '# Requirements\n' > "$TMP/fixtures/requirements.md"
printf '# Spec\n' > "$TMP/fixtures/spec.md"
printf '# Approved Plan\n' > "$TMP/fixtures/plan.md"
printf '{"schemaVersion": 3}\n' > "$TMP/fixtures/plan.wiki-context.json"
printf '# Debug Evidence\n' > "$TMP/fixtures/debug-evidence.md"

"$ROOT/manage.sh" multica-live-acceptance \
  --target-repo "$TARGET_REPO" \
  --superpowers-source "$SUPERPOWERS_SOURCE" \
  --requirements-path "$TMP/fixtures/requirements.md" \
  --spec-path "$TMP/fixtures/spec.md" \
  --plan-path "$TMP/fixtures/plan.md" \
  --wiki-context-path "$TMP/fixtures/plan.wiki-context.json" \
  --debug-evidence "$TMP/fixtures/debug-evidence.md" \
  --shared-wiki-topic "portable API contracts" \
  --dry-run \
  --json \
  > "$TMP/live-acceptance.json"

python3 - <<'PY' "$TMP/live-acceptance.json"
from pathlib import Path
import json
import sys

result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if result.get('status') != 'planned':
    raise SystemExit(f'Visual acceptance dry-run should be planned: {result}')
if result.get('apply') is not False:
    raise SystemExit('Visual acceptance dry-run must report apply=false')
expected_cases = set('ABCDEFGH')
cases = {case.get('caseId'): case for case in result.get('cases', [])}
if set(cases) != expected_cases:
    raise SystemExit(f'Visual acceptance cases mismatch: {cases}')
commands = result.get('commands', [])
if not commands:
    raise SystemExit('Visual acceptance dry-run should plan Multica commands')
if any(command.get('executed') for command in commands):
    raise SystemExit(f'Visual acceptance dry-run unexpectedly executed commands: {commands}')
if any('multica_cli_bootstrap.py' in ' '.join(command.get('argv', [])) for command in commands):
    raise SystemExit('Visual acceptance must not delegate stage execution to multica_cli_bootstrap.py')
if any(command.get('assignee') == 'superpowers-adapter-orchestrator' for command in commands):
    raise SystemExit('Visual acceptance must not assign stages to superpowers-adapter-orchestrator')
required_assignees = {
    'superpowers-runtime-squad',
    'superpowers-lanhu-frontend-requirements-analyst',
    'superpowers-brainstorming-agent',
    'superpowers-wiki-researcher',
    'superpowers-planning-agent',
    'superpowers-spec-document-reviewer',
    'superpowers-plan-document-reviewer',
    'superpowers-implementer',
    'superpowers-spec-compliance-reviewer',
    'superpowers-code-quality-reviewer',
    'superpowers-code-reviewer',
    'superpowers-debugger',
    'superpowers-break-loop-analyst',
    'superpowers-wiki-curator',
    'superpowers-finisher',
    'superpowers-shared-wiki-publisher',
}
assignees = {command.get('assignee') for command in commands if command.get('action') == 'assign'}
missing = required_assignees - assignees
if missing:
    raise SystemExit(f'Visual acceptance missing role-agent assignments: {sorted(missing)}')
create_commands = [command for command in commands if command.get('action') == 'create']
if len(create_commands) < 30:
    raise SystemExit(f'Expected A-H stage issue creation fanout, got only {len(create_commands)} create commands')
for command in create_commands:
    argv_text = '\n'.join(command.get('argv', []))
    for required_text in ('Target repo:', 'Use the attached `superpowers-adapter` skill pack.', 'Do not assign this stage to `superpowers-adapter-orchestrator`'):
        if required_text not in argv_text:
            raise SystemExit(f'Stage issue body missing {required_text!r}: {command}')
checks = {check.get('id'): check for check in result.get('checks', [])}
if checks.get('role-agent-fanout', {}).get('status') != 'passed':
    raise SystemExit(f'Visual acceptance missing role-agent fanout check: {checks}')
if checks.get('external-side-effect-boundary', {}).get('status') != 'passed':
    raise SystemExit(f'Visual acceptance missing side-effect boundary check: {checks}')
PY

"$ROOT/manage.sh" multica-live-acceptance \
  --target-repo "$TARGET_REPO" \
  --superpowers-source "$SUPERPOWERS_SOURCE" \
  --case chain-d \
  --plan-path "$TMP/fixtures/plan.md" \
  --observe-runs \
  --observe-timeout-seconds 1 \
  --observe-interval-seconds 1 \
  --dry-run \
  --json \
  > "$TMP/observe.json"
python3 - <<'PY' "$TMP/observe.json"
from pathlib import Path
import json
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
commands = result.get('commands', [])
observe = [command for command in commands if command.get('action') == 'observe']
if not observe:
    raise SystemExit(f'Observe dry-run should plan issue run / role-agent task observations: {commands}')
if not any(command.get('argv', [])[:3] == ['multica', 'issue', 'runs'] for command in observe):
    raise SystemExit(f'Observe dry-run missing issue runs command: {observe}')
if any(command.get('argv', [])[:3] == ['multica', 'agent', 'tasks'] for command in observe):
    raise SystemExit(f'Observe dry-run should use issue runs as the canonical role-run observation surface: {observe}')
PY

"$ROOT/manage.sh" multica-live-acceptance \
  --target-repo "$TARGET_REPO" \
  --case chain-d \
  --dry-run \
  --json \
  > "$TMP/missing-plan.json" && {
    printf 'Expected chain-d without --plan-path to fail\n' >&2
    exit 1
  }
python3 - <<'PY' "$TMP/missing-plan.json"
from pathlib import Path
import json
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if 'requires --plan-path' not in result.get('error', ''):
    raise SystemExit(f'Missing plan failure should explain required input: {result}')
PY

"$ROOT/manage.sh" multica-live-acceptance \
  --target-repo "$TARGET_REPO" \
  --agent-name superpowers-adapter-orchestrator \
  --dry-run \
  --json \
  > "$TMP/orchestrator.json" && {
    printf 'Expected superpowers-adapter-orchestrator to be rejected\n' >&2
    exit 1
  }
python3 - <<'PY' "$TMP/orchestrator.json"
from pathlib import Path
import json
import sys
result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if 'superpowers-adapter-orchestrator is no longer valid' not in result.get('error', ''):
    raise SystemExit(f'Orchestrator rejection should be explicit: {result}')
PY

printf 'multica-live-acceptance visual dry-run smoke OK\n'
