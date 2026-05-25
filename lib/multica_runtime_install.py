#!/usr/bin/env python3
"""Plan or run safe Multica runtime installation steps."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from multica_runtime_spec import EXPECTED_ROLE_AGENTS, EXPECTED_WORKFLOWS, GATES, SCHEMAS, TRIGGERS


ISSUE_ID_RE = re.compile(r'\b[A-Z][A-Z0-9]+-\d+\b')
UUID_RE = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
NATIVE_SURFACE_SUBSTITUTES = {
    'runtime-install': ('issue-metadata-state-substitute', 'issue-comment-artifact-substitute'),
    'workflow-registration': ('issue-metadata-state-substitute', 'issue-comment-artifact-substitute'),
    'gate-registration': ('issue-metadata-state-substitute', 'issue-comment-artifact-substitute'),
    'trigger-registration': ('autopilot-trigger-substitute', 'issue-metadata-state-substitute'),
    'schema-registration': ('issue-metadata-state-substitute', 'issue-comment-artifact-substitute'),
    'artifact-store-api': ('issue-comment-artifact-substitute',),
    'gate-state-api': ('issue-metadata-state-substitute', 'issue-run-observation-substitute'),
    'mcp-live-probing': ('issue-metadata-state-substitute',),
}


class InstallError(SystemExit):
    pass


@dataclass
class Check:
    id: str
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {'id': self.id, 'status': self.status, 'message': self.message}
        payload.update(self.data)
        return payload


@dataclass
class RuntimeInstallContext:
    args: argparse.Namespace
    adapter_root: Path
    runtime_root: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)
    live_surfaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    substitute_plan_issue_id: str | None = None
    skill_id: str | None = None
    runtime_id: str | None = None
    role_agent_ids: dict[str, str] = field(default_factory=dict)
    squad_id: str | None = None

    @property
    def apply(self) -> bool:
        return bool(self.args.apply)

    def add_check(self, check_id: str, status: str, message: str, **data: Any) -> None:
        self.checks.append(Check(check_id, status, message, data))

    def add_manual_step(self, step: str) -> None:
        if step not in self.manual_steps:
            self.manual_steps.append(step)

    def as_dict(self) -> dict[str, Any]:
        status = 'blocked' if any(check.status == 'blocked' for check in self.checks) else 'ok'
        if not self.apply and status == 'ok':
            status = 'planned'
        return {
            'status': status,
            'apply': self.apply,
            'adapterRoot': self.adapter_root.as_posix(),
            'runtimeRoot': self.runtime_root.as_posix(),
            'runtime': {
                'name': self.manifest.get('name'),
                'schemaVersion': self.manifest.get('schemaVersion'),
                'workflowCount': len(self.manifest.get('workflows', [])),
                'roleAgentCount': len(self.manifest.get('roleAgents', [])),
                'gateCount': len(self.manifest.get('gates', [])),
                'triggerCount': len(self.manifest.get('triggers', [])),
                'schemaCount': len(self.manifest.get('schemas', [])),
            },
            'substitutePlanIssueId': self.substitute_plan_issue_id,
            'skillId': self.skill_id,
            'runtimeId': self.runtime_id,
            'roleAgentIds': self.role_agent_ids,
            'squadId': self.squad_id,
            'checks': [check.as_dict() for check in self.checks],
            'commands': self.commands,
            'liveSurfaces': self.live_surfaces,
            'manualSteps': self.manual_steps,
        }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def parse_json_records(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        records = []
        for line in stripped.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return records
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ('data', 'items', 'results', 'issues'):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def record_id(record: dict[str, Any]) -> str | None:
    for key in ('id', 'uuid', 'key'):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def record_name(record: dict[str, Any]) -> str | None:
    value = record.get('name')
    return value if isinstance(value, str) and value else None


def parse_created_id(text: str) -> str | None:
    for record in parse_json_records(text):
        value = record_id(record)
        if value:
            return value
    match = ISSUE_ID_RE.search(text) or UUID_RE.search(text)
    return match.group(0) if match else None


def run_process(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def help_result(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    if shutil.which('multica') is None:
        return None
    return run_process(['multica', *command, '--help'])


def help_text(command: list[str]) -> str:
    completed = help_result(command)
    if completed is None or completed.returncode != 0:
        return ''
    return completed.stdout + '\n' + completed.stderr


def has_help(command: list[str]) -> bool:
    return bool(help_text(command).strip())


def help_has_any_flag(text: str, flags: Sequence[str]) -> bool:
    return any(flag in text.split() or flag in text for flag in flags)


def help_matches_command(text: str, command: Sequence[str]) -> bool:
    usage = 'multica ' + ' '.join(command)
    return any(line.strip() == usage or line.strip().startswith(usage + ' ') for line in text.splitlines())


def probe_surface(ctx: RuntimeInstallContext, surface_id: str, commands: Sequence[Sequence[str]], purpose: str, *, required_flags: Sequence[str] = ()) -> dict[str, Any]:
    candidates = []
    selected: dict[str, Any] | None = None
    for command in commands:
        completed = help_result(list(command))
        text = '' if completed is None else completed.stdout + '\n' + completed.stderr
        help_matches = completed is not None and completed.returncode == 0 and help_matches_command(text, command)
        flags_ok = not required_flags or help_has_any_flag(text, required_flags)
        supported = help_matches and flags_ok
        candidate = {
            'command': ['multica', *command],
            'supported': supported,
            'helpReturncode': completed.returncode if completed is not None else None,
            'helpMatchesCommand': help_matches,
            'requiredFlagsPresent': flags_ok,
        }
        candidates.append(candidate)
        if supported and selected is None:
            selected = candidate
    result = {
        'purpose': purpose,
        'status': 'supported' if selected else 'manual',
        'selectedCommand': selected['command'] if selected else None,
        'candidates': candidates,
    }
    ctx.live_surfaces[surface_id] = result
    return result


def planned_or_run(ctx: RuntimeInstallContext, argv: list[str], purpose: str) -> subprocess.CompletedProcess[str] | None:
    record: dict[str, Any] = {'argv': argv, 'purpose': purpose, 'executed': False}
    if not ctx.apply:
        ctx.commands.append(record)
        return None

    completed = run_process(argv)
    record.update({
        'executed': True,
        'returncode': completed.returncode,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
    })
    ctx.commands.append(record)
    if completed.returncode != 0:
        raise InstallError(f'Multica command failed ({purpose}): {" ".join(argv)}\n{completed.stderr.strip()}')
    return completed


def substitute_issue_ref(ctx: RuntimeInstallContext) -> str:
    return ctx.substitute_plan_issue_id or '<runtime-registration-issue-id>'


def parse_record_lookup(command: list[str], match_name: str) -> str | None:
    completed = run_process(command)
    if completed.returncode != 0:
        return None
    for record in parse_json_records(completed.stdout):
        if record_name(record) == match_name:
            return record_id(record)
    return None


def lookup_skill_id(name: str) -> str | None:
    return parse_record_lookup(['multica', 'skill', 'list', '--output', 'json'], name)


def lookup_agent_id(name: str) -> str | None:
    return parse_record_lookup(['multica', 'agent', 'list', '--output', 'json'], name)


def lookup_squad_id(name: str) -> str | None:
    return parse_record_lookup(['multica', 'squad', 'list', '--output', 'json'], name)


def find_claude_runtime_id() -> str | None:
    completed = run_process(['multica', 'runtime', 'list', '--output', 'json'])
    if completed.returncode != 0:
        return None
    for record in parse_json_records(completed.stdout):
        provider = str(record.get('provider', '')).lower()
        name = str(record.get('name', '')).lower()
        status = str(record.get('status', '')).lower()
        value = record_id(record)
        if value and ('claude' in provider or 'claude' in name) and (not status or status == 'online'):
            return value
    for record in parse_json_records(completed.stdout):
        value = record_id(record)
        if value:
            return value
    return None


def runtime_contract_paths(ctx: RuntimeInstallContext) -> list[Path]:
    candidates = [
        ctx.runtime_root / 'manifest.json',
        ctx.runtime_root / 'dist' / 'preflight' / 'workflow-invocation-contract.json',
        ctx.runtime_root / 'dist' / 'preflight' / 'runtime-capabilities.json',
        ctx.runtime_root / 'dist' / 'preflight' / 'artifact-store-contract.json',
        ctx.runtime_root / 'dist' / 'preflight' / 'gate-transition-contract.json',
        ctx.runtime_root / 'dist' / 'preflight' / 'role-task-contract.json',
        ctx.runtime_root / 'dist' / 'triggers' / 'issue-template-bindings.json',
        ctx.runtime_root / 'dist' / 'triggers' / 'artifact-next-actions.json',
        ctx.runtime_root / 'dist' / 'gates' / 'gate-contracts.json',
        ctx.runtime_root / 'dist' / 'agents' / 'role-agent-contracts.json',
        ctx.runtime_root / 'dist' / 'schemas' / 'artifact-contracts.json',
        ctx.runtime_root / 'dist' / 'task-graphs' / 'subagent-driven-development.task-graph.json',
    ]
    return [path for path in candidates if path.is_file()]


def substitute_install_body(ctx: RuntimeInstallContext) -> str:
    runtime = ctx.as_dict()['runtime']
    unavailable = [surface_id for surface_id, surface in ctx.live_surfaces.items() if surface.get('status') == 'manual' and not surface_id.endswith('-substitute')]
    substitutes = [surface_id for surface_id, surface in ctx.live_surfaces.items() if surface.get('status') == 'supported' and surface_id.endswith('-substitute')]
    return '\n'.join([
        '# Superpowers runtime registration plan',
        '',
        f'Runtime root: {ctx.runtime_root.as_posix()}',
        f'Runtime name: {runtime.get("name")}',
        f'Schema version: {runtime.get("schemaVersion")}',
        f'Workflows: {runtime.get("workflowCount")}',
        f'Role agents: {runtime.get("roleAgentCount")}',
        f'Gates: {runtime.get("gateCount")}',
        f'Triggers: {runtime.get("triggerCount")}',
        f'Schemas: {runtime.get("schemaCount")}',
        '',
        'Use the attached runtime contract artifacts and issue metadata as the executable Multica registration layer for this workspace.',
        '',
        'Exact native CLI surfaces covered by documented substitutes:',
        *(f'- {surface_id}' for surface_id in unavailable),
        '',
        'Official substitute surfaces selected by the installer:',
        *(f'- {surface_id}' for surface_id in substitutes),
        '',
        'Required behavior:',
        '1. Treat issue metadata as the authoritative WorkflowInvocation / gate-state / schema-contract store for this runtime.',
        '2. Treat issue comments and attachments as the artifact reference channel for this runtime.',
        '3. Treat issue assign/rerun and issue run history as the fresh-role-task dispatch and observation channel.',
        '4. Treat autopilot triggers as the schedule/webhook trigger layer for this runtime.',
        '5. Do not call undocumented Multica APIs or destructive git operations from this registration issue.',
    ])


def create_substitute_plan_issue(ctx: RuntimeInstallContext) -> None:
    if not has_help(['issue', 'create']):
        ctx.add_check('multica-substitute-plan-issue', 'warning', '`multica issue create` is unavailable; substitute runtime registration cannot create a tracking issue automatically.')
        return
    argv = [
        'multica', 'issue', 'create',
        '--title', f'Superpowers runtime registration: {ctx.manifest.get("name", "multica-superpowers-runtime")}',
        '--description', substitute_install_body(ctx),
        '--allow-duplicate',
        '--output', 'json',
    ]
    completed = planned_or_run(ctx, argv, 'Create a Multica issue that stores the runtime registration plan and substitute surface mapping.')
    if completed is not None:
        ctx.substitute_plan_issue_id = parse_created_id(completed.stdout) or parse_created_id(completed.stderr)
        if ctx.substitute_plan_issue_id is None:
            raise InstallError('Could not resolve created runtime registration issue id from Multica output.')
    ctx.add_check('multica-substitute-plan-issue', 'passed', 'Runtime registration is represented by an executable Multica issue using official CLI surfaces.', issueId=substitute_issue_ref(ctx))


def role_agent_instruction(ctx: RuntimeInstallContext, agent_id: str, prompt: str) -> str:
    contract_path = ctx.runtime_root / 'dist' / 'agents' / 'role-agent-contracts.json'
    return '\n'.join([
        f'You are the `{agent_id}` role agent for the Multica Superpowers-compatible runtime.',
        '',
        f'Runtime root: {ctx.runtime_root.as_posix()}',
        f'Role contract: {contract_path.as_posix()}#{agent_id}',
        '',
        'Use the attached `superpowers-adapter` workspace skill pack for Superpowers-compatible workflow behavior.',
        'Treat each assigned issue/task as fresh context. Read only orchestrator-provided artifacts, issue metadata, attached runtime contracts, and the target repo named in the issue body.',
        'Do not commit, push, create PRs, publish shared wiki, delete files, or perform destructive git operations unless the issue body contains explicit authorization.',
        '',
        prompt.strip(),
    ])


def materialize_role_agents(ctx: RuntimeInstallContext) -> None:
    if not has_help(['agent', 'create']) or not has_help(['agent', 'update']):
        ctx.add_check('multica-role-agent-materialization', 'blocked', 'Multica agent create/update surfaces are unavailable.')
        return
    runtime_id = find_claude_runtime_id()
    if runtime_id is None:
        ctx.add_check('multica-role-agent-runtime', 'blocked', 'Could not resolve a Claude-compatible Multica runtime for role agents.')
        return
    ctx.runtime_id = runtime_id
    skill_id = lookup_skill_id('superpowers-adapter')
    if skill_id:
        ctx.skill_id = skill_id
    else:
        ctx.add_check('multica-role-agent-skill', 'warning', '`superpowers-adapter` skill is not present yet; role agents will be created and can receive the skill after multica-bootstrap imports it.')

    created_or_updated = 0
    for agent_id in EXPECTED_ROLE_AGENTS:
        prompt_path = ctx.runtime_root / 'dist' / 'agents' / f'{agent_id}.md'
        if not prompt_path.is_file():
            ctx.add_check(f'multica-role-agent-{agent_id}', 'blocked', f'Generated role agent prompt is missing: {prompt_path.as_posix()}')
            continue
        name = f'superpowers-{agent_id}'
        instructions = role_agent_instruction(ctx, agent_id, prompt_path.read_text(encoding='utf-8'))
        existing_id = lookup_agent_id(name) if ctx.apply else None
        if existing_id:
            completed = planned_or_run(ctx, ['multica', 'agent', 'update', existing_id, '--instructions', instructions, '--description', f'Superpowers runtime role agent: {agent_id}', '--runtime-id', runtime_id, '--visibility', 'workspace', '--output', 'json'], f'Update Multica role agent {name}.')
            role_agent_id = existing_id
        else:
            completed = planned_or_run(ctx, ['multica', 'agent', 'create', '--name', name, '--description', f'Superpowers runtime role agent: {agent_id}', '--instructions', instructions, '--runtime-id', runtime_id, '--visibility', 'workspace', '--output', 'json'], f'Create Multica role agent {name}.')
            role_agent_id = parse_created_id(completed.stdout) if completed is not None else f'<{name}-id>'
        if role_agent_id is None:
            raise InstallError(f'Could not resolve Multica role agent id for {name}.')
        ctx.role_agent_ids[agent_id] = role_agent_id
        created_or_updated += 1
        if ctx.skill_id and has_help(['agent', 'skills', 'set']):
            planned_or_run(ctx, ['multica', 'agent', 'skills', 'set', role_agent_id, '--skill-ids', ctx.skill_id, '--output', 'json'], f'Attach superpowers-adapter skill to role agent {name}.')
    ctx.add_check('multica-role-agent-materialization', 'passed', 'Generated runtime role agents are materialized as Multica agents.', count=created_or_updated, runtimeId=runtime_id, skillId=ctx.skill_id)


def squad_member_ids(squad_id: str) -> set[str]:
    completed = run_process(['multica', 'squad', 'member', 'list', squad_id, '--output', 'json'])
    if completed.returncode != 0:
        return set()
    ids = set()
    for record in parse_json_records(completed.stdout):
        value = record.get('member_id') or record.get('memberId') or record.get('id')
        if isinstance(value, str) and value:
            ids.add(value)
    return ids


def materialize_role_squad(ctx: RuntimeInstallContext) -> None:
    if not ctx.role_agent_ids:
        ctx.add_check('multica-role-squad', 'blocked', 'No materialized role agents are available for squad creation.')
        return
    if not has_help(['squad', 'create']) or not has_help(['squad', 'member', 'add']):
        ctx.add_check('multica-role-squad', 'warning', 'Multica squad create/member surfaces are unavailable; role agents were still materialized individually.')
        return
    squad_name = 'superpowers-runtime-squad'
    leader_id = ctx.role_agent_ids.get('superpowers-orchestrator') or next(iter(ctx.role_agent_ids.values()))
    existing_id = lookup_squad_id(squad_name) if ctx.apply else None
    if existing_id:
        ctx.squad_id = existing_id
        ctx.add_check('multica-role-squad-create', 'passed', 'Superpowers runtime squad already exists.', squadId=existing_id)
    else:
        completed = planned_or_run(ctx, ['multica', 'squad', 'create', '--name', squad_name, '--description', 'Superpowers-compatible runtime role-agent squad.', '--leader', leader_id, '--output', 'json'], 'Create Superpowers runtime role-agent squad.')
        ctx.squad_id = parse_created_id(completed.stdout) if completed is not None else '<superpowers-runtime-squad-id>'
        if ctx.squad_id is None:
            raise InstallError('Could not resolve created Superpowers runtime squad id from Multica output.')
        ctx.add_check('multica-role-squad-create', 'passed', 'Superpowers runtime squad is available.', squadId=ctx.squad_id)
    existing_member_ids = squad_member_ids(ctx.squad_id) if ctx.apply else set()
    for agent_id, multica_agent_id in ctx.role_agent_ids.items():
        if multica_agent_id in existing_member_ids:
            continue
        role = 'leader' if multica_agent_id == leader_id else agent_id
        planned_or_run(ctx, ['multica', 'squad', 'member', 'add', ctx.squad_id, '--member-id', multica_agent_id, '--type', 'agent', '--role', role, '--output', 'json'], f'Add role agent {agent_id} to Superpowers runtime squad.')
    ctx.add_check('multica-role-squad-members', 'passed', 'Superpowers runtime squad includes materialized role agents.', count=len(ctx.role_agent_ids), squadId=ctx.squad_id)


def materialize_runtime_roles(ctx: RuntimeInstallContext) -> None:
    materialize_role_agents(ctx)
    if any(check.status == 'blocked' for check in ctx.checks if check.id.startswith('multica-role-agent')):
        return
    materialize_role_squad(ctx)


def plan_substitute_runtime_commands(ctx: RuntimeInstallContext) -> None:
    materialize_runtime_roles(ctx)
    create_substitute_plan_issue(ctx)
    issue_ref = substitute_issue_ref(ctx)
    metadata_payloads = {
        'superpowers.runtime.root': ctx.runtime_root.as_posix(),
        'superpowers.runtime.name': str(ctx.manifest.get('name') or ''),
        'superpowers.runtime.schemaVersion': str(ctx.manifest.get('schemaVersion') or ''),
        'superpowers.runtime.workflowCount': str(len(ctx.manifest.get('workflows', []))),
        'superpowers.runtime.gateCount': str(len(ctx.manifest.get('gates', []))),
        'superpowers.runtime.triggerCount': str(len(ctx.manifest.get('triggers', []))),
        'superpowers.runtime.schemaCount': str(len(ctx.manifest.get('schemas', []))),
        'superpowers.runtime.workflowInvocationStore': 'issue-metadata',
        'superpowers.runtime.gateStateStore': 'issue-metadata',
        'superpowers.runtime.artifactStore': 'issue-comments-attachments',
        'superpowers.runtime.roleTaskDispatch': 'issue-assign-rerun',
        'superpowers.runtime.triggerProvider': 'autopilot-trigger-substitute',
    }
    if has_help(['issue', 'metadata', 'set']):
        for key, value in metadata_payloads.items():
            planned_or_run(ctx, ['multica', 'issue', 'metadata', 'set', issue_ref, '--key', key, '--value', value, '--type', 'string', '--output', 'json'], f'Store runtime metadata {key}.')
        ctx.add_check('multica-substitute-metadata-store', 'passed', 'WorkflowInvocation, gate state, schema, artifact, role-task, and trigger mappings are stored in issue metadata.')
    else:
        ctx.add_check('multica-substitute-metadata-store', 'blocked', '`multica issue metadata set` is unavailable; cannot store substitute runtime state.')

    if has_help(['issue', 'comment', 'add']):
        for path in runtime_contract_paths(ctx):
            planned_or_run(
                ctx,
                ['multica', 'issue', 'comment', 'add', issue_ref, '--content', f'Runtime contract artifact: {path.relative_to(ctx.runtime_root).as_posix()}', '--attachment', path.as_posix(), '--output', 'json'],
                f'Attach runtime contract artifact {path.relative_to(ctx.runtime_root).as_posix()}.',
            )
        ctx.add_check('multica-substitute-artifact-store', 'passed', 'Runtime contract artifacts are attached to the registration issue through official comment/attachment surfaces.', count=len(runtime_contract_paths(ctx)))
    else:
        ctx.add_check('multica-substitute-artifact-store', 'blocked', '`multica issue comment add` is unavailable; cannot attach runtime contract artifacts.')

    if has_help(['issue', 'runs']) and has_help(['issue', 'get']):
        planned_or_run(ctx, ['multica', 'issue', 'get', issue_ref, '--output', 'json'], 'Read runtime registration issue state for gate-state observation.')
        planned_or_run(ctx, ['multica', 'issue', 'runs', issue_ref, '--output', 'json'], 'Read runtime registration issue runs for role-task observation.')
        ctx.add_check('multica-substitute-run-observation', 'passed', 'Issue get and run history provide official observation surfaces for substituted runtime execution.')
    else:
        ctx.add_check('multica-substitute-run-observation', 'warning', 'Issue get or run history help is unavailable; observation may require UI inspection.')

    if has_help(['autopilot', 'create']) and has_help(['autopilot', 'trigger-add']):
        ctx.add_check('multica-substitute-autopilot-trigger', 'passed', 'Autopilot create/trigger-add is available as the official schedule/webhook trigger substitute.')
        ctx.add_manual_step('Create workflow-specific autopilots only after choosing the target project/agent; use `multica autopilot create` and `multica autopilot trigger-add` with this registration issue as the contract reference.')
    else:
        ctx.add_check('multica-substitute-autopilot-trigger', 'warning', 'Autopilot trigger surfaces are unavailable; trigger substitutes require manual scheduling.')


def verify_runtime(ctx: RuntimeInstallContext) -> None:
    manifest_path = ctx.runtime_root / 'manifest.json'
    if not manifest_path.is_file():
        ctx.add_check('runtime-manifest', 'blocked', 'Runtime manifest is missing.', path=manifest_path.as_posix())
        return
    ctx.manifest = load_json(manifest_path)
    verifier = ctx.adapter_root / 'lib' / 'multica_runtime_verify.py'
    completed = run_process(['python3', verifier.as_posix(), ctx.runtime_root.as_posix(), '--adapter-root', ctx.adapter_root.as_posix()])
    if completed.returncode == 0:
        ctx.add_check('runtime-verify', 'passed', 'Generated runtime bundle passed local verifier.')
    else:
        ctx.add_check('runtime-verify', 'blocked', 'Generated runtime bundle failed local verifier.', stderr=completed.stderr.strip(), stdout=completed.stdout.strip())


def verify_manifest_contract(ctx: RuntimeInstallContext) -> None:
    if not ctx.manifest:
        return
    expected = {
        'workflows': len(EXPECTED_WORKFLOWS),
        'gates': len(GATES),
        'triggers': len(TRIGGERS),
        'schemas': len(SCHEMAS),
    }
    for field, expected_count in expected.items():
        actual_count = len(ctx.manifest.get(field, []))
        if actual_count == expected_count:
            ctx.add_check(f'manifest-{field}', 'passed', f'Runtime manifest declares expected {field}.', count=actual_count)
        else:
            ctx.add_check(f'manifest-{field}', 'blocked', f'Runtime manifest {field} count mismatch.', expected=expected_count, actual=actual_count)
    for field in ('artifactContracts', 'roleAgentContracts', 'gateContracts', 'issueTemplateBindings', 'artifactNextActions'):
        if ctx.manifest.get(field):
            ctx.add_check(f'manifest-{field}', 'passed', f'Runtime manifest declares {field}.', count=len(ctx.manifest[field]))
        else:
            ctx.add_check(f'manifest-{field}', 'blocked', f'Runtime manifest missing {field}.')


def preflight_multica(ctx: RuntimeInstallContext) -> None:
    multica_path = shutil.which('multica')
    if multica_path:
        ctx.add_check('multica-cli', 'passed', 'Multica CLI is installed.', path=multica_path)
    elif ctx.apply:
        ctx.add_check('multica-cli', 'blocked', 'Multica CLI is not installed; install it before using --apply.')
        return
    else:
        ctx.add_check('multica-cli', 'warning', 'Multica CLI is not installed; dry-run will only produce a registration plan.')

    for argv, purpose in (
        (['multica', 'auth', 'status'], 'Check Multica login status.'),
        (['multica', 'daemon', 'status'], 'Check Multica daemon status.'),
        (['multica', 'runtime', 'list'], 'Check available Multica runtimes.'),
    ):
        planned_or_run(ctx, argv, purpose)


def plan_runtime_registration(ctx: RuntimeInstallContext) -> None:
    runtime_install = probe_surface(
        ctx,
        'runtime-install',
        (('runtime', 'install'),),
        'Install or import the generated Multica Superpowers runtime bundle.',
    )
    if runtime_install['status'] == 'supported':
        planned_or_run(ctx, ['multica', 'runtime', 'install', ctx.runtime_root.as_posix()], 'Install the generated Multica Superpowers runtime bundle.')
        ctx.add_check('multica-runtime-install-command', 'passed', '`multica runtime install` is available.')
    else:
        ctx.add_check('multica-runtime-install-command', 'warning', '`multica runtime install` was not detected; automatic runtime registration is not available in this CLI.')
        ctx.add_manual_step(f'Register or import the generated runtime bundle in Multica UI/CLI if supported: {ctx.runtime_root.as_posix()}')

    registration_surfaces = (
        ('workflow-registration', 'workflows', (('workflow', 'import'), ('workflow', 'create'), ('workflows', 'import')), 'Register workflow definitions from dist/workflows/.'),
        ('role-agent-registration', 'role agents', (('agent', 'create'), ('agent', 'update'), ('squad', 'create')), 'Register role agents from dist/agents/.'),
        ('gate-registration', 'gates', (('gate', 'import'), ('gate', 'create'), ('gates', 'import')), 'Register gate contracts from dist/gates/.'),
        ('trigger-registration', 'triggers', (('trigger', 'import'), ('trigger', 'create'), ('triggers', 'import')), 'Register trigger contracts from dist/triggers/.'),
        ('schema-registration', 'schemas', (('schema', 'import'), ('schema', 'create'), ('schemas', 'import')), 'Register schemas from dist/schemas/.'),
        ('tool-manifest-registration', 'tool manifest', (('skill', 'files', 'upsert'), ('skill', 'create'), ('project', 'resource', 'add')), 'Register tool manifest from dist/tools/tool-manifest.json.'),
        ('artifact-store-api', 'artifact store', (('artifact', 'put'), ('artifact', 'create'), ('artifacts', 'put'), ('runtime', 'artifacts')), 'Wire dist/preflight/artifact-store-contract.json to Multica artifact persistence.'),
        ('gate-state-api', 'gate state', (('gate', 'state'), ('gates', 'state'), ('gate', 'transition'), ('workflow', 'gates')), 'Wire dist/preflight/gate-transition-contract.json to live gate blocking/resume.'),
        ('role-task-api', 'fresh role tasks', (('issue', 'assign'), ('issue', 'rerun'), ('agent', 'tasks')), 'Wire dist/preflight/role-task-contract.json to fresh-context role task dispatch.'),
        ('mcp-live-probing', 'MCP live probing', (('mcp', 'list'), ('mcp', 'status'), ('server', 'list'), ('runtime', 'mcp')), 'Probe optional lanhu-mcp/shared-wiki-mcp/github-mcp availability before dependent workflows.'),
        ('issue-metadata-state-substitute', 'issue metadata state', (('issue', 'metadata', 'set'), ('issue', 'metadata', 'get'), ('issue', 'metadata', 'list')), 'Store WorkflowInvocation, gate state, and schema contract references as issue metadata when native runtime registries are unavailable.'),
        ('issue-run-observation-substitute', 'issue run observation', (('issue', 'runs'), ('issue', 'run-messages'), ('issue', 'get')), 'Observe workflow execution, role task output, and gate-blocked status through issue run history.'),
        ('issue-comment-artifact-substitute', 'issue comment artifacts', (('issue', 'comment', 'add'), ('issue', 'comment', 'list'), ('attachment', 'download')), 'Persist lightweight artifact references and retrieve attachment-backed evidence through issue comments when native artifact storage is unavailable.'),
        ('autopilot-trigger-substitute', 'autopilot triggers', (('autopilot', 'create'), ('autopilot', 'trigger-add'), ('autopilot', 'trigger')), 'Use official autopilot schedule/webhook triggers as a live trigger substitute when native workflow triggers are unavailable.'),
    )
    for surface_id, label, commands, manual in registration_surfaces:
        surface = probe_surface(ctx, surface_id, commands, manual)
        check_id = f'multica-{surface_id}'
        if surface['status'] == 'supported':
            selected = ' '.join(surface['selectedCommand'])
            check_status = 'passed' if surface_id.endswith('-substitute') else 'warning'
            message = f'CLI surface `{selected}` exists and is selected for runtime substitute mapping.' if surface_id.endswith('-substitute') else f'CLI surface `{selected}` exists; native registration command is available for this capability.'
            ctx.add_check(check_id, check_status, message)
            ctx.add_manual_step(f'Inspect `{selected} --help`, then {manual}')
        else:
            ctx.add_check(check_id, 'warning', f'No exact CLI surface detected for {label}.')
            ctx.add_manual_step(manual)

    uncovered_required_surfaces = []
    substituted_required_surfaces = []
    for surface_id, substitutes in NATIVE_SURFACE_SUBSTITUTES.items():
        surface = ctx.live_surfaces.get(surface_id, {})
        if surface.get('status') == 'supported':
            continue
        supported_substitutes = [substitute for substitute in substitutes if ctx.live_surfaces.get(substitute, {}).get('status') == 'supported']
        if supported_substitutes:
            substituted_required_surfaces.append((surface_id, supported_substitutes))
            ctx.add_check(f'multica-{surface_id}-substituted', 'passed', f'Exact native surface `{surface_id}` is covered by official substitute surfaces.', substitutes=supported_substitutes)
        else:
            uncovered_required_surfaces.append(surface_id)
            status = 'blocked' if ctx.args.require_native_surfaces else 'warning'
            ctx.add_check(f'multica-{surface_id}-uncovered', status, f'No exact native surface or documented substitute surface detected for {surface_id}.')

    if substituted_required_surfaces:
        plan_substitute_runtime_commands(ctx)

    if uncovered_required_surfaces and ctx.args.require_native_surfaces:
        raise InstallError(f'Official Multica CLI does not expose exact native runtime surfaces or supported substitutes: {", ".join(uncovered_required_surfaces)}')

    ctx.add_manual_step('After registration, configure runtime env MULTICA_SUPERPOWERS_RUNTIME_ROOT to the daemon-synced runtime root.')
    ctx.add_manual_step('After registration, run a disposable test issue and verify WorkflowInvocation preflight, gate blocking, artifact persistence, fresh role task creation, and MCP-dependent workflow blocking.')


def run(ctx: RuntimeInstallContext) -> None:
    verify_runtime(ctx)
    verify_manifest_contract(ctx)
    if any(check.status == 'blocked' for check in ctx.checks):
        if ctx.apply:
            raise InstallError('Runtime install preflight failed; fix blocked checks before using --apply.')
        return
    preflight_multica(ctx)
    if any(check.status == 'blocked' for check in ctx.checks) and ctx.apply:
        raise InstallError('Multica preflight failed; fix blocked checks before using --apply.')
    plan_runtime_registration(ctx)


def resolve_context(args: argparse.Namespace) -> RuntimeInstallContext:
    adapter_root = Path(args.adapter_root).expanduser().resolve()
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    if not adapter_root.is_dir() or not (adapter_root / 'manifest.json').is_file():
        raise InstallError(f'Missing adapter root manifest: {adapter_root}')
    if not runtime_root.is_dir():
        raise InstallError(f'Missing runtime root: {runtime_root}')
    return RuntimeInstallContext(args, adapter_root, runtime_root)


def print_text_summary(ctx: RuntimeInstallContext) -> None:
    data = ctx.as_dict()
    print(f'Multica runtime install status: {data["status"]}')
    print(f'Runtime root: {ctx.runtime_root}')
    for check in ctx.checks:
        print(f'- {check.status}: {check.id} — {check.message}')
    if ctx.commands:
        print('Commands:')
        for command in ctx.commands:
            prefix = 'ran' if command.get('executed') else 'planned'
            print(f'- {prefix}: {" ".join(command["argv"])}')
    if ctx.manual_steps:
        print('Manual steps:')
        for step in ctx.manual_steps:
            print(f'- {step}')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime_root')
    parser.add_argument('--adapter-root', default=Path(__file__).resolve().parents[1].as_posix())
    parser.add_argument('--apply', action='store_true', help='Execute supported external Multica registration commands. Without this flag, only dry-run planning is produced.')
    parser.add_argument('--require-native-surfaces', action='store_true', help='Fail unless every runtime capability has either an exact native CLI surface or a documented substitute surface.')
    parser.add_argument('--dry-run', action='store_true', help='Explicitly keep external Multica registration actions as planned commands.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        raise InstallError('Use either --apply or --dry-run, not both.')
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ctx = resolve_context(args)
    try:
        run(ctx)
    except InstallError as exc:
        if args.json:
            print(json.dumps(ctx.as_dict() | {'error': str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print_text_summary(ctx)
            print(f'Error: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(ctx.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text_summary(ctx)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
