#!/usr/bin/env python3
"""Shared constants for the generated Multica Superpowers runtime bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ADAPTER_PLUGIN_ROOT_PLACEHOLDER = '__SUPERPOWER_ADAPTER_PLUGIN_ROOT__'
MULTICA_RUNTIME_ROOT_EXPR = '${MULTICA_SUPERPOWERS_RUNTIME_ROOT}'
MULTICA_TOOLS_ROOT_EXPR = f'{MULTICA_RUNTIME_ROOT_EXPR}/tools'
GENERATED_BY = 'superpower-adapter multica runtime builder'

REQUIRED_CAPABILITIES = (
    'local-filesystem',
    'shell-git',
    'artifact-store',
    'task-isolation',
    'mcp-client',
)

OPTIONAL_MCP_SERVERS = (
    'lanhu-mcp',
    'shared-wiki-mcp',
    'github-mcp',
)

PREFLIGHT_ARTIFACTS = (
    'runtime-capabilities.json',
    'workflow-invocation-contract.json',
    'artifact-store-contract.json',
    'gate-transition-contract.json',
    'role-task-contract.json',
)

VALIDATOR_SCRIPTS = (
    'runtime_capability_preflight.py',
    'workflow_invocation_validate.py',
    'artifact_next_action_suggest.py',
    'intent_router_suggest.py',
    'gate_state_validate.py',
    'gate_transition_validate.py',
    'artifact_store_validate.py',
    'role_task_validate.py',
    'issue_template_invocation_build.py',
    'compatibility_command_invocation_build.py',
)

TASK_GRAPHS = (
    'subagent-driven-development.task-graph.json',
)

WORKFLOW_MCP_REQUIREMENTS = {
    'lanhu-requirements': ('lanhu-mcp',),
    'shared-wiki-mcp': ('shared-wiki-mcp', 'github-mcp'),
}


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    source_kind: str
    source_path: Path
    gate_ids: tuple[str, ...]
    role_agent_ids: tuple[str, ...]
    execution_mode: str
    required_artifacts: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()

    @property
    def filename(self) -> str:
        return f'{self.workflow_id}.workflow.yaml'


UPSTREAM_WORKFLOWS = (
    WorkflowSpec('using-superpowers', 'superpowers-native-skill', Path('skills/using-superpowers/SKILL.md'), (), ('superpowers-orchestrator',), 'workflow-runtime'),
    WorkflowSpec('brainstorming', 'superpowers-native-skill', Path('skills/brainstorming/SKILL.md'), ('design-approval',), ('superpowers-orchestrator', 'brainstorming-agent', 'wiki-researcher', 'spec-document-reviewer'), 'brainstorming', output_artifacts=('spec',)),
    WorkflowSpec('writing-plans', 'superpowers-native-skill', Path('skills/writing-plans/SKILL.md'), ('spec-approval',), ('superpowers-orchestrator', 'planning-agent', 'wiki-researcher', 'source-of-truth-verifier', 'plan-document-reviewer'), 'planning', required_artifacts=('approved-spec',), output_artifacts=('implementation-plan', 'wiki-context', 'source-truth-report', 'source-truth-constraints')),
    WorkflowSpec('executing-plans', 'superpowers-native-skill', Path('skills/executing-plans/SKILL.md'), (), ('superpowers-orchestrator', 'implementer', 'wiki-curator'), 'inline-sequential', required_artifacts=('implementation-plan', 'wiki-context')),
    WorkflowSpec('subagent-driven-development', 'superpowers-native-skill', Path('skills/subagent-driven-development/SKILL.md'), (), ('superpowers-orchestrator', 'implementer', 'spec-compliance-reviewer', 'code-quality-reviewer', 'code-reviewer'), 'multica-sdd-task-graph', required_artifacts=('implementation-plan', 'wiki-context')),
    WorkflowSpec('systematic-debugging', 'superpowers-native-skill', Path('skills/systematic-debugging/SKILL.md'), (), ('superpowers-orchestrator', 'debugger', 'wiki-researcher'), 'debug', required_artifacts=('failure-evidence',)),
    WorkflowSpec('test-driven-development', 'superpowers-native-skill', Path('skills/test-driven-development/SKILL.md'), (), ('implementer',), 'development'),
    WorkflowSpec('verification-before-completion', 'superpowers-native-skill', Path('skills/verification-before-completion/SKILL.md'), (), ('superpowers-orchestrator',), 'verification'),
    WorkflowSpec('finishing-a-development-branch', 'superpowers-native-skill', Path('skills/finishing-a-development-branch/SKILL.md'), ('shared-wiki-publish-authorization', 'external-pr-creation-authorization'), ('superpowers-orchestrator', 'finisher'), 'finishing'),
    WorkflowSpec('using-git-worktrees', 'superpowers-native-skill', Path('skills/using-git-worktrees/SKILL.md'), (), ('superpowers-orchestrator',), 'git-worktree'),
    WorkflowSpec('requesting-code-review', 'superpowers-native-skill', Path('skills/requesting-code-review/SKILL.md'), (), ('code-reviewer',), 'review'),
    WorkflowSpec('receiving-code-review', 'superpowers-native-skill', Path('skills/receiving-code-review/SKILL.md'), (), ('superpowers-orchestrator', 'implementer'), 'review-response'),
)

ADAPTER_WORKFLOWS = (
    WorkflowSpec('update-wiki', 'adapter-skill', Path('overlays/skills/update-wiki/SKILL.md'), ('wiki-update-authorization',), ('superpowers-orchestrator', 'wiki-curator'), 'maintenance'),
    WorkflowSpec('break-loop', 'adapter-skill', Path('overlays/skills/break-loop/SKILL.md'), (), ('superpowers-orchestrator', 'break-loop-analyst'), 'maintenance'),
    WorkflowSpec('wiki-progressive-disclosure', 'adapter-skill', Path('overlays/skills/wiki-progressive-disclosure/SKILL.md'), (), ('wiki-researcher',), 'maintenance'),
    WorkflowSpec('init-wiki', 'adapter-skill', Path('overlays/skills/init-wiki/SKILL.md'), ('wiki-update-authorization',), ('superpowers-orchestrator', 'wiki-curator'), 'standalone'),
    WorkflowSpec('import-wiki', 'adapter-skill', Path('overlays/skills/import-wiki/SKILL.md'), ('wiki-update-authorization',), ('superpowers-orchestrator', 'wiki-curator'), 'standalone'),
    WorkflowSpec('migrate-wiki', 'adapter-skill', Path('overlays/skills/migrate-wiki/SKILL.md'), ('wiki-update-authorization',), ('superpowers-orchestrator', 'wiki-curator'), 'standalone'),
    WorkflowSpec('lanhu-requirements', 'adapter-skill', Path('overlays/skills/lanhu-requirements/SKILL.md'), ('lanhu-scope-confirmation',), ('superpowers-orchestrator', 'lanhu-frontend-requirements-analyst', 'lanhu-frontend-html-requirements-analyst', 'lanhu-backend-requirements-analyst'), 'standalone'),
    WorkflowSpec('shared-wiki-mcp', 'adapter-skill', Path('overlays/skills/shared-wiki-mcp/SKILL.md'), ('external-pr-creation-authorization',), ('superpowers-orchestrator', 'shared-wiki-publisher', 'wiki-curator'), 'standalone'),
    WorkflowSpec('publish-shared-wiki', 'adapter-skill', Path('overlays/skills/publish-shared-wiki/SKILL.md'), ('shared-wiki-publish-authorization',), ('superpowers-orchestrator', 'shared-wiki-publisher'), 'standalone'),
)

EXPECTED_WORKFLOWS = UPSTREAM_WORKFLOWS + ADAPTER_WORKFLOWS

UPSTREAM_ROLE_PROMPTS = {
    'spec-document-reviewer': Path('skills/brainstorming/spec-document-reviewer-prompt.md'),
    'plan-document-reviewer': Path('skills/writing-plans/plan-document-reviewer-prompt.md'),
    'implementer': Path('skills/subagent-driven-development/implementer-prompt.md'),
    'spec-compliance-reviewer': Path('skills/subagent-driven-development/spec-reviewer-prompt.md'),
    'code-quality-reviewer': Path('skills/subagent-driven-development/code-quality-reviewer-prompt.md'),
    'code-reviewer': Path('skills/requesting-code-review/code-reviewer.md'),
}

ADAPTER_ROLE_AGENT_PATHS = {
    'wiki-researcher': Path('overlays/agents/wiki-researcher.md'),
    'source-of-truth-verifier': Path('overlays/agents/source-of-truth-verifier.md'),
}

GENERATED_LANHU_AGENT_IDS = (
    'lanhu-frontend-requirements-analyst',
    'lanhu-frontend-html-requirements-analyst',
    'lanhu-backend-requirements-analyst',
)

TEMPLATE_ROLE_AGENT_IDS = (
    'superpowers-orchestrator',
    'brainstorming-agent',
    'planning-agent',
    'debugger',
    'break-loop-analyst',
    'wiki-curator',
    'finisher',
    'shared-wiki-publisher',
)

EXPECTED_ROLE_AGENTS = (
    *TEMPLATE_ROLE_AGENT_IDS,
    *ADAPTER_ROLE_AGENT_PATHS.keys(),
    *UPSTREAM_ROLE_PROMPTS.keys(),
    *GENERATED_LANHU_AGENT_IDS,
)

ROLE_AGENT_CONTRACTS = {
    'superpowers-orchestrator': {
        'roleKind': 'orchestrator',
        'inputArtifacts': ('WorkflowInvocation', 'gate-state', 'workflow-output'),
        'outputArtifacts': ('role-task-request', 'WorkflowInvocation-preflight', 'issue-comment'),
        'allowedCapabilities': REQUIRED_CAPABILITIES,
        'toolAccess': ('multica-task-api', 'artifact-store', 'gate-state-management'),
        'mayAdvanceGates': True,
        'mayPerformExternalSideEffects': False,
    },
    'brainstorming-agent': {
        'roleKind': 'workflow-role',
        'inputArtifacts': ('requirements', 'lanhu-evidence-package', 'wiki-disclosure'),
        'outputArtifacts': ('spec', 'design-options', 'open-questions'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'wiki-researcher-result'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'planning-agent': {
        'roleKind': 'workflow-role',
        'inputArtifacts': ('approved-spec', 'wiki-selection', 'source-truth-report', 'source-truth-constraints'),
        'outputArtifacts': ('implementation-plan', 'wiki-context', 'source-truth-report', 'source-truth-constraints'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'wiki-context-render-preview', 'source-truth-render-preview'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'wiki-researcher': {
        'roleKind': 'research-role',
        'inputArtifacts': ('task-intent', 'wiki-root-indexes'),
        'outputArtifacts': ('wiki-selection', 'wiki-disclosure'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-project-wiki', 'read-shared-wiki'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'source-of-truth-verifier': {
        'roleKind': 'verification-role',
        'inputArtifacts': ('implementation-plan', 'wiki-context', 'source-truth-settings'),
        'outputArtifacts': ('source-truth-report', 'source-truth-constraints'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'source-truth-settings', 'source-truth-render-preview'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'implementer': {
        'roleKind': 'implementation-role',
        'inputArtifacts': ('implementation-plan', 'wiki-context', 'source-truth-constraints', 'sdd-task-input'),
        'outputArtifacts': ('sdd-task-output', 'patch-summary', 'verification-result'),
        'allowedCapabilities': ('local-filesystem', 'shell-git', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-write-target-repo', 'shell-git', 'wiki-context-render', 'source-truth-render'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'spec-document-reviewer': {
        'roleKind': 'review-role',
        'inputArtifacts': ('spec',),
        'outputArtifacts': ('review-result',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo',),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'plan-document-reviewer': {
        'roleKind': 'review-role',
        'inputArtifacts': ('implementation-plan', 'wiki-context'),
        'outputArtifacts': ('review-result',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'wiki-context-render'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'spec-compliance-reviewer': {
        'roleKind': 'review-role',
        'inputArtifacts': ('implementation-plan', 'wiki-context', 'sdd-task-output'),
        'outputArtifacts': ('review-result',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'wiki-context-render'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'code-quality-reviewer': {
        'roleKind': 'review-role',
        'inputArtifacts': ('implementation-plan', 'wiki-context', 'sdd-task-output', 'review-result'),
        'outputArtifacts': ('review-result',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo', 'wiki-context-render'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'code-reviewer': {
        'roleKind': 'review-role',
        'inputArtifacts': ('patch-summary', 'sdd-task-output', 'review-result'),
        'outputArtifacts': ('final-code-review-result', 'review-result'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo',),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'debugger': {
        'roleKind': 'debug-role',
        'inputArtifacts': ('failure-evidence', 'target-repo-state'),
        'outputArtifacts': ('root-cause-analysis', 'verification-result', 'patch-summary'),
        'allowedCapabilities': ('local-filesystem', 'shell-git', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-write-target-repo', 'shell-git', 'conditional-wiki-researcher'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'break-loop-analyst': {
        'roleKind': 'retrospective-role',
        'inputArtifacts': ('failure-evidence', 'verification-result', 'root-cause-analysis'),
        'outputArtifacts': ('break-loop-retrospective', 'update-wiki-candidate'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-target-repo',),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'wiki-curator': {
        'roleKind': 'maintenance-role',
        'inputArtifacts': ('update-wiki-candidate', 'gate-state'),
        'outputArtifacts': ('wiki-update-decision', 'wiki-page-patch'),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation'),
        'toolAccess': ('read-project-wiki', 'read-shared-wiki', 'wiki-mechanical-scripts'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'finisher': {
        'roleKind': 'finishing-role',
        'inputArtifacts': ('verification-result', 'final-code-review-result', 'gate-state'),
        'outputArtifacts': ('finishing-report',),
        'allowedCapabilities': ('local-filesystem', 'shell-git', 'artifact-store', 'task-isolation'),
        'toolAccess': ('shell-git', 'read-target-repo'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'shared-wiki-publisher': {
        'roleKind': 'publish-role',
        'inputArtifacts': ('shared-wiki-candidate', 'gate-state'),
        'outputArtifacts': ('publish-report', 'pull-request-reference'),
        'allowedCapabilities': REQUIRED_CAPABILITIES,
        'toolAccess': ('shared-wiki-validation', 'shell-git', 'github-mcp', 'shared-wiki-mcp'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': True,
    },
    'lanhu-frontend-requirements-analyst': {
        'roleKind': 'lanhu-role',
        'inputArtifacts': ('lanhu-page-scope',),
        'outputArtifacts': ('lanhu-evidence-package',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation', 'mcp-client'),
        'toolAccess': ('lanhu-mcp', 'selective-image-analysis'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'lanhu-frontend-html-requirements-analyst': {
        'roleKind': 'lanhu-role',
        'inputArtifacts': ('lanhu-page-scope',),
        'outputArtifacts': ('lanhu-evidence-package',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation', 'mcp-client'),
        'toolAccess': ('lanhu-mcp', 'selective-image-analysis'),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
    'lanhu-backend-requirements-analyst': {
        'roleKind': 'lanhu-role',
        'inputArtifacts': ('lanhu-page-scope',),
        'outputArtifacts': ('lanhu-evidence-package',),
        'allowedCapabilities': ('local-filesystem', 'artifact-store', 'task-isolation', 'mcp-client'),
        'toolAccess': ('lanhu-mcp',),
        'mayAdvanceGates': False,
        'mayPerformExternalSideEffects': False,
    },
}

GATES = (
    'design-approval',
    'spec-approval',
    'lanhu-scope-confirmation',
    'wiki-update-authorization',
    'shared-wiki-publish-authorization',
    'external-pr-creation-authorization',
)

GATE_TRANSITION_CONTRACT = {
    'contractId': 'multica-superpowers-gate-transitions',
    'statusValues': ('pending', 'satisfied', 'blocked'),
    'allowedTransitions': (
        {'from': 'pending', 'to': 'satisfied', 'requiresEvidence': True, 'requiresOwnerRole': True},
        {'from': 'pending', 'to': 'blocked', 'requiresEvidence': True, 'requiresOwnerRole': True},
        {'from': 'blocked', 'to': 'pending', 'requiresEvidence': True, 'requiresOwnerRole': True},
        {'from': 'blocked', 'to': 'satisfied', 'requiresEvidence': True, 'requiresOwnerRole': True},
    ),
    'forbiddenTransitions': (
        {'from': 'satisfied', 'to': 'pending', 'reason': 'Satisfied gates are immutable unless a future live Multica API exposes audited reversal.'},
        {'from': 'satisfied', 'to': 'blocked', 'reason': 'Satisfied gates are immutable unless a future live Multica API exposes audited reversal.'},
    ),
    'advancePolicy': 'gate-owner-or-orchestrator-only',
    'externalSideEffectPolicy': 'blocked-until-side-effect-gate-satisfied',
    'liveApiBoundary': 'Local validators define transition contracts until Multica gate state API integration is available.',
}

GATE_CONTRACTS = {
    'design-approval': {
        'gateType': 'user-approval',
        'ownerRoleAgent': 'superpowers-orchestrator',
        'requiredArtifacts': ('spec',),
        'satisfiedBy': ('user-approved-design-direction',),
        'blocksExternalSideEffects': False,
        'userAuthorizationRequired': True,
        'description': 'Blocks progression from brainstorming output until the user approves the design direction.',
    },
    'spec-approval': {
        'gateType': 'artifact-review',
        'ownerRoleAgent': 'superpowers-orchestrator',
        'requiredArtifacts': ('approved-spec',),
        'satisfiedBy': ('spec-document-reviewer-passed', 'user-approved-spec'),
        'blocksExternalSideEffects': False,
        'userAuthorizationRequired': True,
        'description': 'Blocks planning until spec document review passes and the user approves the spec artifact.',
    },
    'lanhu-scope-confirmation': {
        'gateType': 'scope-confirmation',
        'ownerRoleAgent': 'superpowers-orchestrator',
        'requiredArtifacts': ('lanhu-evidence-package',),
        'satisfiedBy': ('confirmationGate.clear', 'user-confirmed-index-and-scope-summary'),
        'blocksExternalSideEffects': False,
        'userAuthorizationRequired': True,
        'description': 'Blocks Lanhu handoff until evidence scope is clear and the package entrypoint is confirmed.',
    },
    'wiki-update-authorization': {
        'gateType': 'wiki-write-authorization',
        'ownerRoleAgent': 'wiki-curator',
        'requiredArtifacts': ('update-wiki-candidate',),
        'satisfiedBy': ('root-settings-allow-write', 'user-authorized-wiki-write'),
        'blocksExternalSideEffects': False,
        'userAuthorizationRequired': True,
        'description': 'Controls project/shared wiki writes according to root-specific settings and user authorization.',
    },
    'shared-wiki-publish-authorization': {
        'gateType': 'external-side-effect-authorization',
        'ownerRoleAgent': 'shared-wiki-publisher',
        'requiredArtifacts': ('shared-wiki-candidate',),
        'satisfiedBy': ('neutrality-guard-passed', 'user-authorized-publish-scope'),
        'blocksExternalSideEffects': True,
        'userAuthorizationRequired': True,
        'description': 'Blocks local shared wiki submodule commit/push publication until neutrality and publish scope are approved.',
    },
    'external-pr-creation-authorization': {
        'gateType': 'external-side-effect-authorization',
        'ownerRoleAgent': 'shared-wiki-publisher',
        'requiredArtifacts': ('shared-wiki-candidate',),
        'satisfiedBy': ('shared-wiki-patch-validated', 'user-authorized-pr-scope'),
        'blocksExternalSideEffects': True,
        'userAuthorizationRequired': True,
        'description': 'Blocks GitHub-backed shared-wiki PR creation until validation and PR scope authorization pass.',
    },
}

TRIGGERS = (
    'compatibility-commands',
    'issue-template-bindings',
    'intent-router',
    'artifact-next-actions',
    'illegal-transition-rules',
)

COMPATIBILITY_COMMANDS = (
    {'commandId': 'start-brainstorming', 'phrases': ('brainstorming', 'start brainstorming', '进入 brainstorming workflow'), 'workflowId': 'brainstorming', 'requiredArtifacts': (), 'requiredGates': ()},
    {'commandId': 'write-plan', 'phrases': ('writing-plans', 'write implementation plan', '进入 writing-plans workflow'), 'workflowId': 'writing-plans', 'requiredArtifacts': ('approved-spec',), 'requiredGates': ('spec-approval',)},
    {'commandId': 'execute-plan', 'phrases': ('execute this plan', 'executing-plans', '执行这个 plan'), 'workflowId': 'executing-plans', 'requiredArtifacts': ('implementation-plan', 'wiki-context'), 'requiredGates': ()},
    {'commandId': 'sdd-execution', 'phrases': ('subagent-driven-development', 'SDD task graph', '用 SDD task graph 执行'), 'workflowId': 'subagent-driven-development', 'requiredArtifacts': ('implementation-plan', 'wiki-context'), 'requiredGates': ()},
    {'commandId': 'debug', 'phrases': ('systematic-debugging', 'debug this failure', '系统调试'), 'workflowId': 'systematic-debugging', 'requiredArtifacts': ('failure-evidence',), 'requiredGates': ()},
    {'commandId': 'update-wiki', 'phrases': ('update-wiki', '更新 wiki', '沉淀长期知识'), 'workflowId': 'update-wiki', 'requiredArtifacts': ('completed-task-summary',), 'requiredGates': ()},
    {'commandId': 'lanhu-requirements', 'phrases': ('lanhu-requirements', '处理蓝湖链接', 'Lanhu intake'), 'workflowId': 'lanhu-requirements', 'requiredArtifacts': (), 'requiredGates': ()},
)

INTENT_ROUTER_RULES = (
    {'intentId': 'feature-or-behavior-change', 'matches': ('new feature', 'behavior change', '新功能', '改行为'), 'candidateWorkflowId': 'brainstorming', 'cannotBypassGates': ('design-approval', 'spec-approval')},
    {'intentId': 'approved-spec-planning', 'matches': ('spec approved', 'write plan', 'spec 已确认', '写计划'), 'candidateWorkflowId': 'writing-plans', 'cannotBypassGates': ('spec-approval',)},
    {'intentId': 'approved-plan-execution', 'matches': ('plan approved', 'execute plan', 'plan 可以开始', '执行计划'), 'candidateWorkflowId': 'subagent-driven-development', 'cannotBypassGates': ()},
    {'intentId': 'bug-or-test-failure', 'matches': ('bug', 'test failure', '测试失败', '线上问题'), 'candidateWorkflowId': 'systematic-debugging', 'cannotBypassGates': ()},
    {'intentId': 'durable-knowledge', 'matches': ('update wiki', 'durable knowledge', '沉淀知识', '更新知识库'), 'candidateWorkflowId': 'update-wiki', 'cannotBypassGates': ('wiki-update-authorization',)},
    {'intentId': 'lanhu-url', 'matches': ('lanhu', '蓝湖'), 'candidateWorkflowId': 'lanhu-requirements', 'cannotBypassGates': ('lanhu-scope-confirmation',)},
    {'intentId': 'shared-wiki-publish', 'matches': ('publish shared wiki', 'shared wiki PR', '发布 shared wiki'), 'candidateWorkflowId': 'publish-shared-wiki', 'cannotBypassGates': ('shared-wiki-publish-authorization', 'external-pr-creation-authorization')},
)

TRIGGER_CONTRACTS = {
    'compatibility-commands': {
        'requiredInputs': ('commandText', 'targetRepo', 'userIntent'),
        'preflightChecks': ('workflow-id-known', 'target-repo-readable', 'required-artifacts-present'),
    },
    'issue-template-bindings': {
        'requiredInputs': ('issueTemplateId', 'targetRepo', 'sourceArtifacts', 'gates'),
        'preflightChecks': ('template-workflow-mapping-known', 'gate-shape-valid', 'required-artifacts-present'),
    },
    'intent-router': {
        'requiredInputs': ('naturalLanguageRequest', 'targetRepo', 'userIntent'),
        'preflightChecks': ('candidate-workflow-suggested-only', 'orchestrator-approval-required', 'gates-not-satisfied-by-router'),
    },
    'artifact-next-actions': {
        'requiredInputs': ('currentArtifact', 'targetRepo', 'gates'),
        'preflightChecks': ('artifact-state-readable', 'next-action-does-not-skip-gates', 'required-artifacts-present'),
    },
    'illegal-transition-rules': {
        'requiredInputs': ('workflowId', 'sourceArtifacts', 'gates', 'executionMode'),
        'preflightChecks': ('required-artifacts-present', 'required-gates-satisfied', 'external-side-effects-authorized'),
    },
}

ILLEGAL_TRANSITION_RULES = (
    {
        'id': 'planning-requires-approved-spec',
        'blocks': 'writing-plans',
        'requiresArtifacts': ('approved-spec',),
        'requiresGates': ('spec-approval',),
        'description': 'Do not start planning until the spec artifact is approved.',
    },
    {
        'id': 'execution-requires-approved-plan-and-wiki-context',
        'blocks': 'executing-plans, subagent-driven-development',
        'requiresArtifacts': ('implementation-plan', 'wiki-context'),
        'requiresGates': (),
        'description': 'Do not execute implementation workflows without an approved plan and planning-selected wiki context.',
    },
    {
        'id': 'lanhu-handoff-requires-confirmation-gate',
        'blocks': 'brainstorming from lanhu-requirements',
        'requiresArtifacts': ('lanhu-evidence-package',),
        'requiresGates': ('lanhu-scope-confirmation',),
        'description': 'Do not hand Lanhu evidence to brainstorming until confirmationGate is clear and the package entrypoint is confirmed.',
    },
    {
        'id': 'debug-wiki-lookup-after-phase-one-evidence',
        'blocks': 'systematic-debugging wiki lookup',
        'requiresArtifacts': ('failure-evidence',),
        'requiresGates': (),
        'description': 'Do not call wiki-researcher at the start of debugging; use it only after Phase 1 evidence narrows the boundary.',
    },
    {
        'id': 'external-side-effects-require-authorization-gate',
        'blocks': 'commit, push, pull-request, shared-wiki-publish',
        'requiresArtifacts': (),
        'requiresGates': ('shared-wiki-publish-authorization', 'external-pr-creation-authorization'),
        'description': 'Do not perform visible external side effects until the matching authorization gate is satisfied.',
    },
    {
        'id': 'feature-work-cannot-start-at-execution',
        'blocks': 'feature or behavior change directly to executing-plans or subagent-driven-development',
        'requiresArtifacts': ('approved-spec', 'implementation-plan', 'wiki-context'),
        'requiresGates': ('spec-approval',),
        'description': 'Do not start feature or behavior-change implementation directly; it must come from approved spec, plan, and wiki context artifacts.',
    },
    {
        'id': 'update-wiki-is-not-completion-proof',
        'blocks': 'using update-wiki as implementation completion, verification, or release proof',
        'requiresArtifacts': ('completed-task-summary',),
        'requiresGates': (),
        'description': 'Do not treat update-wiki maintenance as proof that implementation, verification, finishing, or release is complete.',
    },
)

SCHEMAS = (
    'workflow-invocation.schema.json',
    'spec.schema.json',
    'implementation-plan.schema.json',
    'wiki-context-v3.schema.json',
    'source-truth-report.schema.json',
    'source-truth-constraints.schema.json',
    'lanhu-evidence-package.schema.json',
    'update-wiki-candidate.schema.json',
    'review-result.schema.json',
    'gate-state.schema.json',
    'sdd-task-graph.schema.json',
    'sdd-task-input.schema.json',
    'sdd-task-output.schema.json',
)

ARTIFACT_STORE_CONTRACT = {
    'storeId': 'multica-superpowers-artifact-store',
    'root': 'artifacts/superpowers',
    'pathPattern': 'artifacts/superpowers/{workflowId}/{runId}/{artifactType}/{name}',
    'statusValues': ('candidate', 'draft', 'reviewed', 'approved', 'current', 'missing', 'blocked', 'superseded'),
    'checksumAlgorithm': 'sha256',
    'requiresChecksumForStatuses': ('approved', 'current'),
    'writePolicy': 'role-output-only',
    'readPolicy': 'orchestrator-injected-source-artifacts-only',
    'externalStoreBoundary': 'Multica artifact API is the source of truth after registration; local files are build-time contracts until live API is available.',
}

ARTIFACT_CONTRACTS = (
    {'artifactType': 'spec', 'schemaFile': 'spec.schema.json', 'producedBy': ('brainstorming',), 'consumedBy': ('writing-plans', 'spec-document-reviewer'), 'requiredForWorkflows': ()},
    {'artifactType': 'approved-spec', 'schemaFile': 'spec.schema.json', 'producedBy': ('brainstorming',), 'consumedBy': ('writing-plans',), 'requiredForWorkflows': ('writing-plans',)},
    {'artifactType': 'implementation-plan', 'schemaFile': 'implementation-plan.schema.json', 'producedBy': ('writing-plans',), 'consumedBy': ('executing-plans', 'subagent-driven-development', 'plan-document-reviewer'), 'requiredForWorkflows': ('executing-plans', 'subagent-driven-development')},
    {'artifactType': 'wiki-context', 'schemaFile': 'wiki-context-v3.schema.json', 'producedBy': ('writing-plans',), 'consumedBy': ('executing-plans', 'subagent-driven-development'), 'requiredForWorkflows': ('executing-plans', 'subagent-driven-development')},
    {'artifactType': 'source-truth-report', 'schemaFile': 'source-truth-report.schema.json', 'producedBy': ('writing-plans', 'source-of-truth-verifier'), 'consumedBy': ('writing-plans', 'plan-document-reviewer'), 'requiredForWorkflows': ()},
    {'artifactType': 'source-truth-constraints', 'schemaFile': 'source-truth-constraints.schema.json', 'producedBy': ('writing-plans', 'source-of-truth-verifier'), 'consumedBy': ('executing-plans', 'subagent-driven-development', 'spec-compliance-reviewer'), 'requiredForWorkflows': ()},
    {'artifactType': 'lanhu-evidence-package', 'schemaFile': 'lanhu-evidence-package.schema.json', 'producedBy': ('lanhu-requirements',), 'consumedBy': ('brainstorming',), 'requiredForWorkflows': ()},
    {'artifactType': 'failure-evidence', 'schemaFile': '', 'producedBy': ('issue-template',), 'consumedBy': ('systematic-debugging', 'break-loop'), 'requiredForWorkflows': ('systematic-debugging',)},
    {'artifactType': 'update-wiki-candidate', 'schemaFile': 'update-wiki-candidate.schema.json', 'producedBy': ('break-loop', 'executing-plans', 'subagent-driven-development'), 'consumedBy': ('update-wiki',), 'requiredForWorkflows': ()},
    {'artifactType': 'review-result', 'schemaFile': 'review-result.schema.json', 'producedBy': ('spec-document-reviewer', 'plan-document-reviewer', 'spec-compliance-reviewer', 'code-quality-reviewer', 'code-reviewer'), 'consumedBy': ('subagent-driven-development',), 'requiredForWorkflows': ()},
    {'artifactType': 'final-code-review-result', 'schemaFile': 'review-result.schema.json', 'producedBy': ('code-reviewer',), 'consumedBy': ('finishing-a-development-branch',), 'requiredForWorkflows': ()},
    {'artifactType': 'sdd-task-output', 'schemaFile': 'sdd-task-output.schema.json', 'producedBy': ('subagent-driven-development',), 'consumedBy': ('spec-compliance-reviewer', 'code-quality-reviewer', 'code-reviewer'), 'requiredForWorkflows': ()},
    {'artifactType': 'completed-task-summary', 'schemaFile': '', 'producedBy': ('executing-plans', 'subagent-driven-development', 'systematic-debugging'), 'consumedBy': ('update-wiki',), 'requiredForWorkflows': ()},
    {'artifactType': 'shared-wiki-candidate', 'schemaFile': 'update-wiki-candidate.schema.json', 'producedBy': ('update-wiki',), 'consumedBy': ('publish-shared-wiki', 'shared-wiki-mcp'), 'requiredForWorkflows': ()},
    {'artifactType': 'verification-result', 'schemaFile': 'review-result.schema.json', 'producedBy': ('executing-plans', 'subagent-driven-development', 'systematic-debugging'), 'consumedBy': ('finishing-a-development-branch', 'break-loop', 'update-wiki'), 'requiredForWorkflows': ()},
)

MCP_EXAMPLES = (
    'required-capabilities.yaml',
    'lanhu-mcp.example.yaml',
    'shared-wiki-mcp.example.yaml',
    'github-mcp.example.yaml',
)

ISSUE_TEMPLATES = (
    '01-lanhu-requirements.md',
    '02-brainstorming.md',
    '03-writing-plan.md',
    '04-execute-plan.md',
    '05-debug-bug.md',
    '06-update-wiki.md',
    '07-shared-wiki-publish.md',
)

ISSUE_TEMPLATE_BINDINGS = (
    {
        'templateId': 'lanhu-requirements',
        'templateFile': '01-lanhu-requirements.md',
        'quickActionId': 'lanhu-requirement-intake',
        'defaultWorkflowId': 'lanhu-requirements',
        'allowedWorkflowIds': ('lanhu-requirements',),
        'requiredMetadata': ('targetRepo', 'userIntent', 'lanhuUrl or requirementsPath', 'role'),
        'requiredArtifacts': (),
        'optionalArtifacts': ('lanhu-page-tree',),
        'requiredStartGates': (),
        'managedGates': ('lanhu-scope-confirmation',),
    },
    {
        'templateId': 'brainstorming',
        'templateFile': '02-brainstorming.md',
        'quickActionId': 'start-brainstorming',
        'defaultWorkflowId': 'brainstorming',
        'allowedWorkflowIds': ('brainstorming',),
        'requiredMetadata': ('targetRepo', 'userIntent'),
        'requiredArtifacts': (),
        'optionalArtifacts': ('lanhu-evidence-package', 'requirements'),
        'requiredStartGates': (),
        'managedGates': ('design-approval',),
    },
    {
        'templateId': 'writing-plan',
        'templateFile': '03-writing-plan.md',
        'quickActionId': 'write-implementation-plan',
        'defaultWorkflowId': 'writing-plans',
        'allowedWorkflowIds': ('writing-plans',),
        'requiredMetadata': ('targetRepo', 'userIntent'),
        'requiredArtifacts': ('approved-spec',),
        'optionalArtifacts': ('lanhu-evidence-package',),
        'requiredStartGates': ('spec-approval',),
        'managedGates': (),
    },
    {
        'templateId': 'execute-plan',
        'templateFile': '04-execute-plan.md',
        'quickActionId': 'execute-approved-plan',
        'defaultWorkflowId': 'subagent-driven-development',
        'allowedWorkflowIds': ('subagent-driven-development', 'executing-plans'),
        'requiredMetadata': ('targetRepo', 'userIntent'),
        'requiredArtifacts': ('implementation-plan', 'wiki-context'),
        'optionalArtifacts': ('review-result',),
        'requiredStartGates': (),
        'managedGates': (),
    },
    {
        'templateId': 'debug-bug',
        'templateFile': '05-debug-bug.md',
        'quickActionId': 'debug-bug-or-test-failure',
        'defaultWorkflowId': 'systematic-debugging',
        'allowedWorkflowIds': ('systematic-debugging',),
        'requiredMetadata': ('targetRepo', 'userIntent', 'failureEvidence'),
        'requiredArtifacts': ('failure-evidence',),
        'optionalArtifacts': (),
        'requiredStartGates': (),
        'managedGates': (),
    },
    {
        'templateId': 'update-wiki',
        'templateFile': '06-update-wiki.md',
        'quickActionId': 'update-durable-knowledge',
        'defaultWorkflowId': 'update-wiki',
        'allowedWorkflowIds': ('update-wiki',),
        'requiredMetadata': ('targetRepo', 'userIntent', 'completedWorkSummary'),
        'requiredArtifacts': ('completed-task-summary',),
        'optionalArtifacts': ('implementation-plan', 'wiki-context', 'review-result'),
        'requiredStartGates': (),
        'managedGates': ('wiki-update-authorization',),
    },
    {
        'templateId': 'shared-wiki-publish',
        'templateFile': '07-shared-wiki-publish.md',
        'quickActionId': 'publish-shared-wiki',
        'defaultWorkflowId': 'publish-shared-wiki',
        'allowedWorkflowIds': ('publish-shared-wiki', 'shared-wiki-mcp'),
        'requiredMetadata': ('targetRepo', 'userIntent', 'sharedWikiTopic'),
        'requiredArtifacts': ('shared-wiki-candidate',),
        'optionalArtifacts': ('update-wiki-candidate',),
        'requiredStartGates': (),
        'managedGates': ('shared-wiki-publish-authorization', 'external-pr-creation-authorization'),
    },
)

ARTIFACT_NEXT_ACTIONS = (
    {
        'actionId': 'lanhu-package-to-brainstorming',
        'fromArtifactTypes': ('lanhu-evidence-package',),
        'requiredSatisfiedGates': ('lanhu-scope-confirmation',),
        'suggestedWorkflowId': 'brainstorming',
        'reason': 'A confirmed Lanhu evidence package can be used as brainstorming input.',
    },
    {
        'actionId': 'approved-spec-to-writing-plan',
        'fromArtifactTypes': ('approved-spec',),
        'requiredSatisfiedGates': ('spec-approval',),
        'suggestedWorkflowId': 'writing-plans',
        'reason': 'An approved spec can be converted into an implementation plan.',
    },
    {
        'actionId': 'reviewed-plan-to-sdd-execution',
        'fromArtifactTypes': ('implementation-plan', 'wiki-context'),
        'requiredSatisfiedGates': (),
        'suggestedWorkflowId': 'subagent-driven-development',
        'reason': 'A reviewed plan with wiki context and lightweight source-truth constraints when configured can be executed by the SDD task graph.',
    },
    {
        'actionId': 'final-review-to-finishing',
        'fromArtifactTypes': ('final-code-review-result',),
        'requiredSatisfiedGates': (),
        'suggestedWorkflowId': 'finishing-a-development-branch',
        'reason': 'A passed final review can move to finishing workflow.',
    },
    {
        'actionId': 'verified-work-to-update-wiki',
        'fromArtifactTypes': ('verification-result', 'completed-task-summary'),
        'requiredSatisfiedGates': (),
        'suggestedWorkflowId': 'update-wiki',
        'reason': 'Verified completed work may contain durable knowledge for update-wiki review.',
    },
    {
        'actionId': 'verified-bugfix-to-break-loop',
        'fromArtifactTypes': ('failure-evidence', 'verification-result'),
        'requiredSatisfiedGates': (),
        'suggestedWorkflowId': 'break-loop',
        'reason': 'A verified bug fix can be reviewed for repeat-failure prevention.',
    },
    {
        'actionId': 'shared-wiki-candidate-to-publish',
        'fromArtifactTypes': ('shared-wiki-candidate',),
        'requiredSatisfiedGates': ('shared-wiki-publish-authorization',),
        'suggestedWorkflowId': 'publish-shared-wiki',
        'reason': 'A shared wiki candidate requires publish authorization before external side effects.',
    },
)

AUTOPILOTS = (
    'wiki-health-check.md',
    'release-check.md',
)

AUTOPILOT_CONTRACTS = (
    {
        'autopilotId': 'wiki-health-check',
        'templateFile': 'wiki-health-check.md',
        'allowedActions': ('read-wiki-indexes', 'validate-section-indexes', 'report-stale-wiki-health'),
        'forbiddenActions': ('brainstorming', 'writing-plans', 'implementation', 'update-wiki-write', 'shared-wiki-publish', 'pull-request-create'),
        'requiredCapabilities': ('local-filesystem', 'artifact-store'),
        'autoExecute': False,
    },
    {
        'autopilotId': 'release-check',
        'templateFile': 'release-check.md',
        'allowedActions': ('verify-runtime-contracts', 'run-local-smoke-tests', 'report-release-readiness'),
        'forbiddenActions': ('brainstorming', 'writing-plans', 'implementation', 'update-wiki-write', 'shared-wiki-publish', 'pull-request-create'),
        'requiredCapabilities': ('local-filesystem', 'shell-git', 'artifact-store'),
        'autoExecute': False,
    },
)

ROLE_TASK_CONTRACT = {
    'contractId': 'multica-superpowers-role-task-dispatch',
    'createdBy': 'superpowers-orchestrator',
    'freshContext': 'required',
    'inputPolicy': 'orchestrator-injected-source-artifacts-only',
    'outputPolicy': 'declared-output-artifacts-only',
    'sharedStatePolicy': 'no-direct-shared-state-writes',
    'gatePolicy': 'role-tasks-must-not-advance-gates',
    'requiredFields': ('taskId', 'workflowId', 'roleAgent', 'freshContext', 'sourceArtifacts', 'expectedOutputArtifacts'),
    'forbiddenActions': ('advance-gates-directly', 'skip-orchestrator-preflight', 'read-unscoped-artifacts', 'write-undeclared-artifacts', 'reuse-prior-task-context'),
    'liveApiBoundary': 'Local validators define role task dispatch contracts until Multica task API integration is available.',
}

SQUAD_CONTRACTS = (
    {
        'squadId': 'superpowers-delivery-squad',
        'displayName': 'Superpowers Delivery Squad',
        'leaderAgent': 'superpowers-orchestrator',
        'memberAgents': EXPECTED_ROLE_AGENTS,
        'routingPolicy': 'orchestrator-gated',
        'freshContextRequired': True,
        'gateOwner': 'superpowers-orchestrator',
        'sharedStateWritePolicy': 'orchestrator-serialized',
        'forbiddenMemberActions': ('advance-gates-directly', 'skip-orchestrator-preflight', 'merge-prs', 'publish-shared-wiki-without-gate'),
    },
)

VALIDATORS = (
    'wiki-health-check.md',
    'runtime-capability-check.md',
    'neutrality-guard.md',
)

FORBIDDEN_GENERATED_STRINGS = (
    ADAPTER_PLUGIN_ROOT_PLACEHOLDER,
    'python3 overlays/scripts/',
    'python3 superpowers/scripts/',
    'python3 scripts/wiki_',
    'python3 scripts/wiki-',
)

SCRIPT_EXECUTABLES = (
    'update-wiki.py',
    'wiki-context.py',
    'wiki_context_render.py',
    'wiki_settings.py',
    'source_truth_settings.py',
    'source_truth_render.py',
    'wiki_import.py',
    'init-wiki.py',
    'wiki_update_check.py',
    'wiki_select_target.py',
    'wiki_apply_update.py',
    'wiki_section.py',
    'wiki_read_section.py',
    'wiki_generate_section_index.py',
    'wiki_migrate_helper.py',
    'lanhu_settings.py',
)
