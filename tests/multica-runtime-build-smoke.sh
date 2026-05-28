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

"$ROOT/manage.sh" build-multica-runtime "$SUPERPOWERS_SOURCE" "$ROOT" "$RUNTIME_ROOT"
"$ROOT/manage.sh" verify-multica-runtime "$RUNTIME_ROOT"

DRIFT_RUNTIME="$TMP/drift-runtime"
cp -R "$RUNTIME_ROOT" "$DRIFT_RUNTIME"
python3 - <<'PY' "$DRIFT_RUNTIME"
from pathlib import Path
import sys
path = Path(sys.argv[1]) / 'dist' / 'workflows' / 'subagent-driven-development.workflow.yaml'
text = path.read_text(encoding='utf-8')
old = 'executionMode: "multica-sdd-task-graph"'
new = 'executionMode: "inline-sequential"'
if old not in text:
    raise SystemExit(f'Missing expected executionMode in {path}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
PY
if "$ROOT/manage.sh" verify-multica-runtime "$DRIFT_RUNTIME" > "$TMP/drift-verify.out" 2>&1; then
  printf 'Drifted Multica runtime unexpectedly passed verification\n' >&2
  exit 1
fi

python3 - <<'PY' "$RUNTIME_ROOT" "$ROOT"
from pathlib import Path
import json
import sys
root = Path(sys.argv[1])
adapter_root = Path(sys.argv[2])
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
adapter_manifest = json.loads((adapter_root / 'manifest.json').read_text(encoding='utf-8'))
tool_manifest = json.loads((root / 'dist' / 'tools' / 'tool-manifest.json').read_text(encoding='utf-8'))
required_caps = {'local-filesystem', 'shell-git', 'artifact-store', 'task-isolation', 'mcp-client'}
missing_caps = required_caps - set(manifest.get('requiredCapabilities', []))
if missing_caps:
    raise SystemExit(f'Missing runtime capabilities: {sorted(missing_caps)}')
if not manifest.get('workflows'):
    raise SystemExit('Runtime manifest missing workflows')
if not manifest.get('roleAgents'):
    raise SystemExit('Runtime manifest missing roleAgents')
squad_contracts = json.loads((root / 'dist' / 'multica' / 'squads' / 'squad-contracts.json').read_text(encoding='utf-8'))
squads_by_id = {item.get('squadId'): item for item in squad_contracts.get('contracts', [])}
if squads_by_id.get('superpowers-delivery-squad', {}).get('leaderAgent') != 'superpowers-orchestrator':
    raise SystemExit('Superpowers delivery squad must be led by superpowers-orchestrator')
if squads_by_id.get('superpowers-delivery-squad', {}).get('freshContextRequired') is not True:
    raise SystemExit('Superpowers delivery squad must require fresh contexts')
if manifest.get('squadContracts') != squad_contracts.get('contracts'):
    raise SystemExit('Runtime manifest squadContracts mismatch')
autopilot_contracts = json.loads((root / 'dist' / 'multica' / 'autopilots' / 'autopilot-contracts.json').read_text(encoding='utf-8'))
autopilots_by_id = {item.get('autopilotId'): item for item in autopilot_contracts.get('contracts', [])}
if autopilots_by_id.get('wiki-health-check', {}).get('autoExecute') is not False:
    raise SystemExit('Wiki health autopilot must not auto-execute')
if 'implementation' not in autopilots_by_id.get('release-check', {}).get('forbiddenActions', []):
    raise SystemExit('Release-check autopilot must forbid implementation')
if manifest.get('autopilotContracts') != autopilot_contracts.get('contracts'):
    raise SystemExit('Runtime manifest autopilotContracts mismatch')
artifact_contracts = json.loads((root / 'dist' / 'schemas' / 'artifact-contracts.json').read_text(encoding='utf-8'))
artifacts_by_type = {item.get('artifactType'): item for item in artifact_contracts.get('contracts', [])}
artifact_store = json.loads((root / 'dist' / 'preflight' / 'artifact-store-contract.json').read_text(encoding='utf-8'))
if artifact_store.get('pathPattern') != 'artifacts/superpowers/{workflowId}/{runId}/{artifactType}/{name}':
    raise SystemExit('Artifact store path pattern mismatch')
if artifact_store.get('requiresChecksumForStatuses') != ['approved', 'current']:
    raise SystemExit('Artifact store checksum status contract mismatch')
if artifact_store.get('writePolicy') != 'role-output-only':
    raise SystemExit('Artifact store write policy mismatch')
if artifact_store.get('artifactContracts') != artifact_contracts.get('contracts'):
    raise SystemExit('Artifact store artifactContracts mismatch')
if manifest.get('artifactStoreContract', {}).get('storeId') != artifact_store.get('storeId'):
    raise SystemExit('Runtime manifest artifactStoreContract mismatch')
if artifacts_by_type.get('implementation-plan', {}).get('schemaFile') != 'implementation-plan.schema.json':
    raise SystemExit('Implementation plan artifact must bind to implementation-plan schema')
if artifacts_by_type.get('source-truth-report', {}).get('schemaFile') != 'source-truth-report.schema.json':
    raise SystemExit('Source-truth report artifact must bind to source-truth-report schema')
if artifacts_by_type.get('source-truth-constraints', {}).get('schemaFile') != 'source-truth-constraints.schema.json':
    raise SystemExit('Source-truth constraints artifact must bind to source-truth-constraints schema')
if 'subagent-driven-development' not in artifacts_by_type.get('wiki-context', {}).get('requiredForWorkflows', []):
    raise SystemExit('Wiki context artifact must be required for SDD workflow')
if manifest.get('artifactContracts') != artifact_contracts.get('contracts'):
    raise SystemExit('Runtime manifest artifactContracts mismatch')
for schema_name, required_field in {
    'spec.schema.json': 'decisions',
    'implementation-plan.schema.json': 'referencedProjectWiki',
    'source-truth-report.schema.json': 'summary',
    'source-truth-constraints.schema.json': 'constraintSets',
    'lanhu-evidence-package.schema.json': 'confirmationGate',
    'update-wiki-candidate.schema.json': 'candidates',
    'review-result.schema.json': 'findings',
}.items():
    schema = json.loads((root / 'dist' / 'schemas' / schema_name).read_text(encoding='utf-8'))
    if required_field not in schema.get('required', []):
        raise SystemExit(f'{schema_name} missing required artifact field: {required_field}')
for agent_file in ('superpowers-orchestrator.md', 'wiki-researcher.md', 'lanhu-frontend-requirements-analyst.md', 'spec-document-reviewer.md'):
    agent_text = (root / 'dist' / 'agents' / agent_file).read_text(encoding='utf-8')
    if "Infer the user's preferred language" not in agent_text:
        raise SystemExit(f'Role agent missing user-facing language inference rule: {agent_file}')
role_contracts = json.loads((root / 'dist' / 'agents' / 'role-agent-contracts.json').read_text(encoding='utf-8'))
if role_contracts.get('freshContext') != 'required':
    raise SystemExit('Role agent contracts must require fresh context')
roles_by_id = {item.get('agentId'): item for item in role_contracts.get('contracts', [])}
if roles_by_id.get('implementer', {}).get('mayAdvanceGates') is not False:
    raise SystemExit('Implementer must not advance gates')
source_truth_role = roles_by_id.get('source-of-truth-verifier', {})
if source_truth_role.get('mayPerformExternalSideEffects') is not False or source_truth_role.get('mayAdvanceGates') is not False:
    raise SystemExit('Source-of-truth verifier must not advance gates or perform external side effects')
if 'source-truth-constraints' not in roles_by_id.get('implementer', {}).get('inputArtifacts', []):
    raise SystemExit('Implementer role contract must accept source-truth constraints')
if 'wiki-context-render' not in roles_by_id.get('implementer', {}).get('toolAccess', []):
    raise SystemExit('Implementer role contract must allow wiki context render')
if 'source-truth-render' not in roles_by_id.get('implementer', {}).get('toolAccess', []):
    raise SystemExit('Implementer role contract must allow source-truth render')
if roles_by_id.get('shared-wiki-publisher', {}).get('mayPerformExternalSideEffects') is not True:
    raise SystemExit('Shared wiki publisher must be the explicit external-side-effect role')
role_task = json.loads((root / 'dist' / 'preflight' / 'role-task-contract.json').read_text(encoding='utf-8'))
if role_task.get('createdBy') != 'superpowers-orchestrator' or role_task.get('freshContext') != 'required':
    raise SystemExit('Role task dispatch contract must be orchestrator-created with fresh context')
if role_task.get('roleAgentContracts') != role_contracts.get('contracts'):
    raise SystemExit('Role task roleAgentContracts mismatch')
if 'reuse-prior-task-context' not in role_task.get('forbiddenActions', []):
    raise SystemExit('Role task contract must forbid context reuse')
if manifest.get('roleTaskContract', {}).get('contractId') != role_task.get('contractId'):
    raise SystemExit('Runtime manifest roleTaskContract mismatch')
if manifest.get('roleAgentContracts') != role_contracts.get('contracts'):
    raise SystemExit('Runtime manifest roleAgentContracts mismatch')
gate_contracts = json.loads((root / 'dist' / 'gates' / 'gate-contracts.json').read_text(encoding='utf-8'))
if gate_contracts.get('statusValues') != ['pending', 'satisfied', 'blocked']:
    raise SystemExit('Gate contracts status values mismatch')
gate_transition = json.loads((root / 'dist' / 'preflight' / 'gate-transition-contract.json').read_text(encoding='utf-8'))
if gate_transition.get('advancePolicy') != 'gate-owner-or-orchestrator-only':
    raise SystemExit('Gate transition advance policy mismatch')
transition_edges = {(item.get('from'), item.get('to')) for item in gate_transition.get('allowedTransitions', [])}
if ('pending', 'satisfied') not in transition_edges or ('blocked', 'pending') not in transition_edges:
    raise SystemExit('Gate transition allowed edges mismatch')
if gate_transition.get('gateContracts') != gate_contracts.get('contracts'):
    raise SystemExit('Gate transition gateContracts mismatch')
if manifest.get('gateTransitionContract', {}).get('contractId') != gate_transition.get('contractId'):
    raise SystemExit('Runtime manifest gateTransitionContract mismatch')
gates_by_id = {item.get('gateId'): item for item in gate_contracts.get('contracts', [])}
if gates_by_id.get('spec-approval', {}).get('requiredArtifacts') != ['approved-spec']:
    raise SystemExit('Spec approval gate must require approved-spec artifact')
if gates_by_id.get('shared-wiki-publish-authorization', {}).get('blocksExternalSideEffects') is not True:
    raise SystemExit('Shared wiki publish gate must block external side effects')
if manifest.get('gateContracts') != gate_contracts.get('contracts'):
    raise SystemExit('Runtime manifest gateContracts mismatch')
gate_state_schema = json.loads((root / 'dist' / 'schemas' / 'gate-state.schema.json').read_text(encoding='utf-8'))
if gate_state_schema.get('properties', {}).get('status', {}).get('enum') != ['pending', 'satisfied', 'blocked']:
    raise SystemExit('Gate state schema status enum mismatch')
expected_scripts = {f"scripts/{Path(rel).name}" for rel in adapter_manifest.get('installedPaths', []) if rel.startswith('scripts/')}
tool_paths = {item.get('path') for item in tool_manifest.get('scripts', [])}
if tool_paths != expected_scripts:
    raise SystemExit(f'Tool manifest scripts mismatch: missing={sorted(expected_scripts - tool_paths)} extra={sorted(tool_paths - expected_scripts)}')
manifest_tool_paths = {item.get('path') for item in manifest.get('toolScripts', [])}
if manifest_tool_paths != expected_scripts:
    raise SystemExit(f'Runtime manifest toolScripts mismatch: missing={sorted(expected_scripts - manifest_tool_paths)} extra={sorted(manifest_tool_paths - expected_scripts)}')
expected_validators = {'validators/runtime_capability_preflight.py', 'validators/workflow_invocation_validate.py', 'validators/artifact_next_action_suggest.py', 'validators/intent_router_suggest.py', 'validators/gate_state_validate.py', 'validators/gate_transition_validate.py', 'validators/artifact_store_validate.py', 'validators/role_task_validate.py', 'validators/issue_template_invocation_build.py', 'validators/compatibility_command_invocation_build.py'}
tool_validator_paths = {item.get('path') for item in tool_manifest.get('validatorScripts', [])}
if tool_validator_paths != expected_validators:
    raise SystemExit(f'Tool manifest validatorScripts mismatch: missing={sorted(expected_validators - tool_validator_paths)} extra={sorted(tool_validator_paths - expected_validators)}')
manifest_validator_paths = {item.get('path') for item in manifest.get('validatorScripts', [])}
if manifest_validator_paths != expected_validators:
    raise SystemExit(f'Runtime manifest validatorScripts mismatch: missing={sorted(expected_validators - manifest_validator_paths)} extra={sorted(manifest_validator_paths - expected_validators)}')
expected_preflight = {'dist/preflight/runtime-capabilities.json', 'dist/preflight/workflow-invocation-contract.json', 'dist/preflight/artifact-store-contract.json', 'dist/preflight/gate-transition-contract.json', 'dist/preflight/role-task-contract.json'}
manifest_preflight_paths = {item.get('path') for item in manifest.get('preflightArtifacts', [])}
if manifest_preflight_paths != expected_preflight:
    raise SystemExit(f'Runtime manifest preflightArtifacts mismatch: missing={sorted(expected_preflight - manifest_preflight_paths)} extra={sorted(manifest_preflight_paths - expected_preflight)}')
compatibility_commands = json.loads((root / 'dist' / 'triggers' / 'compatibility-commands.json').read_text(encoding='utf-8'))
issue_bindings = json.loads((root / 'dist' / 'triggers' / 'issue-template-bindings.json').read_text(encoding='utf-8'))
intent_rules = json.loads((root / 'dist' / 'triggers' / 'intent-router-rules.json').read_text(encoding='utf-8'))
next_actions = json.loads((root / 'dist' / 'triggers' / 'artifact-next-actions.json').read_text(encoding='utf-8'))
if compatibility_commands.get('normalizesTo') != 'WorkflowInvocation':
    raise SystemExit('Compatibility commands must normalize to WorkflowInvocation')
if issue_bindings.get('normalizesTo') != 'WorkflowInvocation':
    raise SystemExit('Issue template bindings must normalize to WorkflowInvocation')
if intent_rules.get('normalizesTo') != 'WorkflowInvocation' or intent_rules.get('suggestOnly') is not True:
    raise SystemExit('Intent router rules must normalize to WorkflowInvocation as suggest-only')
if next_actions.get('normalizesTo') != 'WorkflowInvocation' or next_actions.get('autoExecute') is not False:
    raise SystemExit('Artifact next actions must normalize to WorkflowInvocation without auto-execution')
commands_by_id = {item.get('commandId'): item for item in compatibility_commands.get('commands', [])}
if commands_by_id.get('write-plan', {}).get('workflowId') != 'writing-plans':
    raise SystemExit('Compatibility write-plan command must route to writing-plans')
intent_by_id = {item.get('intentId'): item for item in intent_rules.get('rules', [])}
if intent_by_id.get('feature-or-behavior-change', {}).get('candidateWorkflowId') != 'brainstorming':
    raise SystemExit('Feature intent router rule must suggest brainstorming')
bindings_by_id = {item.get('templateId'): item for item in issue_bindings.get('bindings', [])}
if bindings_by_id.get('execute-plan', {}).get('defaultWorkflowId') != 'subagent-driven-development':
    raise SystemExit('Execute-plan issue template must default to SDD execution')
if 'executing-plans' not in bindings_by_id.get('execute-plan', {}).get('allowedWorkflowIds', []):
    raise SystemExit('Execute-plan issue template must allow inline execution fallback')
actions_by_id = {item.get('actionId'): item for item in next_actions.get('actions', [])}
if actions_by_id.get('reviewed-plan-to-sdd-execution', {}).get('suggestedWorkflowId') != 'subagent-driven-development':
    raise SystemExit('Reviewed-plan next action must suggest SDD execution')
if actions_by_id.get('shared-wiki-candidate-to-publish', {}).get('requiredSatisfiedGates') != ['shared-wiki-publish-authorization']:
    raise SystemExit('Shared wiki publish next action must require publish authorization gate')
contract = json.loads((root / 'dist' / 'preflight' / 'workflow-invocation-contract.json').read_text(encoding='utf-8'))
if contract.get('issueTemplateBindings') != issue_bindings.get('bindings'):
    raise SystemExit('WorkflowInvocation contract issueTemplateBindings mismatch')
if contract.get('artifactNextActions') != next_actions.get('actions'):
    raise SystemExit('WorkflowInvocation contract artifactNextActions mismatch')
for template_file in ('01-lanhu-requirements.md', '04-execute-plan.md', '07-shared-wiki-publish.md'):
    text = (root / 'dist' / 'multica' / 'issue-templates' / template_file).read_text(encoding='utf-8')
    if 'defaultWorkflowId:' not in text or 'WorkflowInvocation candidate' not in text:
        raise SystemExit(f'Issue template missing binding metadata: {template_file}')
graph = json.loads((root / 'dist' / 'task-graphs' / 'subagent-driven-development.task-graph.json').read_text(encoding='utf-8'))
if graph.get('workflowId') != 'subagent-driven-development':
    raise SystemExit('SDD task graph workflowId mismatch')
if 'wiki_context_render.py' not in json.dumps(graph, ensure_ascii=False):
    raise SystemExit('SDD task graph missing wiki_context_render.py reference')
graph_text = json.dumps(graph, ensure_ascii=False)
if 'source_truth_render.py' not in graph_text:
    raise SystemExit('SDD task graph missing source_truth_render.py reference')
for required in ('--fingerprint-preflight', '--task-id <task-id>', 'fullReport', 'capture-renderer-stdout', 'role-task-prompt', 'forbidden-rendered-markdown-context', '## Rendered Wiki Constraints for This Task', '## Rendered Source-of-Truth Constraints for This Task', '.claude-*-source-task*-impl.md'):
    if required not in graph_text:
        raise SystemExit(f'SDD task graph missing source-truth/render delivery contract: {required}')
for node in graph.get('nodes', []):
    if 'rendered-markdown' in json.dumps(node.get('outputArtifacts', []), ensure_ascii=False):
        raise SystemExit('SDD task graph must not output rendered Markdown context artifacts')
nodes = {node.get('nodeId'): node for node in graph.get('nodes', [])}
for node_id in ('implementer', 'spec-compliance-reviewer', 'code-quality-reviewer', 'code-reviewer-final'):
    if node_id not in nodes:
        raise SystemExit(f'SDD task graph missing node: {node_id}')
    if nodes[node_id].get('freshContext') != 'required':
        raise SystemExit(f'SDD task graph node does not require fresh context: {node_id}')
edges = {(edge.get('from'), edge.get('to'), edge.get('condition')) for edge in graph.get('edges', [])}
if ('spec-compliance-reviewer', 'implementer', 'review-failed') not in edges:
    raise SystemExit('SDD task graph missing reviewer failure loop')
for rel in sorted(tool_paths):
    if not (root / 'dist' / 'tools' / rel).is_file():
        raise SystemExit(f'Tool manifest references missing file: {rel}')
contract = root / 'dist' / 'tools' / 'contracts' / 'wiki-context-v3.example.jsonc'
if not contract.is_file():
    raise SystemExit('Missing wiki context example contract in runtime tools/contracts')
if 'contracts/wiki-context-v3.example.jsonc' in tool_paths:
    raise SystemExit('Wiki context example contract must not be listed as a runnable tool script')
planning_agent = (root / 'dist' / 'agents' / 'planning-agent.md').read_text(encoding='utf-8')
for required in ('wiki-context-v3.example.jsonc', '--validate-only --strict', 'Do not inspect wiki_context_render.py to infer the sidecar format'):
    if required not in planning_agent:
        raise SystemExit(f'Planning agent missing wiki context contract instruction: {required}')
required_snapshots = [
    root / 'source' / 'superpower-adapter' / 'overlays' / 'agents' / 'wiki-researcher.md',
    root / 'source' / 'superpower-adapter' / 'overlays' / 'agents' / 'source-of-truth-verifier.md',
    root / 'source' / 'superpower-adapter' / 'overlays' / 'skills' / 'update-wiki' / 'SKILL.md',
    root / 'source' / 'superpower-adapter' / 'overlays' / 'scripts' / 'wiki_context_render.py',
    root / 'source' / 'superpower-adapter' / 'overlays' / 'scripts' / 'wiki_settings.py',
    root / 'source' / 'superpower-adapter' / 'overlays' / 'scripts' / 'source_truth_render.py',
    root / 'source' / 'superpowers' / 'skills' / 'writing-plans' / 'SKILL.md',
]
missing_snapshots = [path.as_posix() for path in required_snapshots if not path.exists()]
if missing_snapshots:
    raise SystemExit(f'Missing runtime source snapshots: {missing_snapshots}')
PY

if grep -R --exclude='manifest.json' -Fq '__SUPERPOWER_ADAPTER_PLUGIN_ROOT__' "$RUNTIME_ROOT/dist"; then
  printf 'Unresolved plugin-root placeholder in generated dist\n' >&2
  exit 1
fi
if grep -R -Eq 'python3 (overlays/scripts|superpowers/scripts|scripts/wiki[_-])' "$RUNTIME_ROOT/dist"; then
  printf 'Forbidden source/project-relative script path in generated dist\n' >&2
  exit 1
fi
if ! grep -R -Fq '${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools/scripts/wiki_context_render.py' "$RUNTIME_ROOT/dist/workflows"; then
  printf 'Missing Multica runtime-root wiki_context_render.py reference\n' >&2
  exit 1
fi
if ! grep -R -Fq '${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools/scripts/source_truth_render.py' "$RUNTIME_ROOT/dist"; then
  printf 'Missing Multica runtime-root source_truth_render.py reference\n' >&2
  exit 1
fi

CAP_ARGS=(
  --available-capability local-filesystem
  --available-capability shell-git
  --available-capability artifact-store
  --available-capability task-isolation
  --available-capability mcp-client
)

MULTICA_SUPERPOWERS_RUNTIME_ROOT="$RUNTIME_ROOT" \
  python3 "$RUNTIME_ROOT/dist/tools/validators/runtime_capability_preflight.py" "$RUNTIME_ROOT" "${CAP_ARGS[@]}" \
  > "$TMP/runtime-capability-preflight.json"

python3 - <<'PY' "$TMP/valid-sdd-invocation.json" "$TMP/invalid-sdd-invocation.json" "$TMP/valid-template-invocation.json" "$TMP/invalid-template-invocation.json" "$TMP/artifact-state.json" "$TMP/valid-lanhu-invocation.json" "$TMP/satisfied-gate-state.json" "$TMP/invalid-gate-state.json"
from pathlib import Path
import json
import sys
valid_path = Path(sys.argv[1])
invalid_path = Path(sys.argv[2])
template_path = Path(sys.argv[3])
invalid_template_path = Path(sys.argv[4])
artifact_state_path = Path(sys.argv[5])
lanhu_path = Path(sys.argv[6])
satisfied_gate_path = Path(sys.argv[7])
invalid_gate_path = Path(sys.argv[8])
base = {
    'workflowId': 'subagent-driven-development',
    'triggerSource': 'artifact-next-action',
    'artifactNextActionId': 'reviewed-plan-to-sdd-execution',
    'targetRepo': '/tmp/example-target-repo',
    'userIntent': 'Execute an approved implementation plan with the SDD task graph.',
    'sourceArtifacts': [
        {'path': 'docs/superpowers/plans/example-plan.md', 'type': 'implementation-plan', 'status': 'approved'},
        {'path': 'docs/superpowers/plans/example-plan.wiki-context.json', 'type': 'wiki-context', 'status': 'current'},
    ],
    'gates': {'required': [], 'satisfied': []},
    'requiredCapabilities': ['local-filesystem', 'shell-git', 'artifact-store', 'task-isolation', 'mcp-client'],
    'mcpRequirements': [],
    'executionMode': 'multica-sdd-task-graph',
}
valid_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
invalid = dict(base)
invalid['sourceArtifacts'] = [item for item in base['sourceArtifacts'] if item['type'] != 'wiki-context']
invalid_path.write_text(json.dumps(invalid, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
template = {
    'workflowId': 'writing-plans',
    'triggerSource': 'issue-template',
    'issueTemplateId': 'writing-plan',
    'targetRepo': '/tmp/example-target-repo',
    'userIntent': 'Write an implementation plan from an approved spec.',
    'sourceArtifacts': [
        {'path': 'docs/superpowers/specs/example-spec.md', 'type': 'approved-spec', 'status': 'approved'},
    ],
    'gates': {'required': ['spec-approval'], 'satisfied': ['spec-approval']},
    'requiredCapabilities': ['local-filesystem', 'shell-git', 'artifact-store', 'task-isolation', 'mcp-client'],
    'mcpRequirements': [],
    'executionMode': 'planning',
}
template_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
invalid_template = dict(template)
invalid_template['workflowId'] = 'brainstorming'
invalid_template['executionMode'] = 'brainstorming'
invalid_template_path.write_text(json.dumps(invalid_template, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
artifact_state = {
    'artifacts': [
        {'type': 'approved-spec', 'path': 'docs/superpowers/specs/example-spec.md'},
        {'type': 'implementation-plan', 'path': 'docs/superpowers/plans/example-plan.md'},
        {'type': 'wiki-context', 'path': 'docs/superpowers/plans/example-plan.wiki-context.json'},
    ],
    'gates': {'satisfied': ['spec-approval']},
}
artifact_state_path.write_text(json.dumps(artifact_state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
lanhu = {
    'workflowId': 'lanhu-requirements',
    'triggerSource': 'issue-template',
    'issueTemplateId': 'lanhu-requirements',
    'targetRepo': '/tmp/example-target-repo',
    'userIntent': 'Process a Lanhu requirement link.',
    'sourceArtifacts': [],
    'gates': {'required': [], 'satisfied': []},
    'requiredCapabilities': ['local-filesystem', 'shell-git', 'artifact-store', 'task-isolation', 'mcp-client'],
    'mcpRequirements': [{'name': 'lanhu-mcp', 'requiredFor': 'lanhu-requirements', 'optionalOtherwise': True}],
    'executionMode': 'standalone',
}
lanhu_path.write_text(json.dumps(lanhu, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
satisfied_gate = {
    'schemaVersion': 1,
    'gateId': 'spec-approval',
    'status': 'satisfied',
    'ownerRoleAgent': 'superpowers-orchestrator',
    'requiredArtifacts': ['approved-spec'],
    'satisfiedBy': ['spec-document-reviewer-passed', 'user-approved-spec'],
    'evidence': [{'kind': 'user-approval', 'reference': 'issue-comment-1'}],
}
satisfied_gate_path.write_text(json.dumps(satisfied_gate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
invalid_gate = dict(satisfied_gate)
invalid_gate['evidence'] = []
invalid_gate_path.write_text(json.dumps(invalid_gate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY

python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/valid-sdd-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/valid-sdd-preflight.json"

if python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/invalid-sdd-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/invalid-sdd-preflight.json" 2>&1; then
  printf 'Invalid SDD WorkflowInvocation unexpectedly passed preflight\n' >&2
  exit 1
fi

python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/valid-template-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/valid-template-preflight.json"

if python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/invalid-template-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/invalid-template-preflight.json" 2>&1; then
  printf 'Invalid issue-template WorkflowInvocation unexpectedly passed preflight\n' >&2
  exit 1
fi

if python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/valid-lanhu-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/lanhu-missing-mcp-preflight.json" 2>&1; then
  printf 'Lanhu WorkflowInvocation unexpectedly passed without available Lanhu MCP\n' >&2
  exit 1
fi

python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/valid-lanhu-invocation.json" "${CAP_ARGS[@]}" --available-mcp lanhu-mcp \
  > "$TMP/lanhu-available-mcp-preflight.json"

python3 "$RUNTIME_ROOT/dist/tools/validators/gate_state_validate.py" \
  "$RUNTIME_ROOT" "$TMP/satisfied-gate-state.json" \
  > "$TMP/satisfied-gate-preflight.json"

if python3 "$RUNTIME_ROOT/dist/tools/validators/gate_state_validate.py" \
  "$RUNTIME_ROOT" "$TMP/invalid-gate-state.json" \
  > "$TMP/invalid-gate-preflight.json" 2>&1; then
  printf 'Invalid satisfied gate state unexpectedly passed preflight\n' >&2
  exit 1
fi

python3 "$RUNTIME_ROOT/dist/tools/validators/gate_transition_validate.py" \
  "$RUNTIME_ROOT" \
  --gate-id spec-approval \
  --from-status pending \
  --to-status satisfied \
  --actor-role superpowers-orchestrator \
  --evidence issue-comment-1 \
  > "$TMP/valid-gate-transition-preflight.json"

if python3 "$RUNTIME_ROOT/dist/tools/validators/gate_transition_validate.py" \
  "$RUNTIME_ROOT" \
  --gate-id spec-approval \
  --from-status satisfied \
  --to-status blocked \
  --actor-role implementer \
  --evidence issue-comment-2 \
  > "$TMP/invalid-gate-transition-preflight.json" 2>&1; then
  printf 'Forbidden gate transition unexpectedly passed preflight\n' >&2
  exit 1
fi

if python3 "$RUNTIME_ROOT/dist/tools/validators/gate_transition_validate.py" \
  "$RUNTIME_ROOT" \
  --gate-id shared-wiki-publish-authorization \
  --from-status pending \
  --to-status blocked \
  --actor-role shared-wiki-publisher \
  --evidence issue-comment-3 \
  --external-side-effect \
  > "$TMP/invalid-side-effect-gate-transition.json" 2>&1; then
  printf 'External side-effect gate transition unexpectedly passed without satisfied gate\n' >&2
  exit 1
fi

python3 - <<'PY' "$TMP/valid-role-task.json" "$TMP/invalid-role-task.json"
from pathlib import Path
import json
import sys
valid = {
    'taskId': 'sdd-implementer-1',
    'workflowId': 'subagent-driven-development',
    'roleAgent': 'implementer',
    'createdBy': 'superpowers-orchestrator',
    'freshContext': 'required',
    'sourceArtifacts': [
        {'type': 'implementation-plan', 'path': 'artifacts/superpowers/subagent-driven-development/run-1/implementation-plan/example.md'},
        {'type': 'wiki-context', 'path': 'artifacts/superpowers/subagent-driven-development/run-1/wiki-context/example.json'},
    ],
    'expectedOutputArtifacts': ['sdd-task-output'],
    'forbiddenActions': ['advance-gates-directly', 'skip-orchestrator-preflight', 'read-unscoped-artifacts', 'write-undeclared-artifacts', 'reuse-prior-task-context'],
}
Path(sys.argv[1]).write_text(json.dumps(valid, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
invalid = dict(valid)
invalid['freshContext'] = 'reuse-previous-context'
invalid['expectedOutputArtifacts'] = ['review-result']
Path(sys.argv[2]).write_text(json.dumps(invalid, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
python3 "$RUNTIME_ROOT/dist/tools/validators/role_task_validate.py" \
  "$RUNTIME_ROOT" "$TMP/valid-role-task.json" \
  > "$TMP/valid-role-task-preflight.json"
if python3 "$RUNTIME_ROOT/dist/tools/validators/role_task_validate.py" \
  "$RUNTIME_ROOT" "$TMP/invalid-role-task.json" \
  > "$TMP/invalid-role-task-preflight.json" 2>&1; then
  printf 'Invalid role task unexpectedly passed preflight\n' >&2
  exit 1
fi

python3 - <<'PY' "$TMP/draft-artifact-reference.json"
from pathlib import Path
import json
import sys
Path(sys.argv[1]).write_text(json.dumps({
    'type': 'implementation-plan',
    'path': 'artifacts/superpowers/writing-plans/run-1/implementation-plan/example-plan.md',
    'status': 'draft',
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
python3 "$RUNTIME_ROOT/dist/tools/validators/artifact_store_validate.py" \
  "$RUNTIME_ROOT" "$TMP/draft-artifact-reference.json" \
  --producer writing-plans \
  --consumer subagent-driven-development \
  > "$TMP/valid-artifact-store-preflight.json"

if python3 "$RUNTIME_ROOT/dist/tools/validators/artifact_store_validate.py" \
  "$RUNTIME_ROOT" "implementation-plan=docs/superpowers/plans/example-plan.md" \
  --producer writing-plans \
  --consumer subagent-driven-development \
  > "$TMP/invalid-artifact-store-path.json" 2>&1; then
  printf 'Invalid artifact store path unexpectedly passed preflight\n' >&2
  exit 1
fi

python3 - <<'PY' "$TMP/current-artifact-reference.json"
from pathlib import Path
import json
import sys
Path(sys.argv[1]).write_text(json.dumps({
    'type': 'wiki-context',
    'path': 'artifacts/superpowers/writing-plans/run-1/wiki-context/example-plan.wiki-context.json',
    'status': 'current',
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
if python3 "$RUNTIME_ROOT/dist/tools/validators/artifact_store_validate.py" \
  "$RUNTIME_ROOT" "$TMP/current-artifact-reference.json" \
  --producer writing-plans \
  --consumer subagent-driven-development \
  > "$TMP/invalid-artifact-store-checksum.json" 2>&1; then
  printf 'Current artifact without checksum unexpectedly passed preflight\n' >&2
  exit 1
fi

python3 "$RUNTIME_ROOT/dist/tools/validators/issue_template_invocation_build.py" \
  "$RUNTIME_ROOT" \
  --issue-template-id writing-plan \
  --target-repo /tmp/example-target-repo \
  --user-intent "Write an implementation plan from approved spec" \
  --artifact approved-spec=docs/superpowers/specs/example-spec.md \
  --satisfied-gate spec-approval \
  > "$TMP/generated-template-invocation.json"
python3 - <<'PY' "$TMP/generated-template-invocation.json" "$TMP/generated-template-workflow-invocation.json"
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
invocation = payload.get('workflowInvocation')
if payload.get('status') != 'candidate' or not invocation:
    raise SystemExit(f'Issue template builder did not produce a candidate invocation: {payload}')
if invocation.get('workflowId') != 'writing-plans':
    raise SystemExit(f'Issue template builder routed writing-plan incorrectly: {invocation}')
if invocation.get('gates', {}).get('required') != ['spec-approval']:
    raise SystemExit(f'Issue template builder did not carry required start gate: {invocation}')
Path(sys.argv[2]).write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/generated-template-workflow-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/generated-template-preflight.json"

python3 "$RUNTIME_ROOT/dist/tools/validators/compatibility_command_invocation_build.py" \
  "$RUNTIME_ROOT" \
  --command-id write-plan \
  --target-repo /tmp/example-target-repo \
  --user-intent "writing-plans from approved spec" \
  --artifact approved-spec=docs/superpowers/specs/example-spec.md \
  --satisfied-gate spec-approval \
  > "$TMP/generated-command-invocation.json"
python3 - <<'PY' "$TMP/generated-command-invocation.json" "$TMP/generated-command-workflow-invocation.json"
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
invocation = payload.get('workflowInvocation')
if payload.get('status') != 'candidate' or not invocation:
    raise SystemExit(f'Compatibility command builder did not produce a candidate invocation: {payload}')
if invocation.get('workflowId') != 'writing-plans':
    raise SystemExit(f'Compatibility command builder routed write-plan incorrectly: {invocation}')
Path(sys.argv[2]).write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
python3 "$RUNTIME_ROOT/dist/tools/validators/workflow_invocation_validate.py" \
  "$RUNTIME_ROOT" "$TMP/generated-command-workflow-invocation.json" "${CAP_ARGS[@]}" \
  > "$TMP/generated-command-preflight.json"

python3 "$RUNTIME_ROOT/dist/tools/validators/artifact_next_action_suggest.py" \
  "$RUNTIME_ROOT" "$TMP/artifact-state.json" \
  > "$TMP/artifact-next-actions.json"
python3 - <<'PY' "$TMP/artifact-next-actions.json"
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if payload.get('autoExecute') is not False:
    raise SystemExit('Artifact next action suggestor must never auto-execute')
actions = {item.get('actionId'): item for item in payload.get('suggestions', [])}
for action_id in ('approved-spec-to-writing-plan', 'reviewed-plan-to-sdd-execution'):
    if action_id not in actions:
        raise SystemExit(f'Missing expected artifact next action suggestion: {action_id}\n{payload}')
if actions['reviewed-plan-to-sdd-execution'].get('suggestedWorkflowId') != 'subagent-driven-development':
    raise SystemExit('Reviewed plan next action should suggest SDD execution')
PY

python3 "$RUNTIME_ROOT/dist/tools/validators/intent_router_suggest.py" \
  "$RUNTIME_ROOT" "I want to build a new feature for billing" \
  > "$TMP/intent-router.json"
python3 - <<'PY' "$TMP/intent-router.json"
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if payload.get('autoExecute') is not False or payload.get('suggestOnly') is not True:
    raise SystemExit('Intent router must be suggest-only and non-auto-executing')
intents = {item.get('intentId'): item for item in payload.get('suggestions', [])}
if intents.get('feature-or-behavior-change', {}).get('candidateWorkflowId') != 'brainstorming':
    raise SystemExit(f'Feature intent should suggest brainstorming:\n{payload}')
if 'design-approval' not in intents['feature-or-behavior-change'].get('cannotBypassGates', []):
    raise SystemExit('Feature intent must not bypass design approval gate')
PY

bash "$ROOT/tests/wiki-context-json-render-smoke.sh" "$RUNTIME_ROOT/dist/tools"

printf 'multica-runtime-build smoke OK\n'
