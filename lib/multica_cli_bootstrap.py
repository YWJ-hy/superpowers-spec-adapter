#!/usr/bin/env python3
"""Bootstrap the Superpowers adapter into a real Multica workspace."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from adapter_manifest import installed_paths, load_manifest
from multica_runtime_spec import UPSTREAM_WORKFLOWS
from native_skill_patch import PATCHES, find_anchor, strip_block

GENERATED_BY = 'superpower-adapter multica bootstrap'
SKILL_NAME = 'superpowers-adapter'
DEFAULT_AGENT_NAME = 'superpowers-superpowers-orchestrator'
REMOVED_AGENT_NAME = 'superpowers-adapter-orchestrator'
DEFAULT_PROVIDER = 'claude'
MULTICA_SKILL_ROOT_HINT = f'.claude/skills/{SKILL_NAME}'
ISSUE_ID_RE = re.compile(r'\b[A-Z][A-Z0-9]+-\d+\b')
UUID_RE = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')


class BootstrapError(SystemExit):
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
class BootstrapContext:
    args: argparse.Namespace
    adapter_root: Path
    superpowers_source: Path | None
    target_repo: Path | None
    skill_pack_dir: Path
    skill_root: Path
    checks: list[Check] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    issue_id: str | None = None
    skill_id: str | None = None
    agent_id: str | None = None
    runtime_id: str | None = None
    agent_exists: bool | None = None

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
        if not self.apply:
            status = 'planned' if status == 'ok' else status
        return {
            'status': status,
            'apply': self.apply,
            'adapterRoot': self.adapter_root.as_posix(),
            'superpowersSource': self.superpowers_source.as_posix() if self.superpowers_source else None,
            'targetRepo': self.target_repo.as_posix() if self.target_repo else None,
            'skillPack': {
                'id': self.skill_id,
                'name': SKILL_NAME,
                'directory': self.skill_pack_dir.as_posix(),
                'root': self.skill_root.as_posix(),
                'multicaSkillRootHint': MULTICA_SKILL_ROOT_HINT,
            },
            'agent': {
                'id': self.agent_id,
                'name': self.args.agent_name,
                'provider': self.args.provider,
                'runtimeId': self.runtime_id,
                'exists': self.agent_exists,
            },
            'issue': {
                'id': self.issue_id,
                'title': self.args.issue_title or ISSUE_TEMPLATES[self.args.issue_template].default_title,
                'template': self.args.issue_template,
            },
            'checks': [check.as_dict() for check in self.checks],
            'commands': self.commands,
            'observations': self.observations,
            'manualSteps': self.manual_steps,
        }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_text(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def copy_file(src: Path, dst: Path, *, executable: bool = False) -> None:
    if not src.is_file():
        raise BootstrapError(f'Missing source file: {src}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if executable:
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_tree(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        ignored = {'.git', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', '.DS_Store'}
        return {name for name in names if name in ignored}

    if not src.is_dir():
        raise BootstrapError(f'Missing source directory: {src}')
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore)


def marker_path(skill_root: Path) -> Path:
    return skill_root / '.superpower-adapter-multica-skill-pack.json'


def reset_generated_skill_root(skill_root: Path) -> None:
    marker = marker_path(skill_root)
    if skill_root.exists():
        if not marker.is_file():
            raise BootstrapError(f'Refusing to replace non-generated skill pack directory: {skill_root}')
        try:
            marker_payload = load_json(marker)
        except json.JSONDecodeError as exc:
            raise BootstrapError(f'Invalid generated skill pack marker in {skill_root}: {exc}') from exc
        if marker_payload.get('generatedBy') != GENERATED_BY:
            raise BootstrapError(f'Refusing to replace skill pack generated by another tool: {skill_root}')
        shutil.rmtree(skill_root)
    skill_root.mkdir(parents=True)


def render_multica_patch_block(spec) -> str:
    body = spec.content.replace('__SUPERPOWER_ADAPTER_PLUGIN_ROOT__', MULTICA_SKILL_ROOT_HINT)
    return f'{spec.start_marker}\n{body.rstrip()}\n{spec.end_marker}\n'


def patched_upstream_skill(superpowers_source: Path, workflow_id: str) -> str:
    source_path = superpowers_source / 'skills' / workflow_id / 'SKILL.md'
    if not source_path.is_file():
        raise BootstrapError(f'Missing upstream Superpowers skill: {source_path}')
    text = source_path.read_text(encoding='utf-8')
    for spec in PATCHES:
        if spec.skill != workflow_id:
            continue
        text, _ = strip_block(text, spec)
        anchor = find_anchor(text, spec)
        insert_at = text.find(anchor) + len(anchor)
        block = '\n' + render_multica_patch_block(spec) + '\n'
        text = text[:insert_at] + block + text[insert_at:]
    return text.rstrip() + '\n'


def adapter_source_for_installed_path(adapter_root: Path, rel: str) -> Path:
    if rel.startswith(('skills/', 'agents/', 'scripts/')):
        return adapter_root / 'overlays' / rel
    raise BootstrapError(f'Unsupported installed path for Multica skill pack: {rel}')


def copy_adapter_assets(adapter_root: Path, skill_root: Path) -> dict[str, list[str]]:
    copied = {'skills': [], 'agents': [], 'scripts': []}
    for rel in installed_paths(adapter_root):
        if not rel.startswith(('skills/', 'agents/', 'scripts/')):
            continue
        src = adapter_source_for_installed_path(adapter_root, rel)
        dst = skill_root / rel
        copy_file(src, dst, executable=rel.startswith('scripts/') and src.suffix == '.py')
        copied[rel.split('/', 1)[0]].append(rel)
    return copied


def write_upstream_superpowers_docs(superpowers_source: Path, skill_root: Path) -> list[str]:
    copied = []
    upstream_dir = skill_root / 'upstream-superpowers'
    for workflow in UPSTREAM_WORKFLOWS:
        text = patched_upstream_skill(superpowers_source, workflow.workflow_id)
        dst = upstream_dir / f'{workflow.workflow_id}.md'
        write_text(dst, text)
        copied.append(dst.relative_to(skill_root).as_posix())
    return copied


@dataclass(frozen=True)
class IssueTemplateSpec:
    template_id: str
    default_title: str
    entrypoint: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    render: Callable[[BootstrapContext], str]


def target_repo_text(ctx: BootstrapContext) -> str:
    if ctx.target_repo is None:
        raise BootstrapError('--target-repo is required when rendering a Multica issue template')
    return ctx.target_repo.as_posix()


def optional_input(label: str, value: str | None) -> str:
    return f'- {label}: {value}' if value else f'- {label}: not provided'


def path_input(ctx: BootstrapContext, arg_name: str) -> str | None:
    value = getattr(ctx.args, arg_name)
    if not value:
        return None
    return Path(value).expanduser().resolve().as_posix()


def require_any_input(ctx: BootstrapContext, template_id: str, arg_names: tuple[str, ...], message: str) -> None:
    if any(getattr(ctx.args, arg_name) for arg_name in arg_names):
        return
    raise BootstrapError(f'--issue-template {template_id} requires {message}')


def common_issue_header(ctx: BootstrapContext, spec: IssueTemplateSpec) -> str:
    return f'''# {spec.default_title}

Target repo: {target_repo_text(ctx)}
Issue template: {spec.template_id}
Entrypoint: {spec.entrypoint}

Use the attached `{SKILL_NAME}` skill pack.
'''


def common_do_not(ctx: BootstrapContext) -> str:
    if ctx.args.allow_external_side_effects:
        side_effects = '- External side effects are authorized only to the extent explicitly requested in this issue; still ask before destructive operations or merging PRs.'
    else:
        side_effects = '- Do not commit, push, create or merge PRs, publish shared wiki changes, delete files, or run destructive git operations.'
    return f'''Do not:
{side_effects}
- Do not run adapter repository Python scripts directly; use the injected skill-pack supporting files when a Superpowers-compatible instruction asks for helper scripts.
- Do not treat the adapter repository as the target project unless this issue explicitly says so.
'''


def authorization_gate(ctx: BootstrapContext, action: str) -> str:
    if ctx.args.allow_external_side_effects:
        return f'Authorization: the issue creator passed --allow-external-side-effects for {action}. Confirm the exact scope before performing irreversible steps.'
    return f'Authorization gate: do not perform {action}. Prepare the result and ask the user to explicitly authorize the external side effect first.'


def render_smoke_issue_body(ctx: BootstrapContext) -> str:
    spec = ISSUE_TEMPLATES['smoke']
    return common_issue_header(ctx, spec) + f'''
Inputs:
- Target repo readability check only.

Required behavior:
1. Confirm you can read the target repo.
2. Confirm whether `.superpowers/wiki/index.md` exists.
3. Confirm whether `.shared-superpowers/wiki/index.md` exists.
4. If a wiki root exists, read only the root index and summarize the available wiki roots.
5. Post a comment with:
   - working directory observed
   - whether adapter skill pack is visible
   - whether project/shared wiki roots exist
   - recommended next Superpowers-compatible entrypoint

{common_do_not(ctx)}
Expected output:
- One issue comment summarizing the read-only smoke result.

Handoff / next step:
- Recommend the next issue template to use for the user's actual Superpowers-compatible flow.

This is a smoke task for Multica daemon + Claude Code + superpower-adapter skill injection.
'''


def render_lanhu_intake_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'lanhu-intake', ('lanhu_url', 'requirements_path'), '--lanhu-url or --requirements-path')
    spec = ISSUE_TEMPLATES['lanhu-intake']
    return common_issue_header(ctx, spec) + f'''
Inputs:
- Lanhu URL: {ctx.args.lanhu_url or 'not provided'}
{optional_input('Requirements path', path_input(ctx, 'requirements_path'))}

Required behavior:
1. Follow `skills/lanhu-requirements/SKILL.md` from the attached skill pack.
2. Extract only Lanhu/source requirements evidence and organize it into the adapter's PRD/evidence package style.
3. If screenshots or design assets are present, analyze only images with real evidence value.
4. Stop after requirements intake; do not proceed to brainstorming, planning, or implementation.

{common_do_not(ctx)}
Expected output:
- A requirements/evidence package location or a concise issue comment explaining what was captured.
- Open questions for missing product/design details.

Handoff / next step:
- Use `brainstorming` after the user confirms the intake result.
'''


def render_brainstorming_issue_body(ctx: BootstrapContext) -> str:
    spec = ISSUE_TEMPLATES['brainstorming']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Requirements path', path_input(ctx, 'requirements_path'))}
{optional_input('Spec path', path_input(ctx, 'spec_path'))}

Required behavior:
1. Follow `upstream-superpowers/brainstorming.md` from the attached skill pack.
2. Use `agents/wiki-researcher.md` only for lightweight project/shared wiki disclosure relevant to the task.
3. Keep exploration bounded to the user's task and the issue inputs.
4. Produce brainstorming output and explicit open questions; do not write an implementation plan yet.

{common_do_not(ctx)}
Expected output:
- Brainstorming summary, key decisions/options, and unanswered questions.

Handoff / next step:
- Use `writing-plans` only after the user approves a direction/spec.
'''


def render_writing_plans_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'writing-plans', ('spec_path', 'requirements_path'), '--spec-path or --requirements-path')
    spec = ISSUE_TEMPLATES['writing-plans']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Requirements path', path_input(ctx, 'requirements_path'))}
{optional_input('Spec path', path_input(ctx, 'spec_path'))}

Required behavior:
1. Follow `upstream-superpowers/writing-plans.md` from the attached skill pack.
2. Select only the wiki pages needed for the plan and record them as `Referenced Project Wiki`.
3. Produce or update a schemaVersion 3 `.wiki-context.json` next to the plan when wiki context is used.
4. Stop after producing the plan; do not implement until the user approves it.

{common_do_not(ctx)}
Expected output:
- A plan path or issue comment containing the plan.
- The selected `Referenced Project Wiki` list and `.wiki-context.json` location when applicable.

Handoff / next step:
- Use `execute-plan` or `sdd-execution` after the user approves the plan.
'''


def render_execute_plan_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'execute-plan', ('plan_path',), '--plan-path')
    spec = ISSUE_TEMPLATES['execute-plan']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Plan path', path_input(ctx, 'plan_path'))}
{optional_input('Wiki context path', path_input(ctx, 'wiki_context_path'))}

Required behavior:
1. Follow `upstream-superpowers/executing-plans.md` from the attached skill pack.
2. Confirm the plan has been approved before editing target project files.
3. Read only the plan-selected `Referenced Project Wiki` and the provided `.wiki-context.json`; do not broaden to the entire wiki.
4. Implement the approved plan in the target repo and verify the touched behavior with appropriate local checks.
5. If the work creates durable implementation knowledge, include an `update-wiki` handoff.

{common_do_not(ctx)}
Expected output:
- Summary of files changed, verification run, and any follow-up `update-wiki` recommendation.

Handoff / next step:
- Use `update-wiki` for durable knowledge review after implementation is complete.
'''


def render_sdd_execution_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'sdd-execution', ('plan_path',), '--plan-path')
    spec = ISSUE_TEMPLATES['sdd-execution']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Plan path', path_input(ctx, 'plan_path'))}
{optional_input('Wiki context path', path_input(ctx, 'wiki_context_path'))}

Required behavior:
1. Follow `upstream-superpowers/subagent-driven-development.md` from the attached skill pack.
2. Confirm the plan has been approved before editing target project files.
3. Run the implementer/reviewer loop as Claude Code task behavior described by the skill; do not create a local adapter state machine.
4. Consume only the plan-selected wiki context and provided `.wiki-context.json`.
5. Verify the completed behavior and report reviewer findings.

{common_do_not(ctx)}
Expected output:
- Implementation summary, reviewer loop outcome, verification result, and any `update-wiki` handoff.

Handoff / next step:
- Use `update-wiki` if the SDD task produced reusable project/shared knowledge.
'''


def render_systematic_debugging_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'systematic-debugging', ('debug_evidence', 'requirements_path'), '--debug-evidence or --requirements-path')
    spec = ISSUE_TEMPLATES['systematic-debugging']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Debug evidence', ctx.args.debug_evidence)}
{optional_input('Requirements or bug report path', path_input(ctx, 'requirements_path'))}
{optional_input('Wiki context path', path_input(ctx, 'wiki_context_path'))}

Required behavior:
1. Follow `upstream-superpowers/systematic-debugging.md` from the attached skill pack.
2. Start from the provided evidence and reproduce or narrow the failure before changing code.
3. Use wiki context only when it directly explains the failing area.
4. If repeated attempts fail, stop and hand off to `break-loop` instead of thrashing.

{common_do_not(ctx)}
Expected output:
- Root-cause analysis, fix or next diagnostic step, verification result, and whether `break-loop` is needed.

Handoff / next step:
- Use `break-loop` for repeated failures or `update-wiki` for durable debugging knowledge.
'''


def render_break_loop_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'break-loop', ('debug_evidence',), '--debug-evidence')
    spec = ISSUE_TEMPLATES['break-loop']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Debug evidence', ctx.args.debug_evidence)}
{optional_input('Plan path', path_input(ctx, 'plan_path'))}

Required behavior:
1. Follow `skills/break-loop/SKILL.md` from the attached skill pack.
2. Analyze why the loop/repeated failure happened.
3. Identify missing context, wrong assumptions, insufficient tests, or wiki gaps.
4. Do not fix code in this task unless the issue explicitly changes scope after the retrospective.

{common_do_not(ctx)}
Expected output:
- A retrospective with concrete next diagnostic or planning steps.
- A list of durable knowledge candidates for `update-wiki`.

Handoff / next step:
- Use `systematic-debugging`, `writing-plans`, or `update-wiki` based on the retrospective outcome.
'''


def render_update_wiki_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'update-wiki', ('plan_path', 'requirements_path'), '--plan-path or --requirements-path describing the completed work')
    spec = ISSUE_TEMPLATES['update-wiki']
    return common_issue_header(ctx, spec) + f'''
Inputs:
{optional_input('Completed work / requirements path', path_input(ctx, 'requirements_path'))}
{optional_input('Plan path', path_input(ctx, 'plan_path'))}
{optional_input('Wiki context path', path_input(ctx, 'wiki_context_path'))}

Required behavior:
1. Follow `skills/update-wiki/SKILL.md` from the attached skill pack.
2. Review only durable implementation knowledge produced by the completed work.
3. Respect `{target_repo_text(ctx)}/.superpowers/settings.json` and `{target_repo_text(ctx)}/.shared-superpowers/settings.json`.
4. Keep shared wiki content neutral and portable.
5. Ask before creating new wiki documents unless settings already authorize it.

{common_do_not(ctx)}
Expected output:
- Wiki update decision: skipped, proposed, or updated.
- Exact wiki files considered and rationale.

Handoff / next step:
- If shared wiki changes are publish-ready, use `publish-shared-wiki` or `shared-wiki-mcp-pr`.
'''


def render_publish_shared_wiki_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'publish-shared-wiki', ('shared_wiki_topic',), '--shared-wiki-topic')
    spec = ISSUE_TEMPLATES['publish-shared-wiki']
    return common_issue_header(ctx, spec) + f'''
Inputs:
- Shared wiki topic: {ctx.args.shared_wiki_topic}
{optional_input('Wiki context path', path_input(ctx, 'wiki_context_path'))}

Required behavior:
1. Follow `skills/publish-shared-wiki/SKILL.md` from the attached skill pack.
2. Re-check shared wiki neutrality before publishing.
3. Confirm the target shared wiki settings authorize the requested publication path.
4. {authorization_gate(ctx, 'shared wiki publication')}

{common_do_not(ctx)}
Expected output:
- Publication readiness report, files/topics involved, and any blocked neutrality terms.

Handoff / next step:
- If GitHub-backed PR flow is needed, use `shared-wiki-mcp-pr`.
'''


def render_shared_wiki_mcp_pr_issue_body(ctx: BootstrapContext) -> str:
    require_any_input(ctx, 'shared-wiki-mcp-pr', ('shared_wiki_topic',), '--shared-wiki-topic')
    spec = ISSUE_TEMPLATES['shared-wiki-mcp-pr']
    return common_issue_header(ctx, spec) + f'''
Inputs:
- Shared wiki topic: {ctx.args.shared_wiki_topic}
{optional_input('Requirements path', path_input(ctx, 'requirements_path'))}

Required behavior:
1. Follow `skills/shared-wiki-mcp/SKILL.md` from the attached skill pack.
2. Prepare a GitHub-backed shared wiki PR path only if MCP access and user authorization are available.
3. Re-check shared wiki neutrality before preparing PR content.
4. {authorization_gate(ctx, 'shared wiki PR creation')}
5. Do not merge PRs.

{common_do_not(ctx)}
Expected output:
- PR readiness report or created PR reference, depending on authorization and tool availability.
- Explicit note that merge remains a human decision.

Handoff / next step:
- Human review/merge outside this bootstrap command.
'''


ISSUE_TEMPLATES: dict[str, IssueTemplateSpec] = {
    'smoke': IssueTemplateSpec('smoke', 'Superpowers+adapter Multica smoke', 'skills/superpowers-adapter/SKILL.md', (), (), render_smoke_issue_body),
    'lanhu-intake': IssueTemplateSpec('lanhu-intake', 'Superpowers+adapter Lanhu intake', 'skills/lanhu-requirements/SKILL.md', ('lanhu-url or requirements-path',), ('target-repo',), render_lanhu_intake_issue_body),
    'brainstorming': IssueTemplateSpec('brainstorming', 'Superpowers brainstorming', 'upstream-superpowers/brainstorming.md', (), ('requirements-path', 'spec-path'), render_brainstorming_issue_body),
    'writing-plans': IssueTemplateSpec('writing-plans', 'Superpowers writing plans', 'upstream-superpowers/writing-plans.md', ('spec-path or requirements-path',), ('wiki-context-path',), render_writing_plans_issue_body),
    'execute-plan': IssueTemplateSpec('execute-plan', 'Superpowers execute plan', 'upstream-superpowers/executing-plans.md', ('plan-path',), ('wiki-context-path',), render_execute_plan_issue_body),
    'sdd-execution': IssueTemplateSpec('sdd-execution', 'Superpowers SDD execution', 'upstream-superpowers/subagent-driven-development.md', ('plan-path',), ('wiki-context-path',), render_sdd_execution_issue_body),
    'systematic-debugging': IssueTemplateSpec('systematic-debugging', 'Superpowers systematic debugging', 'upstream-superpowers/systematic-debugging.md', ('debug-evidence or requirements-path',), ('wiki-context-path',), render_systematic_debugging_issue_body),
    'break-loop': IssueTemplateSpec('break-loop', 'Superpowers break-loop retrospective', 'skills/break-loop/SKILL.md', ('debug-evidence',), ('plan-path',), render_break_loop_issue_body),
    'update-wiki': IssueTemplateSpec('update-wiki', 'Superpowers update-wiki review', 'skills/update-wiki/SKILL.md', ('plan-path or requirements-path',), ('wiki-context-path',), render_update_wiki_issue_body),
    'publish-shared-wiki': IssueTemplateSpec('publish-shared-wiki', 'Superpowers shared wiki publish', 'skills/publish-shared-wiki/SKILL.md', ('shared-wiki-topic',), ('wiki-context-path',), render_publish_shared_wiki_issue_body),
    'shared-wiki-mcp-pr': IssueTemplateSpec('shared-wiki-mcp-pr', 'Superpowers shared wiki MCP PR', 'skills/shared-wiki-mcp/SKILL.md', ('shared-wiki-topic',), ('requirements-path',), render_shared_wiki_mcp_pr_issue_body),
}


def issue_template_choices() -> tuple[str, ...]:
    return tuple(ISSUE_TEMPLATES)


def selected_issue_template(ctx: BootstrapContext) -> IssueTemplateSpec:
    try:
        return ISSUE_TEMPLATES[ctx.args.issue_template]
    except KeyError as exc:
        raise BootstrapError(f'Unknown issue template: {ctx.args.issue_template}') from exc


def render_issue_template_body(ctx: BootstrapContext) -> str:
    return selected_issue_template(ctx).render(ctx)


def issue_template_route_summary() -> str:
    return '\n'.join(
        f'- `{spec.template_id}` → `{spec.entrypoint}`'
        for spec in ISSUE_TEMPLATES.values()
    )


def root_skill_md(adapter_root: Path, target_repo: Path | None) -> str:
    adapter_manifest = load_manifest(adapter_root)
    target_text = target_repo.as_posix() if target_repo else '<target repo from the Multica issue>'
    return f'''---
name: {SKILL_NAME}
description: Superpowers-compatible adapter workflow pack for Multica Claude Code agents, including project/shared wiki disclosure, Lanhu intake, SDD plan execution guidance, and durable update-wiki review.
---

Generated by superpower-adapter.

# Superpowers Adapter for Multica

This workspace skill pack lets a Multica Claude Code agent run the Superpowers + adapter workflow from a real Multica issue, assignment, mention, chat task, or autopilot. The user entrypoint is the Multica task, not direct execution of adapter Python scripts.

Adapter version: `{adapter_manifest.get('version')}`. Adapted Superpowers version: `{adapter_manifest.get('adaptedSuperpowersVersion')}`.

## Runtime boundary

- Multica creates the task by assigning or mentioning the agent.
- Claude Code receives this skill pack as a workspace skill.
- The target project is the repo named in the issue body, normally `{target_text}`.
- Supporting scripts live inside this skill pack under `scripts/`. When a copied Superpowers instruction mentions `{MULTICA_SKILL_ROOT_HINT}/scripts/<name>.py`, resolve that path from the task workspace where Multica injected this skill. Do not run `scripts/<name>.py` from the target repository unless that file is part of the injected skill pack.
- Do not commit, push, open PRs, publish shared wiki changes, or perform other external side effects without explicit user authorization in the Multica issue.

## Normal Superpowers-compatible flow

1. Optional Lanhu intake: use `skills/lanhu-requirements/SKILL.md` when the issue includes a Lanhu URL and the workspace has Claude Code MCP access.
2. Brainstorming: follow `upstream-superpowers/brainstorming.md`; use `agents/wiki-researcher.md` for lightweight project/shared wiki disclosure.
3. Planning: follow `upstream-superpowers/writing-plans.md`; produce a plan and schemaVersion 3 `.wiki-context.json` under the target repo.
4. Execution: follow `upstream-superpowers/executing-plans.md` or `upstream-superpowers/subagent-driven-development.md`; consume only the plan-selected `Referenced Project Wiki` and rendered wiki-context constraints.
5. Finishing: follow `upstream-superpowers/finishing-a-development-branch.md` and ask before visible side effects.
6. Durable knowledge review: use `skills/update-wiki/SKILL.md` only when the completed work produced reusable implementation knowledge.

## Multica issue templates

The issue body is the routing surface. When it contains `Issue template: <id>`, use the matching entrypoint below and stay inside the target repo named by `Target repo:`.

{issue_template_route_summary()}

## Adapter standalone and maintenance skills

- `skills/init-wiki/SKILL.md`
- `skills/import-wiki/SKILL.md`
- `skills/migrate-wiki/SKILL.md`
- `skills/lanhu-requirements/SKILL.md`
- `skills/shared-wiki-mcp/SKILL.md`
- `skills/publish-shared-wiki/SKILL.md`
- `skills/break-loop/SKILL.md`
- `skills/update-wiki/SKILL.md`

Standalone adapter skill completion is not the same as Superpowers development-task completion. Do not claim implementation, bug fixing, verification, commit readiness, or PR readiness solely because one of these maintenance skills completed.

## Wiki roots and authorization

Project wiki writes are governed by `{target_text}/.superpowers/settings.json`. Shared wiki writes are governed by `{target_text}/.shared-superpowers/settings.json`. If settings are absent, update existing wiki pages only when the skill instructions allow it, and ask before creating new wiki documents.

Shared wiki content must stay neutral and portable. Do not write current-system identifiers, internal URLs, environment names, local paths, deployment instances, tenant names, or current-system-only business rules into shared wiki.

## First smoke task behavior

For the first Multica smoke issue, do only read-only checks: confirm the target repo is readable, whether this skill pack is visible, and whether `.superpowers/wiki/index.md` / `.shared-superpowers/wiki/index.md` exist. Post the result as an issue comment and do not edit files.
'''


def prepare_skill_pack(ctx: BootstrapContext) -> None:
    if ctx.superpowers_source is None:
        raise BootstrapError('--superpowers-source is required to prepare a Multica skill pack')
    if not (ctx.superpowers_source / 'skills').is_dir():
        raise BootstrapError(f'Superpowers source does not contain skills/: {ctx.superpowers_source}')

    reset_generated_skill_root(ctx.skill_root)
    copied = copy_adapter_assets(ctx.adapter_root, ctx.skill_root)
    upstream_docs = write_upstream_superpowers_docs(ctx.superpowers_source, ctx.skill_root)
    write_text(ctx.skill_root / 'SKILL.md', root_skill_md(ctx.adapter_root, ctx.target_repo))
    write_json(marker_path(ctx.skill_root), {
        'generatedBy': GENERATED_BY,
        'generatedAt': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'skillName': SKILL_NAME,
        'adapterRoot': ctx.adapter_root.as_posix(),
        'superpowersSource': ctx.superpowers_source.as_posix(),
        'multicaSkillRootHint': MULTICA_SKILL_ROOT_HINT,
        'copied': copied,
        'upstreamSuperpowers': upstream_docs,
    })
    ctx.add_check('skill-pack-prepared', 'passed', 'Multica workspace skill pack was generated.', path=ctx.skill_root.as_posix())


def run_process(argv: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def planned_or_run(ctx: BootstrapContext, argv: list[str], purpose: str, *, capture_issue_id: bool = False) -> subprocess.CompletedProcess[str] | None:
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
        raise BootstrapError(f'Multica command failed ({purpose}): {" ".join(argv)}\n{completed.stderr.strip()}')
    if capture_issue_id:
        ctx.issue_id = parse_issue_id(completed.stdout) or parse_issue_id(completed.stderr)
    return completed


def help_text(command: list[str]) -> str:
    if shutil.which('multica') is None:
        return ''
    completed = run_process(['multica', *command, '--help'])
    return completed.stdout + '\n' + completed.stderr if completed.returncode == 0 else ''


def has_flag(text: str, flag: str) -> bool:
    return flag in text.split() or flag in text


def first_supported_flag(text: str, flags: tuple[str, ...]) -> str | None:
    for flag in flags:
        if has_flag(text, flag):
            return flag
    return None


def parse_json_records(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ('agents', 'items', 'data', 'results'):
            values = data.get(key)
            if isinstance(values, list):
                return [item for item in values if isinstance(item, dict)]
        return [data]
    return []


def record_matches_agent(record: dict[str, Any], agent_name: str) -> bool:
    for key in ('slug', 'name', 'id', 'username'):
        value = record.get(key)
        if isinstance(value, str) and value == agent_name:
            return True
    return False


def record_matches_skill(record: dict[str, Any], skill_name: str) -> bool:
    for key in ('slug', 'name', 'id'):
        value = record.get(key)
        if isinstance(value, str) and value == skill_name:
            return True
    return False


def record_id(record: dict[str, Any]) -> str | None:
    for key in ('id', 'uuid'):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def parse_created_record_id(text: str) -> str | None:
    for record in parse_json_records(text):
        value = record_id(record)
        if value:
            return value
    return None


def find_claude_runtime_id(text: str) -> str | None:
    for record in parse_json_records(text):
        provider = str(record.get('provider', '')).lower()
        name = str(record.get('name', '')).lower()
        status = str(record.get('status', '')).lower()
        if 'claude' in provider or 'claude' in name:
            value = record_id(record)
            if value and (not status or status == 'online'):
                return value
    return None


def parse_issue_id(text: str) -> str | None:
    match = ISSUE_ID_RE.search(text)
    if match:
        return match.group(0)
    match = UUID_RE.search(text)
    if match:
        return match.group(0)
    for record in parse_json_records(text):
        for key in ('number', 'key', 'id', 'uuid'):
            value = record.get(key)
            if isinstance(value, str) and (ISSUE_ID_RE.fullmatch(value) or UUID_RE.fullmatch(value)):
                return value
        prefix = record.get('prefix')
        number = record.get('number')
        if isinstance(prefix, str) and isinstance(number, int):
            return f'{prefix}-{number}'
    return None


def observation_commands(ctx: BootstrapContext) -> list[list[str]]:
    if not ctx.apply:
        return [['multica', 'issue', 'runs', ctx.issue_id or '<created-issue-id>']]
    commands: list[list[str]] = []
    if ctx.issue_id:
        if help_text(['issue', 'runs']):
            commands.append(['multica', 'issue', 'runs', ctx.issue_id])
        elif help_text(['issue', 'status']):
            commands.append(['multica', 'issue', 'status', ctx.issue_id])
    return commands


def observe_runs(ctx: BootstrapContext) -> None:
    if not ctx.args.observe_runs:
        return
    commands = observation_commands(ctx)
    if not commands:
        ctx.add_manual_step(f'Observe the created task manually: multica issue runs {ctx.issue_id or "<issue-id>"}')
        ctx.add_check('multica-run-observation', 'warning', 'No documented issue run observation CLI surface was detected.')
        return
    deadline = time.monotonic() + ctx.args.observe_timeout_seconds
    observed_output = False
    while True:
        for argv in commands:
            if not ctx.apply:
                ctx.commands.append({'argv': argv, 'purpose': 'Observe Multica issue run after assignment.', 'executed': False})
                continue
            completed = run_process(argv)
            record = {
                'argv': argv,
                'purpose': 'Observe Multica issue run after assignment.',
                'executed': True,
                'returncode': completed.returncode,
                'stdout': completed.stdout.strip(),
                'stderr': completed.stderr.strip(),
            }
            ctx.commands.append(record)
            ctx.observations.append(record)
            observed_output = observed_output or bool(completed.stdout.strip() or completed.stderr.strip())
        if not ctx.apply:
            ctx.add_check('multica-run-observation', 'passed', 'Dry-run planned read-only Multica issue run observation commands.')
            return
        if observed_output:
            ctx.add_check('multica-run-observation', 'passed', 'Observed Multica issue run output after issue assignment.')
            return
        if time.monotonic() >= deadline:
            ctx.add_check('multica-run-observation', 'warning', 'No Multica issue run output appeared before the observation timeout.')
            return
        time.sleep(ctx.args.observe_interval_seconds)


def preflight(ctx: BootstrapContext) -> None:
    multica_path = shutil.which('multica')
    if multica_path:
        ctx.add_check('multica-cli', 'passed', 'Multica CLI is installed.', path=multica_path)
    elif ctx.apply:
        ctx.add_check('multica-cli', 'blocked', 'Multica CLI is not installed; install it before using --apply.')
        return
    else:
        ctx.add_check('multica-cli', 'warning', 'Multica CLI is not installed; dry-run will only generate the skill pack and command plan.')
        ctx.commands.extend([
            {'argv': ['multica', 'auth', 'status'], 'purpose': 'Check Multica login status.', 'executed': False},
            {'argv': ['multica', 'daemon', 'status'], 'purpose': 'Check Multica daemon status.', 'executed': False},
            {'argv': ['multica', 'runtime', 'list'], 'purpose': 'Check available Multica runtimes.', 'executed': False},
        ])
        return

    for argv, check_id, message in (
        (['multica', 'auth', 'status'], 'multica-auth', 'Multica authentication status checked.'),
        (['multica', 'daemon', 'status'], 'multica-daemon', 'Multica daemon status checked.'),
        (['multica', 'runtime', 'list', '--output', 'json'], 'multica-runtime', 'Multica runtime list checked.'),
    ):
        if not ctx.apply:
            ctx.commands.append({'argv': argv, 'purpose': message, 'executed': False})
            continue
        completed = run_process(argv)
        ctx.commands.append({
            'argv': argv,
            'purpose': message,
            'executed': True,
            'returncode': completed.returncode,
            'stdout': completed.stdout.strip(),
            'stderr': completed.stderr.strip(),
        })
        if completed.returncode == 0:
            ctx.add_check(check_id, 'passed', message)
        else:
            ctx.add_check(check_id, 'blocked', f'{message} Command failed.', stderr=completed.stderr.strip())

        if check_id == 'multica-runtime' and completed.returncode == 0 and ctx.args.provider == 'claude':
            runtime_text = completed.stdout + completed.stderr
            ctx.runtime_id = find_claude_runtime_id(runtime_text)
            if ctx.runtime_id or 'claude' in runtime_text.lower():
                ctx.add_check('multica-claude-runtime', 'passed', 'A Claude runtime appears in Multica runtime output.', runtimeId=ctx.runtime_id)
            else:
                ctx.add_check('multica-claude-runtime', 'blocked', 'No Claude runtime appears in Multica runtime output; start a daemon with Claude Code available.')


def lookup_skill(ctx: BootstrapContext) -> str | None:
    completed = run_process(['multica', 'skill', 'list', '--output', 'json'])
    ctx.commands.append({
        'argv': ['multica', 'skill', 'list', '--output', 'json'],
        'purpose': 'Look up existing Multica skills.',
        'executed': True,
        'returncode': completed.returncode,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
    })
    if completed.returncode != 0:
        return None
    for record in parse_json_records(completed.stdout):
        if record_matches_skill(record, SKILL_NAME):
            return record_id(record)
    return None


def skill_files(skill_root: Path) -> list[Path]:
    return sorted(path for path in skill_root.rglob('*') if path.is_file() and path.name != marker_path(skill_root).name)


def import_skills(ctx: BootstrapContext) -> None:
    create_help = help_text(['skill', 'create'])
    update_help = help_text(['skill', 'update'])
    files_help = help_text(['skill', 'files', 'upsert'])
    if ctx.apply and not create_help:
        ctx.add_manual_step(f'Create or update the `{SKILL_NAME}` skill in Multica UI/CLI, then upload files from {ctx.skill_root.as_posix()}')
        raise BootstrapError('Cannot inspect `multica skill create --help`; refusing to guess skill creation flags.')

    root_md = (ctx.skill_root / 'SKILL.md').read_text(encoding='utf-8')
    existing_id = lookup_skill(ctx) if ctx.apply else None
    if existing_id:
        ctx.skill_id = existing_id
        if not ctx.args.update_skill:
            ctx.add_check('multica-skill', 'passed', 'Multica skill already exists; leaving uploaded skill files unchanged.', skillId=existing_id)
            return
        cmd = ['multica', 'skill', 'update', existing_id]
        if update_help and has_flag(update_help, '--name'):
            cmd.extend(['--name', SKILL_NAME])
        if update_help and has_flag(update_help, '--content'):
            cmd.extend(['--content', root_md])
        if update_help and has_flag(update_help, '--description'):
            cmd.extend(['--description', 'Superpowers-compatible adapter workflow pack for Multica Claude Code agents.'])
        planned_or_run(ctx, cmd, 'Update the generated superpowers-adapter workspace skill.')
    else:
        cmd = ['multica', 'skill', 'create', '--name', SKILL_NAME]
        if create_help and has_flag(create_help, '--content'):
            cmd.extend(['--content', root_md])
        if create_help and has_flag(create_help, '--description'):
            cmd.extend(['--description', 'Superpowers-compatible adapter workflow pack for Multica Claude Code agents.'])
        completed = planned_or_run(ctx, cmd, 'Create the generated superpowers-adapter workspace skill.')
        if completed is not None:
            ctx.skill_id = parse_created_record_id(completed.stdout) or parse_created_record_id(completed.stderr)
        if not ctx.apply:
            ctx.skill_id = '<created-skill-id>'

    if ctx.apply and not ctx.skill_id:
        raise BootstrapError('Skill id could not be resolved after create/update; cannot upload skill files or attach skill.')
    skill_id = ctx.skill_id or '<created-skill-id>'
    if ctx.apply and not files_help:
        ctx.add_manual_step(f'Upload generated skill files from {ctx.skill_root.as_posix()} to skill {skill_id}.')
        raise BootstrapError('Cannot inspect `multica skill files upsert --help`; refusing to guess skill file upload flags.')
    for path in skill_files(ctx.skill_root):
        rel = path.relative_to(ctx.skill_root).as_posix()
        content = path.read_text(encoding='utf-8')
        planned_or_run(ctx, ['multica', 'skill', 'files', 'upsert', skill_id, '--path', rel, '--content', content], f'Upload skill file {rel}.')


def agent_system_instructions(ctx: BootstrapContext) -> str:
    target_repo = ctx.target_repo.as_posix() if ctx.target_repo else '<target repo from issue body>'
    return f'''Use the `{SKILL_NAME}` workspace skill pack when an issue asks for Superpowers, adapter, project wiki, shared wiki, Lanhu, update-wiki, or debugging-retrospective flows.

For target project work, operate in the target repo named by the issue body, normally `{target_repo}`. Do not treat the adapter repository as the business project unless the issue explicitly asks to maintain the adapter itself.

Do not directly run adapter repository scripts. Adapter Python files are skill supporting files; run the injected skill-pack copy when a Superpowers-compatible instruction asks for a helper script.

Treat the Multica issue body as the routing surface. If it contains `Issue template: <id>`, follow the matching entrypoint from the attached skill pack instead of inventing a local workflow.

Ask before commit, push, PR creation, shared wiki publish, deleting files, destructive git operations, or other external visible side effects.
'''


def agent_exists(ctx: BootstrapContext) -> bool:
    if not ctx.apply:
        ctx.agent_exists = None
        return False
    completed = run_process(['multica', 'agent', 'list', '--output', 'json'])
    ctx.commands.append({
        'argv': ['multica', 'agent', 'list', '--output', 'json'],
        'purpose': 'Look up existing Multica agents.',
        'executed': True,
        'returncode': completed.returncode,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
    })
    if completed.returncode != 0:
        ctx.add_manual_step(f'Check whether the agent already exists: multica agent get {ctx.args.agent_name}')
        ctx.agent_exists = None
        return False
    matching = next((record for record in parse_json_records(completed.stdout) if record_matches_agent(record, ctx.args.agent_name)), None)
    ctx.agent_id = record_id(matching) if matching else None
    exists = matching is not None
    ctx.agent_exists = exists
    return exists


def ensure_agent(ctx: BootstrapContext) -> None:
    create_help = help_text(['agent', 'create'])
    update_help = help_text(['agent', 'update'])
    exists = agent_exists(ctx) if ctx.apply else False
    if exists and not ctx.args.update_agent:
        ctx.add_check('multica-agent', 'passed', 'Multica agent already exists; leaving configuration unchanged.', agent=ctx.args.agent_name)
        return

    instructions = agent_system_instructions(ctx)
    if exists:
        if ctx.apply and not update_help:
            ctx.add_manual_step(f'Update agent instructions manually if needed: multica agent update {ctx.args.agent_name} ...')
            return
        cmd = ['multica', 'agent', 'update', ctx.args.agent_name]
        instructions_flag = first_supported_flag(update_help, ('--instructions', '--system-instructions', '--context')) if update_help else '--instructions'
        if instructions_flag:
            cmd.extend([instructions_flag, instructions])
        planned_or_run(ctx, cmd, 'Update the existing Multica compatibility agent instructions.')
        ctx.add_check('multica-agent', 'passed', 'Multica agent update was planned or executed.', agent=ctx.args.agent_name)
        return

    if ctx.apply and not create_help:
        ctx.add_manual_step(f'Create a Claude Code agent named {ctx.args.agent_name} in Multica, then attach the {SKILL_NAME} skill.')
        raise BootstrapError('Cannot inspect `multica agent create --help`; refusing to guess create flags.')

    name_flag = first_supported_flag(create_help, ('--name',)) if create_help else '--name'
    runtime_flag = first_supported_flag(create_help, ('--runtime-id',)) if create_help else None
    provider_flag = first_supported_flag(create_help, ('--provider', '--runtime', '--tool')) if create_help else '--provider'
    if ctx.apply and not name_flag:
        ctx.add_manual_step(f'Create a Claude Code agent named {ctx.args.agent_name} in Multica UI or with `multica agent create --help` guidance.')
        raise BootstrapError('Could not find supported agent create name flag.')
    if ctx.apply and runtime_flag and not ctx.runtime_id:
        raise BootstrapError('Claude runtime id could not be resolved from `multica runtime list --output json`; cannot create agent with current CLI.')

    cmd = ['multica', 'agent', 'create']
    if name_flag:
        cmd.extend([name_flag, ctx.args.agent_name])
    if runtime_flag:
        cmd.extend([runtime_flag, ctx.runtime_id or '<claude-runtime-id>'])
    elif provider_flag:
        cmd.extend([provider_flag, ctx.args.provider])
    instructions_flag = first_supported_flag(create_help, ('--instructions', '--system-instructions', '--context')) if create_help else '--instructions'
    if instructions_flag:
        cmd.extend([instructions_flag, instructions])
    if ctx.args.model:
        model_flag = first_supported_flag(create_help, ('--model',)) if create_help else '--model'
        if model_flag:
            cmd.extend([model_flag, ctx.args.model])
    visibility_flag = first_supported_flag(create_help, ('--visibility',)) if create_help else None
    if visibility_flag:
        cmd.extend([visibility_flag, 'workspace'])

    completed = planned_or_run(ctx, cmd, 'Create the Multica Claude Code compatibility agent.')
    if completed is not None:
        ctx.agent_id = parse_created_record_id(completed.stdout) or parse_created_record_id(completed.stderr)
    ctx.add_check('multica-agent', 'passed', 'Multica agent creation was planned or executed.', agent=ctx.args.agent_name, agentId=ctx.agent_id)


def attach_skills(ctx: BootstrapContext) -> None:
    set_help = help_text(['agent', 'skills', 'set'])
    if ctx.apply and not set_help:
        ctx.add_manual_step(f'Attach workspace skill `{SKILL_NAME}` to agent `{ctx.args.agent_name}` in Multica UI or CLI.')
        raise BootstrapError('Cannot inspect `multica agent skills set --help`; refusing to guess attach command.')
    agent_ref = ctx.agent_id or ctx.args.agent_name
    skill_ref = ctx.skill_id or SKILL_NAME
    if not ctx.apply:
        planned_or_run(ctx, ['multica', 'agent', 'skills', 'set', agent_ref, '--skill-ids', skill_ref], 'Attach the superpowers-adapter skill to the compatibility agent.')
        return
    if not ctx.agent_id:
        raise BootstrapError('Agent id could not be resolved; current Multica CLI requires agent id for skill assignment.')
    if not ctx.skill_id:
        raise BootstrapError('Skill id could not be resolved; current Multica CLI requires skill id for skill assignment.')
    planned_or_run(ctx, ['multica', 'agent', 'skills', 'set', ctx.agent_id, '--skill-ids', ctx.skill_id], 'Attach the superpowers-adapter skill to the compatibility agent.')


def issue_body_from_args(ctx: BootstrapContext) -> str:
    if ctx.args.issue_body_file:
        return Path(ctx.args.issue_body_file).expanduser().resolve().read_text(encoding='utf-8')
    if ctx.args.issue_body:
        return ctx.args.issue_body
    return render_issue_template_body(ctx)


def issue_title(ctx: BootstrapContext) -> str:
    return ctx.args.issue_title or selected_issue_template(ctx).default_title


def create_issue(ctx: BootstrapContext) -> None:
    body = issue_body_from_args(ctx)
    create_help = help_text(['issue', 'create'])
    template = selected_issue_template(ctx)
    cmd = ['multica', 'issue', 'create', '--title', issue_title(ctx)]
    body_flag = first_supported_flag(create_help, ('--description', '--body')) if create_help else '--description'
    if not body_flag and not ctx.apply:
        body_flag = '--description'
    if body_flag:
        cmd.extend([body_flag, body])
    elif ctx.apply:
        ctx.add_manual_step('Create the issue body manually before assignment; this Multica CLI did not expose --description or --body in help output.')
        raise BootstrapError('Cannot create a useful Multica issue because no issue body flag was detected.')
    if create_help and has_flag(create_help, '--output'):
        cmd.extend(['--output', 'json'])
    planned_or_run(ctx, cmd, f'Create a Multica {template.template_id} issue for the Superpowers+adapter flow.', capture_issue_id=True)
    if not ctx.apply:
        ctx.issue_id = '<created-issue-id>'


def assign_issue(ctx: BootstrapContext) -> None:
    if not ctx.issue_id:
        ctx.add_manual_step(f'Assign the created issue to the agent manually: multica issue assign <issue-id> --to {ctx.args.agent_name}')
        if ctx.apply:
            raise BootstrapError('Issue id could not be parsed from `multica issue create` output.')
    issue_id = ctx.issue_id or '<created-issue-id>'
    planned_or_run(ctx, ['multica', 'issue', 'assign', issue_id, '--to', ctx.args.agent_name], 'Assign the Multica issue to the compatibility agent and trigger a real task.')


def resolve_context(args: argparse.Namespace) -> BootstrapContext:
    adapter_root = Path(args.adapter_root).expanduser().resolve()
    if not (adapter_root / 'manifest.json').is_file():
        raise BootstrapError(f'Missing adapter manifest in {adapter_root}')
    superpowers_source = Path(args.superpowers_source).expanduser().resolve() if args.superpowers_source else None
    target_repo = Path(args.target_repo).expanduser().resolve() if args.target_repo else None
    if target_repo and not target_repo.is_dir():
        raise BootstrapError(f'Missing target repo: {target_repo}')
    skill_pack_dir = Path(args.skill_pack_dir).expanduser().resolve() if args.skill_pack_dir else adapter_root / 'dist' / 'multica-skill-pack'
    skill_root = skill_pack_dir / SKILL_NAME
    return BootstrapContext(args, adapter_root, superpowers_source, target_repo, skill_pack_dir, skill_root)


def run_command(ctx: BootstrapContext) -> None:
    command = ctx.args.command
    if command in {'prepare-skill-pack', 'import-skills', 'bootstrap'}:
        prepare_skill_pack(ctx)
    if command in {'preflight', 'import-skills', 'ensure-agent', 'attach-skills', 'create-issue', 'assign-issue', 'bootstrap'}:
        preflight(ctx)
    if any(check.status == 'blocked' for check in ctx.checks) and ctx.apply:
        raise BootstrapError('Multica preflight failed; fix blocked checks before using --apply.')

    if command == 'preflight':
        return
    if command == 'prepare-skill-pack':
        return
    if command in {'import-skills', 'bootstrap'}:
        import_skills(ctx)
    if command in {'ensure-agent', 'bootstrap'}:
        ensure_agent(ctx)
    if command in {'attach-skills', 'bootstrap'}:
        attach_skills(ctx)
    if command in {'create-issue', 'bootstrap'}:
        create_issue(ctx)
    if command in {'assign-issue', 'bootstrap'}:
        assign_issue(ctx)
    if command in {'assign-issue', 'bootstrap'}:
        observe_runs(ctx)


def print_text_summary(ctx: BootstrapContext) -> None:
    data = ctx.as_dict()
    print(f'Multica bootstrap status: {data["status"]}')
    print(f'Skill pack: {ctx.skill_root}')
    for check in ctx.checks:
        print(f'- {check.status}: {check.id} — {check.message}')
    if ctx.commands:
        print('Commands:')
        for record in ctx.commands:
            prefix = 'ran' if record.get('executed') else 'planned'
            print(f'- {prefix}: {" ".join(record["argv"])}')
    if ctx.manual_steps:
        print('Manual steps:')
        for step in ctx.manual_steps:
            print(f'- {step}')
    if ctx.issue_id:
        print(f'Issue: {ctx.issue_id}')
        print(f'Check runs: multica issue runs {ctx.issue_id}')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='bootstrap', choices=(
        'preflight',
        'prepare-skill-pack',
        'import-skills',
        'ensure-agent',
        'attach-skills',
        'create-issue',
        'assign-issue',
        'bootstrap',
    ))
    parser.add_argument('--adapter-root', default=Path(__file__).resolve().parents[1].as_posix())
    parser.add_argument('--superpowers-source')
    parser.add_argument('--target-repo')
    parser.add_argument('--skill-pack-dir')
    parser.add_argument('--agent-name', default=DEFAULT_AGENT_NAME)
    parser.add_argument('--provider', default=DEFAULT_PROVIDER)
    parser.add_argument('--model')
    parser.add_argument('--issue-template', default='smoke', choices=issue_template_choices())
    parser.add_argument('--issue-title')
    parser.add_argument('--issue-body')
    parser.add_argument('--issue-body-file')
    parser.add_argument('--lanhu-url')
    parser.add_argument('--requirements-path')
    parser.add_argument('--spec-path')
    parser.add_argument('--plan-path')
    parser.add_argument('--wiki-context-path')
    parser.add_argument('--debug-evidence')
    parser.add_argument('--shared-wiki-topic')
    parser.add_argument('--allow-external-side-effects', action='store_true')
    parser.add_argument('--observe-runs', action='store_true', help='After issue assignment, observe Multica issue runs using documented read-only CLI surfaces when available.')
    parser.add_argument('--observe-timeout-seconds', type=int, default=60)
    parser.add_argument('--observe-interval-seconds', type=int, default=5)
    parser.add_argument('--update-skill', action='store_true', help='Update an existing Multica skill and re-upload files. Without this, existing skills are reused.')
    parser.add_argument('--update-agent', action='store_true')
    parser.add_argument('--apply', action='store_true', help='Execute external Multica workspace actions. Without this flag, only dry-run command planning is produced.')
    parser.add_argument('--dry-run', action='store_true', help='Explicitly keep external Multica workspace actions as planned commands.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        raise BootstrapError('Use either --apply or --dry-run, not both.')
    if args.agent_name == REMOVED_AGENT_NAME:
        raise BootstrapError(f'{REMOVED_AGENT_NAME} has been removed. Use role agents, superpowers-runtime-squad, or {DEFAULT_AGENT_NAME} for compatibility smoke only.')
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        ctx = resolve_context(args)
    except BootstrapError as exc:
        if '--json' in argv:
            print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f'Error: {exc}', file=sys.stderr)
        return 1
    try:
        run_command(ctx)
    except BootstrapError as exc:
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
