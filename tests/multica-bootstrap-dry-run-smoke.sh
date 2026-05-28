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
BASH_EXE="$(command -v bash)"
if command -v cygpath >/dev/null 2>&1; then
  BASH_EXE="$(cygpath -am "$BASH_EXE")"
fi
export BASH_EXE
TARGET_REPO="$TMP/target-repo"
SKILL_PACK_DIR="$TMP/skill-pack"
mkdir -p "$TARGET_REPO/.superpowers/wiki" "$TARGET_REPO/.shared-superpowers/wiki"
printf '# Project Wiki\n' > "$TARGET_REPO/.superpowers/wiki/index.md"
printf '# Shared Wiki\n' > "$TARGET_REPO/.shared-superpowers/wiki/index.md"

"$ROOT/manage.sh" multica-bootstrap bootstrap \
  --superpowers-source "$SUPERPOWERS_SOURCE" \
  --target-repo "$TARGET_REPO" \
  --skill-pack-dir "$SKILL_PACK_DIR" \
  --dry-run \
  --json \
  > "$TMP/bootstrap.json"

python3 - <<'PY' "$TMP/bootstrap.json" "$SKILL_PACK_DIR"
from pathlib import Path
import json
import sys

result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
skill_pack_dir = Path(sys.argv[2])
skill_root = skill_pack_dir / 'superpowers-adapter'
required_files = [
    skill_root / 'SKILL.md',
    skill_root / 'skills' / 'init-wiki' / 'SKILL.md',
    skill_root / 'skills' / 'update-wiki' / 'SKILL.md',
    skill_root / 'skills' / 'lanhu-requirements' / 'SKILL.md',
    skill_root / 'agents' / 'wiki-researcher.md',
    skill_root / 'agents' / 'source-of-truth-verifier.md',
    skill_root / 'scripts' / 'wiki_context_render.py',
    skill_root / 'scripts' / 'source_truth_render.py',
    skill_root / 'scripts' / 'source_truth_settings.py',
    skill_root / 'scripts' / 'wiki_read_section.py',
    skill_root / 'upstream-superpowers' / 'brainstorming.md',
    skill_root / 'upstream-superpowers' / 'writing-plans.md',
    skill_root / 'upstream-superpowers' / 'subagent-driven-development.md',
]
missing = [path.as_posix() for path in required_files if not path.is_file()]
if missing:
    raise SystemExit(f'Missing generated skill pack files: {missing}')

root_text = (skill_root / 'SKILL.md').read_text(encoding='utf-8')
if 'name: superpowers-adapter' not in root_text:
    raise SystemExit('Root SKILL.md missing skill frontmatter name')
serialized = json.dumps(result, ensure_ascii=False)
if 'Target repo:' not in serialized:
    raise SystemExit('Dry-run output missing target repo smoke issue body')
if 'User-facing language:' not in serialized:
    raise SystemExit('Dry-run output missing user-facing language inference rule')
if 'Infer the user\'s preferred language' not in root_text:
    raise SystemExit('Root SKILL.md missing user-facing language inference rule')
if 'superpowers-source-of-truth-verifier' not in root_text:
    raise SystemExit('Root SKILL.md missing visible source-truth verifier role-agent guidance')
if 'source_truth_render.py' not in root_text:
    raise SystemExit('Root SKILL.md missing source-truth renderer guidance')

brainstorming = (skill_root / 'upstream-superpowers' / 'brainstorming.md').read_text(encoding='utf-8')
if '<!-- superpower-adapter:native-skill:brainstorming-wiki-disclosure -->' not in brainstorming:
    raise SystemExit('Patched brainstorming upstream skill missing adapter native patch')
if '.claude/skills/superpowers-adapter/scripts/lanhu_settings.py' not in brainstorming:
    raise SystemExit('Patched brainstorming skill did not rewrite adapter plugin root to Multica skill root')
writing_plans = (skill_root / 'upstream-superpowers' / 'writing-plans.md').read_text(encoding='utf-8')
for required in ('source-of-truth-verifier', 'source-truth-report.json', 'source-truth-constraints.json', 'Source-of-Truth Verification'):
    if required not in writing_plans:
        raise SystemExit(f'Patched writing-plans skill missing source-truth text: {required}')
execute_plan = (skill_root / 'upstream-superpowers' / 'executing-plans.md').read_text(encoding='utf-8')
sdd = (skill_root / 'upstream-superpowers' / 'subagent-driven-development.md').read_text(encoding='utf-8')
for text, label in ((execute_plan, 'execute-plan'), (sdd, 'sdd')):
    for required in ('source_truth_render.py', 'source-truth-constraints.json', 'source-truth-report.json'):
        if required not in text:
            raise SystemExit(f'Patched {label} skill missing source-truth execution text: {required}')

