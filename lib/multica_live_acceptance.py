#!/usr/bin/env python3
"""Plan or run Multica-visible Superpowers+adapter role-agent acceptance chains."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ISSUE_ID_RE = re.compile(r'\b[A-Z][A-Z0-9]+-\d+\b')
UUID_RE = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
SKILL_NAME = 'superpowers-adapter'
SQUAD_NAME = 'superpowers-runtime-squad'
ORCHESTRATOR_AGENT = 'superpowers-adapter-orchestrator'

ROLE_AGENTS = {
    'lanhu-frontend': 'superpowers-lanhu-frontend-requirements-analyst',
    'lanhu-frontend-html': 'superpowers-lanhu-frontend-html-requirements-analyst',
    'lanhu-backend': 'superpowers-lanhu-backend-requirements-analyst',
    'brainstorming': 'superpowers-brainstorming-agent',
    'wiki-researcher': 'superpowers-wiki-researcher',
    'planning': 'superpowers-planning-agent',
    'spec-document-reviewer': 'superpowers-spec-document-reviewer',
    'plan-document-reviewer': 'superpowers-plan-document-reviewer',
    'implementer': 'superpowers-implementer',
    'spec-reviewer': 'superpowers-spec-compliance-reviewer',
    'quality-reviewer': 'superpowers-code-quality-reviewer',
    'code-reviewer': 'superpowers-code-reviewer',
    'debugger': 'superpowers-debugger',
    'break-loop': 'superpowers-break-loop-analyst',
    'wiki-curator': 'superpowers-wiki-curator',
    'finisher': 'superpowers-finisher',
    'shared-wiki-publisher': 'superpowers-shared-wiki-publisher',
    'orchestrator': 'superpowers-superpowers-orchestrator',
}


class AcceptanceError(SystemExit):
    pass


@dataclass(frozen=True)
class Stage:
    stage_id: str
    title: str
    assignee: str
    issue_template: str
    entrypoint: str
    required_behavior: tuple[str, ...]
    expected_output: tuple[str, ...]
    handoff: str
    upstream: tuple[str, ...] = ()
    required_args: tuple[str, ...] = ()
    optional_args: tuple[str, ...] = ()
    action: str = 'create-assign'
    target_stage_id: str | None = None


@dataclass(frozen=True)
class VisualCase:
    case_id: str
    title: str
    description: str
    stages: tuple[Stage, ...]
    required_args: tuple[str, ...] = ()


@dataclass
class AcceptanceContext:
    args: argparse.Namespace
    adapter_root: Path
    target_repo: Path
    commands: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)
    issue_ids: dict[str, str] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))

    @property
    def apply(self) -> bool:
        return bool(self.args.apply)

    def as_dict(self) -> dict[str, Any]:
        status = 'blocked' if any(check.get('status') == 'blocked' for check in self.checks) else 'ok'
        if not self.apply and status == 'ok':
            status = 'planned'
        return {
            'status': status,
            'apply': self.apply,
            'adapterRoot': self.adapter_root.as_posix(),
            'targetRepo': self.target_repo.as_posix(),
            'selected': self.args.case,
            'runId': self.run_id,
            'cases': self.cases,
            'issueIds': self.issue_ids,
            'checks': self.checks,
            'commands': self.commands,
        }


def main_stage(case_id: str, title: str) -> Stage:
    return Stage(
        f'{case_id}0',
        f'{title} main workflow',
        SQUAD_NAME,
        'visual-workflow',
        'multica/squad-dispatch',
        (
            'Create a visible workflow coordination run for this acceptance chain.',
            'Do not execute downstream Superpowers stages inside this single run.',
            'Confirm each downstream stage is represented by its own issue assigned to the listed role agent.',
        ),
        ('Workflow issue comment listing stage issues and expected handoffs.',),
        'Stage issues below are the executable work; this issue is only the coordination anchor.',
    )


VISUAL_CASES: dict[str, VisualCase] = {
    'A': VisualCase(
        'A',
        'Wiki-aware feature development main chain',
        'Validate wiki research, brainstorming, planning, implementation, reviewer fanout, final review, and update-wiki as separate Multica role-agent runs.',
        (
            main_stage('A', 'Wiki-aware feature development'),
            Stage('A1', 'Spec-context wiki research', ROLE_AGENTS['wiki-researcher'], 'wiki-research', 'agents/wiki-researcher.md', ('Select lightweight wiki context for the requested spec.', 'Post selected pages and constraints; do not write a plan.'), ('Wiki context summary for A2.',), 'A2 consumes this issue comment.', optional_args=('requirements_path', 'spec_path')),
            Stage('A2', 'Spec brainstorming discussion', ROLE_AGENTS['brainstorming'], 'brainstorming', 'upstream-superpowers/brainstorming.md', ('Discuss the feature direction using A1 context.', 'Ask open questions and stop before planning.'), ('Approved or pending brainstorming direction.',), 'A2r reviews the produced spec before planning.', upstream=('A1',), optional_args=('requirements_path', 'spec_path')),
            Stage('A2r', 'Spec document review', ROLE_AGENTS['spec-document-reviewer'], 'spec-document-review', 'skills/brainstorming/spec-document-reviewer-prompt.md', ('Review the brainstorming/spec document before planning begins.', 'Request clarification if the spec is ambiguous, internally inconsistent, or not user-approved.'), ('Spec document review pass/fail finding.',), 'A3/A4 use only a reviewed and user-approved spec.', upstream=('A2',), optional_args=('requirements_path', 'spec_path')),
            Stage('A3', 'Plan-context wiki research', ROLE_AGENTS['wiki-researcher'], 'wiki-research', 'agents/wiki-researcher.md', ('Select wiki pages needed for planning.', 'Keep disclosure bounded to the approved direction.'), ('Plan-ready wiki context candidates.',), 'A4 records the selected wiki in the plan.', upstream=('A2r',), optional_args=('requirements_path', 'spec_path')),
            Stage('A4', 'Write implementation plan', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Create an approved-plan candidate.', 'Include `Referenced Project Wiki`.', 'Generate schemaVersion 3 `.wiki-context.json`.'), ('Plan path/comment and `.wiki-context.json` path.',), 'A4r reviews the plan document before implementation.', upstream=('A2r', 'A3'), required_args=('requirements_path',), optional_args=('spec_path', 'wiki_context_path')),
            Stage('A4r', 'Plan document review', ROLE_AGENTS['plan-document-reviewer'], 'plan-document-review', 'skills/writing-plans/plan-document-reviewer-prompt.md', ('Review the implementation plan and selected wiki context before execution.', 'Block implementation if tasks, acceptance criteria, or wiki references are incomplete.'), ('Plan document review pass/fail finding.',), 'A5 can only start after user approval of this reviewed plan.', upstream=('A4',), optional_args=('plan_path', 'wiki_context_path')),
            Stage('A5', 'Implement approved plan', ROLE_AGENTS['implementer'], 'execute-plan', 'upstream-superpowers/executing-plans.md', ('Consume only A4 plan and `.wiki-context.json`.', 'Implement in the target repo and run local verification.', 'Report changed files and verification.'), ('Implementation summary and verification result.',), 'A6/A7 review this implementation.', upstream=('A4r',), optional_args=('plan_path', 'wiki_context_path')),
            Stage('A6', 'Spec compliance review', ROLE_AGENTS['spec-reviewer'], 'spec-compliance-review', 'agents/spec-compliance-reviewer.md', ('Review implementation against the approved plan/spec.', 'Request changes on mismatch; do not continue silently.'), ('Pass/fail review finding.',), 'A5 fixes failures; A8 waits for pass.', upstream=('A5',), optional_args=('plan_path', 'spec_path')),
            Stage('A7', 'Code quality review', ROLE_AGENTS['quality-reviewer'], 'code-quality-review', 'agents/code-quality-reviewer.md', ('Review maintainability, security, and test quality.', 'Request changes on actionable issues.'), ('Pass/fail review finding.',), 'A5 fixes failures; A8 waits for pass.', upstream=('A5',), optional_args=('plan_path',)),
            Stage('A8', 'Final code review', ROLE_AGENTS['code-reviewer'], 'final-code-review', 'agents/code-reviewer.md', ('Perform final review after A6/A7 pass.', 'Do not approve release side effects.'), ('Final review decision.',), 'A9 runs only after final review passes.', upstream=('A6', 'A7'), optional_args=('plan_path',)),
            Stage('A9', 'Finish development branch', ROLE_AGENTS['finisher'], 'finishing-a-development-branch', 'upstream-superpowers/finishing-a-development-branch.md', ('Run finishing-a-development-branch readiness after final review.', 'Ask before commit, push, PR creation, branch merge, or destructive git/worktree operations.'), ('Finishing readiness report and requested user authorization gates.',), 'A10 runs after finishing readiness is reported.', upstream=('A8',), optional_args=('plan_path',)),
            Stage('A10', 'Update wiki review', ROLE_AGENTS['wiki-curator'], 'update-wiki', 'skills/update-wiki/SKILL.md', ('Decide whether durable implementation knowledge should update project/shared wiki.', 'May skip, but must report the decision.'), ('Wiki update decision and files considered.',), 'Chain A complete after this independent run.', upstream=('A9',), optional_args=('plan_path', 'wiki_context_path')),
        ),
        required_args=('requirements_path',),
    ),
    'B': VisualCase(
        'B',
        'Lanhu intake to Superpowers main chain',
        'Validate Lanhu evidence-package intake then downstream Superpowers roles without Lanhu or adapter orchestrator taking over later stages.',
        (
            Stage('B1', 'Lanhu frontend intake', ROLE_AGENTS['lanhu-frontend'], 'lanhu-intake', 'skills/lanhu-requirements/SKILL.md', ('Extract source requirement evidence.', 'If role is missing, block and ask for `Role: frontend|backend`.', 'Stop after PRD/evidence package.'), ('.lanhu/.../index.md and prd.md or blocked-input report.',), 'B2 reruns this same role if user adds missing evidence.', required_args=('requirements_path',), optional_args=('lanhu_url',)),
            Stage('B2', 'Lanhu evidence confirmation rerun', ROLE_AGENTS['lanhu-frontend'], 'lanhu-intake', 'skills/lanhu-requirements/SKILL.md', ('Re-check user confirmation/evidence comments only.', 'Do not proceed to brainstorming inside the Lanhu agent.'), ('Confirmed evidence-package handoff.',), 'B3 consumes the confirmed package.', upstream=('B1',), optional_args=('requirements_path', 'lanhu_url')),
            Stage('B3', 'Brainstorm from intake', ROLE_AGENTS['brainstorming'], 'brainstorming', 'upstream-superpowers/brainstorming.md', ('Discuss product direction from Lanhu evidence.', 'Keep output as brainstorming, not plan.'), ('Brainstorming output and open questions.',), 'B3r reviews the spec before planning.', upstream=('B2',), optional_args=('requirements_path',)),
            Stage('B3r', 'Spec document review from intake', ROLE_AGENTS['spec-document-reviewer'], 'spec-document-review', 'skills/brainstorming/spec-document-reviewer-prompt.md', ('Review the intake-derived spec before planning.', 'Block planning if the spec is not clear or not user-approved.'), ('Spec document review finding.',), 'B4 starts after user-approved reviewed direction.', upstream=('B3',), optional_args=('requirements_path', 'spec_path')),
            Stage('B4', 'Plan from intake direction', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Write plan using approved direction and selected wiki context.', 'Generate plan-selected context artifacts.'), ('Plan and `.wiki-context.json` references.',), 'B4r reviews the plan before execution.', upstream=('B3r',), optional_args=('requirements_path', 'spec_path', 'wiki_context_path')),
            Stage('B4r', 'Plan document review from intake', ROLE_AGENTS['plan-document-reviewer'], 'plan-document-review', 'skills/writing-plans/plan-document-reviewer-prompt.md', ('Review the intake-derived implementation plan before execution.', 'Block implementation if task decomposition, acceptance criteria, or wiki context are incomplete.'), ('Plan document review finding.',), 'B5 stages execute/review after approval.', upstream=('B4',), optional_args=('plan_path', 'wiki_context_path')),
            Stage('B5a', 'Implement intake plan', ROLE_AGENTS['implementer'], 'execute-plan', 'upstream-superpowers/executing-plans.md', ('Implement the approved plan only.', 'Post verification evidence.'), ('Implementation summary.',), 'B5b/B5c/B5d review.', upstream=('B4r',), optional_args=('plan_path', 'wiki_context_path')),
            Stage('B5b', 'Spec review intake implementation', ROLE_AGENTS['spec-reviewer'], 'spec-compliance-review', 'agents/spec-compliance-reviewer.md', ('Review against the plan/spec.',), ('Spec review finding.',), 'Failures return to B5a.', upstream=('B5a',), optional_args=('plan_path', 'spec_path')),
            Stage('B5c', 'Quality review intake implementation', ROLE_AGENTS['quality-reviewer'], 'code-quality-review', 'agents/code-quality-reviewer.md', ('Review code quality and tests.',), ('Quality review finding.',), 'Failures return to B5a.', upstream=('B5a',), optional_args=('plan_path',)),
            Stage('B5d', 'Final review intake implementation', ROLE_AGENTS['code-reviewer'], 'final-code-review', 'agents/code-reviewer.md', ('Run final review after B5b/B5c pass.',), ('Final review finding.',), 'B6 runs after pass.', upstream=('B5b', 'B5c'), optional_args=('plan_path',)),
            Stage('B6', 'Finish intake development branch', ROLE_AGENTS['finisher'], 'finishing-a-development-branch', 'upstream-superpowers/finishing-a-development-branch.md', ('Run finishing readiness after final review.', 'Ask before commit, push, PR creation, branch merge, or destructive git/worktree operations.'), ('Finishing readiness report.',), 'B7 updates wiki after finish readiness.', upstream=('B5d',), optional_args=('plan_path',)),
            Stage('B7', 'Update wiki from intake flow', ROLE_AGENTS['wiki-curator'], 'update-wiki', 'skills/update-wiki/SKILL.md', ('Review durable knowledge produced by B5.',), ('Wiki update decision.',), 'Chain B complete.', upstream=('B6',), optional_args=('plan_path', 'wiki_context_path')),
        ),
        required_args=('requirements_path',),
    ),
    'C': VisualCase(
        'C',
        'Brainstorming multi-turn to planning',
        'Validate user follow-up reruns brainstorming and only an approved direction creates separate planning/wiki-research runs.',
        (
            Stage('C1', 'Initial brainstorming', ROLE_AGENTS['brainstorming'], 'brainstorming', 'upstream-superpowers/brainstorming.md', ('Start brainstorming from the provided requirement/spec.', 'Do not write a plan.'), ('Initial brainstorming response.',), 'C2 handles user follow-up.', optional_args=('requirements_path', 'spec_path')),
            Stage('C2', 'Brainstorming follow-up rerun', ROLE_AGENTS['brainstorming'], 'brainstorming', 'upstream-superpowers/brainstorming.md', ('Respond to user follow-up.', 'Do not implement or write a plan.'), ('Updated brainstorming decision/options.',), 'C2r reviews the spec before approved-direction planning.', upstream=('C1',), optional_args=('requirements_path', 'spec_path')),
            Stage('C2r', 'Spec document review after brainstorming follow-up', ROLE_AGENTS['spec-document-reviewer'], 'spec-document-review', 'skills/brainstorming/spec-document-reviewer-prompt.md', ('Review the multi-turn brainstorming/spec document.', 'Block planning if open questions remain unresolved.'), ('Spec document review finding.',), 'C3 begins only after approved direction.', upstream=('C2',), optional_args=('requirements_path', 'spec_path')),
            Stage('C3', 'Approved direction planning', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Write plan from the approved direction.', 'Stop after plan output.'), ('Plan candidate.',), 'C3r reviews the plan document.', upstream=('C2r',), optional_args=('requirements_path', 'spec_path')),
            Stage('C3r', 'Plan document review after brainstorming', ROLE_AGENTS['plan-document-reviewer'], 'plan-document-review', 'skills/writing-plans/plan-document-reviewer-prompt.md', ('Review the plan generated from approved brainstorming.', 'Block execution if task boundaries or wiki references are incomplete.'), ('Plan document review finding.',), 'C4 supplies/validates plan wiki context.', upstream=('C3',), optional_args=('plan_path', 'wiki_context_path')),
            Stage('C4', 'Plan context wiki research', ROLE_AGENTS['wiki-researcher'], 'wiki-research', 'agents/wiki-researcher.md', ('Research wiki context for the planning stage as a separate run.',), ('Selected plan context.',), 'Planning issue records this context.', upstream=('C3r',), optional_args=('wiki_context_path',)),
        ),
    ),
    'D': VisualCase(
        'D',
        'SDD reviewer loop visible',
        'Validate implementer, spec reviewer, quality reviewer, fix loop, and final reviewer as separate Multica runs.',
        (
            Stage('D0', 'SDD plan document review', ROLE_AGENTS['plan-document-reviewer'], 'plan-document-review', 'skills/writing-plans/plan-document-reviewer-prompt.md', ('Review the approved SDD plan before task execution.', 'Block implementation if the plan is not execution-ready.'), ('Plan document review pass/fail.',), 'D1 implements only after this plan review passes.', required_args=('plan_path',), optional_args=('wiki_context_path',)),
            Stage('D1', 'Implement SDD task 1', ROLE_AGENTS['implementer'], 'sdd-implement-task', 'upstream-superpowers/subagent-driven-development.md', ('Implement task 1 from the approved plan.', 'Post verification evidence.'), ('Implementation artifact and verification.',), 'D2/D3 review this stage.', upstream=('D0',), required_args=('plan_path',), optional_args=('wiki_context_path',)),
            Stage('D2', 'Spec compliance review task 1', ROLE_AGENTS['spec-reviewer'], 'spec-compliance-review', 'agents/spec-compliance-reviewer.md', ('Review task 1 against plan/spec.', 'Block downstream if changes are required.'), ('Spec review pass/fail.',), 'Failures go to D4.', upstream=('D1',), required_args=('plan_path',)),
            Stage('D3', 'Code quality review task 1', ROLE_AGENTS['quality-reviewer'], 'code-quality-review', 'agents/code-quality-reviewer.md', ('Review task 1 quality and tests.', 'Block downstream if changes are required.'), ('Quality review pass/fail.',), 'Failures go to D4.', upstream=('D1',), required_args=('plan_path',)),
            Stage('D4', 'Implement reviewer fixes', ROLE_AGENTS['implementer'], 'sdd-implement-fixes', 'upstream-superpowers/subagent-driven-development.md', ('Apply requested fixes only if D2 or D3 requested changes.', 'Otherwise report no-op readiness.'), ('Fix summary or no-op readiness.',), 'D5 final review after fixes/pass.', upstream=('D2', 'D3'), required_args=('plan_path',), optional_args=('wiki_context_path',)),
            Stage('D5', 'Final code review after SDD loop', ROLE_AGENTS['code-reviewer'], 'final-code-review', 'agents/code-reviewer.md', ('Perform final review only after reviewer loop is resolved.',), ('Final review decision.',), 'D6 runs finishing readiness after final review.', upstream=('D4',), required_args=('plan_path',)),
            Stage('D6', 'Finish SDD development branch', ROLE_AGENTS['finisher'], 'finishing-a-development-branch', 'upstream-superpowers/finishing-a-development-branch.md', ('Run finishing-a-development-branch readiness after SDD final review.', 'Ask before commit, push, PR creation, branch merge, or destructive git/worktree operations.'), ('Finishing readiness report.',), 'Update-wiki is allowed only after this readiness report.', upstream=('D5',), required_args=('plan_path',)),
        ),
        required_args=('plan_path',),
    ),
    'E': VisualCase(
        'E',
        'Systematic debugging to break loop to update wiki',
        'Validate debugger, optional wiki research, implementer/fix handoff, break-loop retrospective, and wiki curator as separate runs.',
        (
            Stage('E1', 'Systematic debugging', ROLE_AGENTS['debugger'], 'systematic-debugging', 'upstream-superpowers/systematic-debugging.md', ('Start from evidence and narrow/reproduce before changing code.',), ('Root cause or next diagnostic step.',), 'E2 only if evidence points to wiki context.', required_args=('debug_evidence',), optional_args=('requirements_path',)),
            Stage('E2', 'Debug context wiki research', ROLE_AGENTS['wiki-researcher'], 'wiki-research', 'agents/wiki-researcher.md', ('Research wiki context only after E1 narrows the failing area.',), ('Relevant debug context or skip decision.',), 'E3 consumes only relevant context.', upstream=('E1',), optional_args=('wiki_context_path',)),
            Stage('E3', 'Debug fix handoff', ROLE_AGENTS['implementer'], 'execute-plan', 'upstream-superpowers/executing-plans.md', ('Implement a narrowed fix or post why code should not change.',), ('Fix/diagnostic handoff result.',), 'E4 runs for repeated-loop retrospective.', upstream=('E1', 'E2'), optional_args=('plan_path', 'wiki_context_path')),
            Stage('E4', 'Break-loop retrospective', ROLE_AGENTS['break-loop'], 'break-loop', 'skills/break-loop/SKILL.md', ('Analyze repeated failure or debugging loop.', 'Do not directly fix code.'), ('Retrospective and update-wiki candidates.',), 'E5 reviews durable knowledge.', upstream=('E3',), required_args=('debug_evidence',)),
            Stage('E5', 'Update wiki after debugging', ROLE_AGENTS['wiki-curator'], 'update-wiki', 'skills/update-wiki/SKILL.md', ('Review durable debugging knowledge.',), ('Wiki update decision.',), 'Chain E complete.', upstream=('E4',), optional_args=('plan_path', 'wiki_context_path')),
        ),
        required_args=('debug_evidence',),
    ),
    'F': VisualCase(
        'F',
        'Shared wiki local readiness',
        'Validate local shared-wiki review and publish readiness without MCP, publish, commit, push, or PR side effects.',
        (
            Stage('F1', 'Local shared wiki review', ROLE_AGENTS['wiki-researcher'], 'shared-wiki-local-review', 'agents/wiki-researcher.md', ('Inspect only local `.shared-superpowers/wiki` and settings.', 'Do not call shared-wiki MCP.'), ('Local neutrality/readiness findings.',), 'F2 prepares publish readiness.', optional_args=('wiki_context_path', 'requirements_path')),
            Stage('F2', 'Publish shared wiki readiness', ROLE_AGENTS['shared-wiki-publisher'], 'publish-shared-wiki', 'skills/publish-shared-wiki/SKILL.md', ('Produce neutrality, authorization gate, and missing-hook readiness report.', 'Do not publish, commit, push, or create PRs.'), ('Readiness report.',), 'Human authorizes any external publish separately.', upstream=('F1',), required_args=('shared_wiki_topic',), optional_args=('wiki_context_path',)),
        ),
        required_args=('shared_wiki_topic',),
    ),
    'G': VisualCase(
        'G',
        'Direct role-agent and squad dispatch',
        'Validate direct role-agent issue assignment and squad dispatch surfaces.',
        (
            Stage('G1', 'Direct brainstorming issue', ROLE_AGENTS['brainstorming'], 'brainstorming', 'upstream-superpowers/brainstorming.md', ('Run directly as brainstorming role agent.',), ('Brainstorming run visible under role agent.',), 'G2 validates planning direct assignment.', optional_args=('requirements_path',)),
            Stage('G2', 'Direct planning issue', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Run directly as planning role agent.',), ('Planning run visible under role agent.',), 'G3 validates squad assignment.', optional_args=('requirements_path', 'spec_path')),
            Stage('G3', 'Direct squad issue', SQUAD_NAME, 'visual-workflow', 'multica/squad-dispatch', ('Assign to squad and require visible squad leader run.', 'Do not let adapter orchestrator run all stages.'), ('Squad leader run and selected role handoff.',), 'G4 confirms selected role-agent run.', optional_args=('requirements_path',)),
            Stage('G4', 'Squad-selected role issue', ROLE_AGENTS['wiki-researcher'], 'wiki-research', 'agents/wiki-researcher.md', ('Run selected role agent from the squad handoff.',), ('Role-agent run visible.',), 'Chain G complete.', upstream=('G3',), optional_args=('requirements_path',)),
        ),
    ),
    'H': VisualCase(
        'H',
        'Failure recovery lifecycle',
        'Validate blocked, user-comment recovery, cancel, and rerun lifecycle without falling back to adapter orchestrator.',
        (
            Stage('H1', 'Missing required input blocks stage', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Detect missing required planning input and mark the stage blocked.', 'Do not continue downstream.'), ('Blocked status/comment requesting required input.',), 'H2 adds input and reruns the same role agent.'),
            Stage('H2', 'User adds required input then rerun', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Add a user-style comment with required input.', 'Rerun the same issue and same role agent.'), ('Recovered planning run visible.',), 'H3 cancels a running task for visibility.', action='comment-rerun', target_stage_id='H1', optional_args=('requirements_path', 'spec_path')),
            Stage('H3', 'Cancel running task', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Start a cancellable planning task.', 'Cancel it immediately so cancellation is visible in issue runs.'), ('Cancelled run visible.',), 'H4 reruns the cancelled issue.', action='create-assign-cancel'),
            Stage('H4', 'Rerun cancelled issue', ROLE_AGENTS['planning'], 'writing-plans', 'upstream-superpowers/writing-plans.md', ('Rerun after cancellation and confirm a new role-agent run completes.',), ('New completed role-agent run.',), 'Chain H complete.', action='rerun', target_stage_id='H3'),
        ),
    ),
}

CASE_ALIASES: dict[str, tuple[str, ...]] = {
    'all': tuple(VISUAL_CASES),
    'visual-all': tuple(VISUAL_CASES),
    'chain-a': ('A',),
    'chain-b': ('B',),
    'chain-c': ('C',),
    'chain-d': ('D',),
    'chain-e': ('E',),
    'chain-f': ('F',),
    'chain-g': ('G',),
    'chain-h': ('H',),
    'phase3': ('B', 'C'),
    'phase4': ('A', 'D'),
    'phase5': ('E', 'H'),
    'phase6': ('F',),
    'phase3-lanhu-intake': ('B',),
    'phase3-brainstorming': ('C',),
    'phase3-writing-plans': ('A',),
    'phase4-execute-plan': ('D',),
    'phase4-sdd-execution': ('D',),
    'phase5-systematic-debugging': ('E',),
    'phase5-break-loop': ('E',),
    'phase6-update-wiki': ('A',),
    'phase6-publish-shared-wiki': ('F',),
    'phase6-shared-wiki-mcp-pr': ('F',),
}


def case_choices() -> tuple[str, ...]:
    return tuple(CASE_ALIASES)


def selected_case_ids(selection: str) -> tuple[str, ...]:
    return CASE_ALIASES[selection]


def path_value(value: str | None) -> str | None:
    return Path(value).expanduser().resolve().as_posix() if value else None


def arg_flag(arg_name: str) -> str:
    return '--' + arg_name.replace('_', '-')


def input_line(ctx: AcceptanceContext, arg_name: str) -> str:
    value = getattr(ctx.args, arg_name)
    label = arg_name.replace('_', ' ')
    if not value:
        return f'- {label}: not provided'
    if arg_name.endswith('_path'):
        value = path_value(value)
    return f'- {label}: {value}'


def validate_required_args(ctx: AcceptanceContext, case: VisualCase) -> None:
    required = set(case.required_args)
    for stage in case.stages:
        required.update(stage.required_args)
    missing = [arg_flag(name) for name in sorted(required) if not getattr(ctx.args, name)]
    if missing:
        raise AcceptanceError(f'{case.case_id} requires {", ".join(missing)}')


def common_safety(ctx: AcceptanceContext) -> str:
    if ctx.args.allow_external_side_effects:
        side_effects = '- External side effects are authorized only to the extent explicitly requested in this issue; still ask before destructive operations or merging PRs.'
    else:
        side_effects = '- Do not commit, push, create or merge PRs, publish shared wiki changes, delete files, or run destructive git operations.'
    return '\n'.join([
        'Safety boundary:',
        side_effects,
        '- Do not run adapter repository Python scripts directly; use injected skill-pack supporting files when Superpowers instructions ask for helper scripts.',
        '- Do not assign this stage to `superpowers-adapter-orchestrator` or complete downstream stages inside one runtime.',
    ])


def stage_body(ctx: AcceptanceContext, case: VisualCase, stage: Stage) -> str:
    upstream = ', '.join(stage.upstream) if stage.upstream else 'none'
    inputs = tuple(dict.fromkeys((*stage.required_args, *stage.optional_args)))
    input_lines = '\n'.join(input_line(ctx, name) for name in inputs) if inputs else '- no direct CLI fixture input; use upstream stage issue comments/metadata.'
    required = '\n'.join(f'{index}. {item}' for index, item in enumerate(stage.required_behavior, 1))
    expected = '\n'.join(f'- {item}' for item in stage.expected_output)
    return f'''# {stage.title}

Run id: {ctx.run_id}
Visual chain: {case.case_id} — {case.title}
Stage: {stage.stage_id}
Assignee: {stage.assignee}
Target repo: {ctx.target_repo.as_posix()}
Issue template: {stage.issue_template}
Entrypoint: {stage.entrypoint}
Upstream stages: {upstream}

Use the attached `{SKILL_NAME}` skill pack.

User-facing language:
- Infer the user's preferred language only after first reading the assigned issue title, issue body, and latest user-authored comments.
- Ignore template labels, code, logs, commands, file paths, and API identifiers for language detection.
- Do not emit progress/status text before this language inference is complete.
- Write all user-facing comments, questions, summaries, review findings, readiness reports, and handoffs in that inferred language unless the user explicitly asks for another language.
- Keep code identifiers, commands, paths, logs, schemas, and quoted evidence in their original form.
- If the language is mixed or unclear, use the latest user-authored instruction's dominant language.

Inputs:
{input_lines}

Required behavior:
{required}

{common_safety(ctx)}

Expected output:
{expected}

Handoff / next step:
- {stage.handoff}
'''


def main_case_record(case: VisualCase) -> dict[str, Any]:
    return {
        'caseId': case.case_id,
        'title': case.title,
        'description': case.description,
        'stages': [
            {
                'stageId': stage.stage_id,
                'title': stage.title,
                'issueTemplate': stage.issue_template,
                'assignee': stage.assignee,
                'action': stage.action,
                'targetStageId': stage.target_stage_id,
            }
            for stage in case.stages
        ],
    }


def parse_json_records(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        records = []
        for line in text.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return records
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ('agents', 'items', 'data', 'results', 'issues'):
            values = data.get(key)
            if isinstance(values, list):
                return [item for item in values if isinstance(item, dict)]
        return [data]
    return []


def parse_issue_id(text: str) -> str | None:
    match = ISSUE_ID_RE.search(text) or UUID_RE.search(text)
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


def run_process(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def is_transient_multica_error(completed: subprocess.CompletedProcess[str]) -> bool:
    text = f'{completed.stdout}\n{completed.stderr}'.lower()
    return any(marker in text for marker in (
        'connection reset by peer',
        'connection refused',
        'tls handshake timeout',
        'i/o timeout',
        'context deadline exceeded',
        'temporary failure',
        'bad gateway',
        'gateway timeout',
        'service unavailable',
    ))


def run_process_with_retry(argv: list[str], attempts: int) -> subprocess.CompletedProcess[str]:
    completed = run_process(argv)
    for _ in range(1, attempts):
        if completed.returncode == 0 or not is_transient_multica_error(completed):
            return completed
        time.sleep(2)
        completed = run_process(argv)
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


def record_command(ctx: AcceptanceContext, argv: list[str], purpose: str, case: VisualCase, stage: Stage, *, action: str, issue_id: str | None = None, fail_on_error: bool = True) -> subprocess.CompletedProcess[str] | None:
    record: dict[str, Any] = {
        'caseId': case.case_id,
        'stageId': stage.stage_id,
        'issueTemplate': stage.issue_template,
        'assignee': stage.assignee,
        'action': action,
        'purpose': purpose,
        'argv': argv,
        'issueId': issue_id,
        'executed': False,
    }
    if not ctx.apply:
        ctx.commands.append(record)
        return None
    attempts = 3
    completed = run_process_with_retry(argv, attempts)
    record.update({
        'executed': True,
        'attempts': attempts,
        'returncode': completed.returncode,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
    })
    ctx.commands.append(record)
    if completed.returncode != 0 and fail_on_error:
        raise AcceptanceError(f'Multica visual acceptance command failed ({purpose}): {" ".join(argv)}\n{completed.stderr.strip() or completed.stdout.strip()}')
    return completed


def created_issue_placeholder(stage: Stage) -> str:
    return f'<{stage.stage_id}-issue-id>'


def create_issue(ctx: AcceptanceContext, case: VisualCase, stage: Stage) -> str:
    body = stage_body(ctx, case, stage)
    create_help = help_text(['issue', 'create'])
    body_flag = first_supported_flag(create_help, ('--description', '--body')) if create_help else '--description'
    cmd = ['multica', 'issue', 'create', '--title', f'{stage.stage_id} {stage.title} [{ctx.run_id}]']
    if body_flag:
        cmd.extend([body_flag, body])
    elif ctx.apply:
        raise AcceptanceError('Cannot create visual stage issue because Multica issue create exposes no --description/--body flag.')
    if create_help and has_flag(create_help, '--allow-duplicate'):
        cmd.append('--allow-duplicate')
    if create_help and has_flag(create_help, '--output'):
        cmd.extend(['--output', 'json'])
    completed = record_command(ctx, cmd, 'Create a Multica visual stage issue.', case, stage, action='create')
    if completed is None:
        issue_id = created_issue_placeholder(stage)
    else:
        issue_id = parse_issue_id(completed.stdout) or parse_issue_id(completed.stderr)
        if not issue_id:
            raise AcceptanceError(f'Could not parse created issue id for stage {stage.stage_id}.')
    ctx.issue_ids[stage.stage_id] = issue_id
    return issue_id


def assign_issue(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> None:
    record_command(ctx, ['multica', 'issue', 'assign', issue_id, '--to', stage.assignee], 'Assign the stage issue to the Multica role agent or squad.', case, stage, action='assign', issue_id=issue_id)


def comment_issue(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> None:
    comment = f'''Run id: {ctx.run_id}
Recovery stage: {stage.stage_id}
Required input has been supplied for rerun.

{stage_body(ctx, case, stage)}
'''
    comment_help = help_text(['issue', 'comment', 'add'])
    content_flag = first_supported_flag(comment_help, ('--content', '--body')) if comment_help else '--content'
    if not content_flag and ctx.apply:
        raise AcceptanceError('Cannot add recovery comment because Multica issue comment add exposes no --content/--body flag.')
    argv = ['multica', 'issue', 'comment', 'add', issue_id]
    if content_flag:
        argv.extend([content_flag, comment])
    record_command(ctx, argv, 'Add recovery input as an issue comment before rerun.', case, stage, action='comment', issue_id=issue_id)


def rerun_issue(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> None:
    record_command(ctx, ['multica', 'issue', 'rerun', issue_id], 'Rerun the stage issue so a new role-agent run is visible.', case, stage, action='rerun', issue_id=issue_id)


def latest_issue_run_id(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> str:
    argv = ['multica', 'issue', 'runs', issue_id, '--full-id', '--output', 'json']
    completed = record_command(ctx, argv, 'Resolve latest issue task run id for cancellation.', case, stage, action='resolve-run', issue_id=issue_id)
    if completed is None:
        return f'<{stage.stage_id}-task-run-id>'
    records = parse_json_records(completed.stdout)
    if not records:
        raise AcceptanceError(f'No task runs are visible for issue {issue_id}; cannot cancel stage {stage.stage_id}.')
    latest = sorted(records, key=lambda record: str(record.get('created_at') or record.get('started_at') or ''))[-1]
    task_id = latest.get('id')
    if not isinstance(task_id, str) or not task_id:
        raise AcceptanceError(f'Could not resolve latest task run id for issue {issue_id}.')
    return task_id


def cancel_issue_task(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> None:
    task_id = latest_issue_run_id(ctx, case, stage, issue_id)
    record_command(ctx, ['multica', 'issue', 'cancel-task', task_id, '--issue', issue_id], 'Cancel the active stage task so cancellation is visible in issue runs.', case, stage, action='cancel', issue_id=issue_id)


def observe_issue(ctx: AcceptanceContext, case: VisualCase, stage: Stage, issue_id: str) -> None:
    if not ctx.args.observe_runs:
        return
    commands = [['multica', 'issue', 'runs', issue_id]]
    deadline = time.monotonic() + ctx.args.observe_timeout_seconds
    while True:
        observed_output = False
        for argv in commands:
            completed = record_command(ctx, argv, 'Observe Multica issue runs.', case, stage, action='observe', issue_id=issue_id, fail_on_error=False)
            if completed is None:
                continue
            if completed.returncode != 0:
                ctx.checks.append({'id': f'observe-{stage.stage_id}', 'status': 'warning', 'message': 'Observation command failed without blocking stage dispatch.', 'argv': argv, 'stderr': completed.stderr.strip(), 'issueId': issue_id})
                continue
            observed_output = observed_output or bool(completed.stdout.strip() or completed.stderr.strip())
        if not ctx.apply or observed_output:
            return
        if time.monotonic() >= deadline:
            ctx.checks.append({'id': f'observe-{stage.stage_id}', 'status': 'warning', 'message': 'No Multica issue run output appeared before the observation timeout.', 'issueId': issue_id})
            return
        time.sleep(ctx.args.observe_interval_seconds)


def target_issue_id(ctx: AcceptanceContext, stage: Stage) -> str:
    target_stage_id = stage.target_stage_id or stage.stage_id
    issue_id = ctx.issue_ids.get(target_stage_id)
    if issue_id:
        return issue_id
    return f'<{target_stage_id}-issue-id>'


def run_stage(ctx: AcceptanceContext, case: VisualCase, stage: Stage) -> None:
    if stage.action == 'create-assign':
        issue_id = create_issue(ctx, case, stage)
        assign_issue(ctx, case, stage, issue_id)
        observe_issue(ctx, case, stage, issue_id)
        return
    if stage.action == 'create-assign-cancel':
        issue_id = create_issue(ctx, case, stage)
        assign_issue(ctx, case, stage, issue_id)
        cancel_issue_task(ctx, case, stage, issue_id)
        observe_issue(ctx, case, stage, issue_id)
        return
    issue_id = target_issue_id(ctx, stage)
    if stage.action == 'comment-rerun':
        comment_issue(ctx, case, stage, issue_id)
        rerun_issue(ctx, case, stage, issue_id)
        observe_issue(ctx, case, stage, issue_id)
        return
    if stage.action == 'cancel':
        cancel_issue_task(ctx, case, stage, issue_id)
        observe_issue(ctx, case, stage, issue_id)
        return
    if stage.action == 'rerun':
        rerun_issue(ctx, case, stage, issue_id)
        observe_issue(ctx, case, stage, issue_id)
        return
    raise AcceptanceError(f'Unknown visual stage action: {stage.action}')


def run_case(ctx: AcceptanceContext, case: VisualCase) -> None:
    validate_required_args(ctx, case)
    ctx.cases.append(main_case_record(case))
    for stage in case.stages:
        run_stage(ctx, case, stage)


def preflight(ctx: AcceptanceContext) -> None:
    if not ctx.apply:
        ctx.commands.extend([
            {'argv': ['multica', 'auth', 'status'], 'purpose': 'Check Multica login status.', 'executed': False},
            {'argv': ['multica', 'daemon', 'status'], 'purpose': 'Check Multica daemon status.', 'executed': False},
            {'argv': ['multica', 'agent', 'list', '--output', 'json'], 'purpose': 'Check materialized Superpowers role agents.', 'executed': False},
            {'argv': ['multica', 'squad', 'list', '--output', 'json'], 'purpose': 'Check Superpowers runtime squad.', 'executed': False},
        ])
        return
    if shutil.which('multica') is None:
        ctx.checks.append({'id': 'multica-cli', 'status': 'blocked', 'message': 'Multica CLI is not installed.'})
        raise AcceptanceError('Multica CLI is not installed; cannot run --apply visual acceptance.')
    for argv, check_id, message in (
        (['multica', 'auth', 'status'], 'multica-auth', 'Multica authentication status checked.'),
        (['multica', 'daemon', 'status'], 'multica-daemon', 'Multica daemon status checked.'),
        (['multica', 'agent', 'list', '--output', 'json'], 'multica-role-agents', 'Multica role agent list checked.'),
        (['multica', 'squad', 'list', '--output', 'json'], 'multica-squad', 'Multica squad list checked.'),
    ):
        completed = run_process(argv)
        ctx.commands.append({'argv': argv, 'purpose': message, 'executed': True, 'returncode': completed.returncode, 'stdout': completed.stdout.strip(), 'stderr': completed.stderr.strip()})
        if completed.returncode == 0:
            ctx.checks.append({'id': check_id, 'status': 'passed', 'message': message})
        else:
            ctx.checks.append({'id': check_id, 'status': 'blocked', 'message': f'{message} Command failed.', 'stderr': completed.stderr.strip()})
            raise AcceptanceError(f'{message} Command failed: {completed.stderr.strip() or completed.stdout.strip()}')


def run(ctx: AcceptanceContext) -> None:
    preflight(ctx)
    for case_id in selected_case_ids(ctx.args.case):
        run_case(ctx, VISUAL_CASES[case_id])
    all_assignees = {command.get('assignee') for command in ctx.commands if command.get('assignee')}
    if ORCHESTRATOR_AGENT in all_assignees:
        ctx.checks.append({'id': 'no-adapter-orchestrator-fallback', 'status': 'blocked', 'message': 'Visual acceptance must not assign stages to superpowers-adapter-orchestrator.'})
        raise AcceptanceError('Visual acceptance planned an adapter-orchestrator fallback assignment.')
    ctx.checks.append({'id': 'role-agent-fanout', 'status': 'passed', 'message': 'Acceptance uses visible Multica stage issues assigned to role agents/squad instead of one adapter orchestrator.'})
    ctx.checks.append({'id': 'external-side-effect-boundary', 'status': 'passed', 'message': 'Stage issue bodies default to readiness/authorization gates for push, PR, merge, publish, and destructive operations.'})


def resolve_context(args: argparse.Namespace) -> AcceptanceContext:
    adapter_root = Path(args.adapter_root).expanduser().resolve()
    target_repo = Path(args.target_repo).expanduser().resolve()
    if not (adapter_root / 'manifest.json').is_file():
        raise AcceptanceError(f'Missing adapter manifest: {adapter_root}')
    if not target_repo.is_dir():
        raise AcceptanceError(f'Missing target repo: {target_repo}')
    return AcceptanceContext(args, adapter_root, target_repo)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=case_choices(), default='all')
    parser.add_argument('--adapter-root', default=Path(__file__).resolve().parents[1].as_posix())
    parser.add_argument('--superpowers-source', help='Accepted for compatibility; role-agent visual acceptance assumes the Multica runtime has already been installed/updated.')
    parser.add_argument('--target-repo', required=True)
    parser.add_argument('--skill-pack-dir', help='Accepted for compatibility; visual acceptance uses already attached role-agent skills.')
    parser.add_argument('--agent-name', default=SQUAD_NAME, help='Deprecated compatibility flag; visual acceptance routes by stage assignee instead.')
    parser.add_argument('--lanhu-url')
    parser.add_argument('--requirements-path')
    parser.add_argument('--spec-path')
    parser.add_argument('--plan-path')
    parser.add_argument('--wiki-context-path')
    parser.add_argument('--debug-evidence')
    parser.add_argument('--shared-wiki-topic')
    parser.add_argument('--bootstrap', action='store_true', help='Deprecated compatibility flag; visual acceptance always creates stage issues directly.')
    parser.add_argument('--allow-external-side-effects', action='store_true')
    parser.add_argument('--observe-runs', action='store_true', help='Observe issue runs after assignment or rerun.')
    parser.add_argument('--observe-timeout-seconds', type=int, default=60)
    parser.add_argument('--observe-interval-seconds', type=int, default=5)
    parser.add_argument('--apply', action='store_true', help='Create/assign real Multica visual acceptance stage issues.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        raise AcceptanceError('Use either --apply or --dry-run, not both.')
    if args.agent_name == ORCHESTRATOR_AGENT:
        raise AcceptanceError('superpowers-adapter-orchestrator is no longer valid for visual acceptance; use role-agent/squad dispatch.')
    return args


def print_text_summary(ctx: AcceptanceContext) -> None:
    data = ctx.as_dict()
    print(f'Multica visual acceptance status: {data["status"]}')
    for case in ctx.cases:
        print(f'- Chain {case["caseId"]}: {case["title"]}')
        for stage in case['stages']:
            print(f'  - {stage["stageId"]}: {stage["assignee"]} — {stage["title"]}')
    if ctx.commands:
        print('Commands:')
        for command in ctx.commands:
            prefix = 'ran' if command.get('executed') else 'planned'
            print(f'- {prefix}: {" ".join(command["argv"])}')


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        ctx = resolve_context(args)
        run(ctx)
    except AcceptanceError as exc:
        json_flag = '--json' in argv
        if json_flag and 'ctx' in locals():
            print(json.dumps(ctx.as_dict() | {'error': str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        elif json_flag:
            print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            if 'ctx' in locals():
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