commands = result.get('commands', [])
if not commands:
    raise SystemExit('Dry-run output missing planned commands')
if any(command.get('executed') for command in commands):
    raise SystemExit(f'Dry-run unexpectedly executed commands: {commands}')
rendered = [' '.join(command.get('argv', [])) for command in commands]
expected_fragments = [
    'multica auth status',
    'multica daemon status',
    'multica runtime list',
    'multica skill create',
    'multica skill files upsert',
    'multica agent create',
    'superpowers-source-of-truth-verifier',
    'multica agent skills set',
    'multica issue create',
    'multica issue assign',
]
missing_fragments = [fragment for fragment in expected_fragments if not any(fragment in command for command in rendered)]
if missing_fragments:
    raise SystemExit(f'Dry-run missing planned Multica commands: {missing_fragments}\nCommands: {rendered}')
if result.get('apply') is not False:
    raise SystemExit('Dry-run result must report apply=false')
if result.get('skillPack', {}).get('name') != 'superpowers-adapter':
    raise SystemExit('Dry-run result missing skill pack name')
PY

python3 - <<'PY' "$ROOT" "$TARGET_REPO" "$TMP"
from pathlib import Path
import json
import os
import subprocess
import sys

root = Path(sys.argv[1])
target_repo = Path(sys.argv[2])
tmp = Path(sys.argv[3])
fixtures = tmp / 'fixtures'
fixtures.mkdir(parents=True, exist_ok=True)
requirements = fixtures / 'requirements.md'
spec = fixtures / 'spec.md'
plan = fixtures / 'plan.md'
wiki_context = fixtures / 'plan.wiki-context.json'
debug_evidence = fixtures / 'debug-evidence.md'
requirements.write_text('# Requirements\n', encoding='utf-8')
spec.write_text('# Spec\n', encoding='utf-8')
plan.write_text('# Plan\n', encoding='utf-8')
wiki_context.write_text('{"schemaVersion": 3}\n', encoding='utf-8')
debug_evidence.write_text('# Debug evidence\n', encoding='utf-8')

cases = {
    'smoke': ('skills/superpowers-adapter/SKILL.md', []),
    'lanhu-intake': ('skills/lanhu-requirements/SKILL.md', ['--requirements-path', requirements.as_posix()]),
    'brainstorming': ('upstream-superpowers/brainstorming.md', []),
    'writing-plans': ('upstream-superpowers/writing-plans.md', ['--spec-path', spec.as_posix()]),
    'execute-plan': ('upstream-superpowers/executing-plans.md', ['--plan-path', plan.as_posix(), '--wiki-context-path', wiki_context.as_posix()]),
    'sdd-execution': ('upstream-superpowers/subagent-driven-development.md', ['--plan-path', plan.as_posix(), '--wiki-context-path', wiki_context.as_posix()]),
    'systematic-debugging': ('upstream-superpowers/systematic-debugging.md', ['--debug-evidence', debug_evidence.as_posix()]),
    'break-loop': ('skills/break-loop/SKILL.md', ['--debug-evidence', debug_evidence.as_posix()]),
    'update-wiki': ('skills/update-wiki/SKILL.md', ['--plan-path', plan.as_posix()]),
    'publish-shared-wiki': ('skills/publish-shared-wiki/SKILL.md', ['--shared-wiki-topic', 'portable API contracts']),
    'shared-wiki-mcp-pr': ('skills/shared-wiki-mcp/SKILL.md', ['--shared-wiki-topic', 'portable API contracts']),
}

def manage_command(*args):
    return [os.environ.get('BASH_EXE', 'bash'), (root / 'manage.sh').as_posix(), *args]


def run_template(template, extra):
    command = manage_command(
        'multica-bootstrap',
        'create-issue',
        '--target-repo',
        target_repo.as_posix(),
        '--issue-template',
        template,
        '--dry-run',
        '--json',
        *extra,
    )
    completed = subprocess.run(command, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise SystemExit(f'Template {template} dry-run failed:\nSTDOUT={completed.stdout}\nSTDERR={completed.stderr}')
    return json.loads(completed.stdout)

def issue_body(result):
    commands = result.get('commands', [])
    if any(command.get('executed') for command in commands):
        raise SystemExit(f'Dry-run unexpectedly executed commands: {commands}')
    for command in commands:
        argv = command.get('argv', [])
        if argv[:3] == ['multica', 'issue', 'create']:
            for flag in ('--description', '--body'):
                if flag in argv:
                    return argv[argv.index(flag) + 1]
    raise SystemExit(f'Dry-run output missing issue create body: {commands}')

for template, (entrypoint, extra) in cases.items():
    result = run_template(template, extra)
    if result.get('issue', {}).get('template') != template:
        raise SystemExit(f'Template {template} missing JSON issue.template: {result}')
    body = issue_body(result)
    expected = [
        f'Issue template: {template}',
        f'Entrypoint: {entrypoint}',
        'Target repo:',
        'Use the attached `superpowers-adapter` skill pack.',
        'Do not commit, push, create or merge PRs',
        'User-facing language:',
        "Infer the user's preferred language",
    ]
    missing = [fragment for fragment in expected if fragment not in body]
    if missing:
        raise SystemExit(f'Template {template} body missing {missing}:\n{body}')
    if template == 'writing-plans':
        for required in ('superpowers-source-of-truth-verifier', 'source-truth-report.json', 'source-truth-constraints.json', 'constraintSets', 'taskConstraintRefs', 'Source-of-Truth Verification'):
            if required not in body:
                raise SystemExit(f'writing-plans issue body missing source-truth requirement {required!r}:\n{body}')
    if template in {'execute-plan', 'sdd-execution'}:
        for required in ('Source-truth constraints path', 'source_truth_render.py', '--fingerprint-preflight', '--task-id', 'do not read the full `*.source-truth-report.json`'):
            if required not in body:
                raise SystemExit(f'{template} issue body missing constraints-only execution guidance {required!r}:\n{body}')
    if template in {'publish-shared-wiki', 'shared-wiki-mcp-pr'} and 'Authorization gate:' not in body:
        raise SystemExit(f'Template {template} must keep an authorization gate without --allow-external-side-effects:\n{body}')

custom_body_command = manage_command(
    'multica-bootstrap',
    'create-issue',
    '--target-repo',
    target_repo.as_posix(),
    '--issue-body',
    '# 自定义中文 issue\n\n请用中文回复。',
    '--dry-run',
    '--json',
)
completed = subprocess.run(custom_body_command, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if completed.returncode != 0:
    raise SystemExit(f'Custom issue body dry-run failed:\nSTDOUT={completed.stdout}\nSTDERR={completed.stderr}')
custom_body = issue_body(json.loads(completed.stdout))
if 'User-facing language:' not in custom_body or "Infer the user's preferred language" not in custom_body:
    raise SystemExit(f'Custom issue body must include language inference rule:\n{custom_body}')

observe_command = manage_command(
    'multica-bootstrap',
    'bootstrap',
    '--superpowers-source',
    root.parent.joinpath('superpowers').as_posix(),
    '--target-repo',
    target_repo.as_posix(),
    '--skill-pack-dir',
    (tmp / 'observe-skill-pack').as_posix(),
    '--observe-runs',
    '--observe-timeout-seconds',
    '1',
    '--observe-interval-seconds',
    '1',
    '--dry-run',
    '--json',
)
completed = subprocess.run(observe_command, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if completed.returncode != 0:
    raise SystemExit(f'Observe bootstrap dry-run failed:\nSTDOUT={completed.stdout}\nSTDERR={completed.stderr}')
observe_result = json.loads(completed.stdout)
observe_commands = [' '.join(command.get('argv', [])) for command in observe_result.get('commands', [])]
if not any('multica issue runs <created-issue-id>' in command for command in observe_commands):
    raise SystemExit(f'Observe bootstrap dry-run must plan issue run observation commands: {observe_commands}')
if observe_result.get('observations'):
    raise SystemExit(f'Dry-run must not collect live observations: {observe_result.get("observations")}')

negative_cases = [
    ('execute-plan', []),
    ('lanhu-intake', []),
]
for template, extra in negative_cases:
    command = manage_command(
        'multica-bootstrap',
        'create-issue',
        '--target-repo',
        target_repo.as_posix(),
        '--issue-template',
        template,
        '--dry-run',
        '--json',
        *extra,
    )
    completed = subprocess.run(command, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode == 0:
        raise SystemExit(f'Template {template} should fail without required inputs')
    if 'requires' not in completed.stdout:
        raise SystemExit(f'Template {template} failure should explain required inputs:\n{completed.stdout}\n{completed.stderr}')

removed_agent_command = manage_command(
    'multica-bootstrap',
    'create-issue',
    '--target-repo',
    target_repo.as_posix(),
    '--agent-name',
    'superpowers-adapter-orchestrator',
    '--dry-run',
    '--json',
)
completed = subprocess.run(removed_agent_command, text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if completed.returncode == 0:
    raise SystemExit('superpowers-adapter-orchestrator should be rejected by multica-bootstrap')
if 'has been removed' not in completed.stdout:
    raise SystemExit(f'Removed agent failure should explain removal:\n{completed.stdout}\n{completed.stderr}')
PY

printf 'multica-bootstrap dry-run smoke OK\n'
