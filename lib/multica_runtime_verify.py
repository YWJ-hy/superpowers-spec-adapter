#!/usr/bin/env python3
"""Verify a generated Multica Superpowers runtime bundle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from adapter_manifest import installed_paths
from multica_runtime_spec import (
    ARTIFACT_STORE_CONTRACT,
    AUTOPILOT_CONTRACTS,
    COMPATIBILITY_COMMANDS,
    EXPECTED_ROLE_AGENTS,
    EXPECTED_WORKFLOWS,
    FORBIDDEN_GENERATED_STRINGS,
    GATE_CONTRACTS,
    GATE_TRANSITION_CONTRACT,
    GATES,
    GENERATED_BY,
    ARTIFACT_CONTRACTS,
    ARTIFACT_NEXT_ACTIONS,
    ILLEGAL_TRANSITION_RULES,
    INTENT_ROUTER_RULES,
    ISSUE_TEMPLATE_BINDINGS,
    ISSUE_TEMPLATES,
    MCP_EXAMPLES,
    MULTICA_TOOLS_ROOT_EXPR,
    OPTIONAL_MCP_SERVERS,
    PREFLIGHT_ARTIFACTS,
    REQUIRED_CAPABILITIES,
    ROLE_AGENT_CONTRACTS,
    ROLE_TASK_CONTRACT,
    SCHEMAS,
    SCRIPT_EXECUTABLES,
    SQUAD_CONTRACTS,
    TASK_GRAPHS,
    TRIGGER_CONTRACTS,
    TRIGGERS,
    AUTOPILOTS,
    VALIDATORS,
    VALIDATOR_SCRIPTS,
    WORKFLOW_MCP_REQUIREMENTS,
)
from native_skill_patch import PATCHES


class VerifyError(SystemExit):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise VerifyError(f'Invalid JSON {path}: {exc}') from exc


def require_file(path: Path) -> None:
    if not path.is_file():
        raise VerifyError(f'Missing file: {path}')


def require_dir(path: Path) -> None:
    if not path.is_dir():
        raise VerifyError(f'Missing directory: {path}')


def require_text(path: Path, needle: str) -> None:
    text = path.read_text(encoding='utf-8')
    if needle not in text:
        raise VerifyError(f'Expected {path} to contain: {needle}')


def require_equal_set(label: str, expected, actual) -> None:
    expected_set = set(expected)
    actual_set = set(actual)
    if expected_set != actual_set:
        raise VerifyError(f'{label} mismatch: missing={sorted(expected_set - actual_set)} extra={sorted(actual_set - expected_set)}')


def require_equal_list(label: str, expected, actual) -> None:
    expected_list = list(expected)
    actual_list = list(actual)
    if expected_list != actual_list:
        raise VerifyError(f'{label} mismatch: expected={expected_list} actual={actual_list}')


def workflow_by_id() -> dict:
    return {workflow.workflow_id: workflow for workflow in EXPECTED_WORKFLOWS}


def expected_squad_contracts() -> list[dict]:
    records = []
    for contract in SQUAD_CONTRACTS:
        record = dict(contract)
        for key in ('memberAgents', 'forbiddenMemberActions'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_autopilot_contracts() -> list[dict]:
    records = []
    for contract in AUTOPILOT_CONTRACTS:
        record = dict(contract)
        for key in ('allowedActions', 'forbiddenActions', 'requiredCapabilities'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_artifact_contracts() -> list[dict]:
    records = []
    for contract in ARTIFACT_CONTRACTS:
        record = dict(contract)
        for key in ('producedBy', 'consumedBy', 'requiredForWorkflows'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_artifact_store_contract() -> dict:
    record = dict(ARTIFACT_STORE_CONTRACT)
    for key in ('statusValues', 'requiresChecksumForStatuses'):
        record[key] = list(record[key])
    return record


def expected_role_agent_contracts() -> list[dict]:
    records = []
    for agent_id in EXPECTED_ROLE_AGENTS:
        record = {'agentId': agent_id, 'freshContext': 'required', **ROLE_AGENT_CONTRACTS[agent_id]}
        for key in ('inputArtifacts', 'outputArtifacts', 'allowedCapabilities', 'toolAccess'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_gate_contracts() -> list[dict]:
    records = []
    for gate_id in GATES:
        record = {'gateId': gate_id, **GATE_CONTRACTS[gate_id]}
        for key in ('requiredArtifacts', 'satisfiedBy'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_gate_transition_contract() -> dict:
    record = dict(GATE_TRANSITION_CONTRACT)
    record['statusValues'] = list(record['statusValues'])
    record['allowedTransitions'] = [dict(item) for item in record['allowedTransitions']]
    record['forbiddenTransitions'] = [dict(item) for item in record['forbiddenTransitions']]
    return record


def expected_role_task_contract() -> dict:
    record = dict(ROLE_TASK_CONTRACT)
    record['requiredFields'] = list(record['requiredFields'])
    record['forbiddenActions'] = list(record['forbiddenActions'])
    return record


def expected_issue_template_bindings() -> list[dict]:
    records = []
    for binding in ISSUE_TEMPLATE_BINDINGS:
        record = dict(binding)
        for key in ('allowedWorkflowIds', 'requiredMetadata', 'requiredArtifacts', 'optionalArtifacts', 'requiredStartGates', 'managedGates'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_compatibility_commands() -> list[dict]:
    records = []
    for command in COMPATIBILITY_COMMANDS:
        record = dict(command)
        for key in ('phrases', 'requiredArtifacts', 'requiredGates'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_intent_router_rules() -> list[dict]:
    records = []
    for rule in INTENT_ROUTER_RULES:
        record = dict(rule)
        for key in ('matches', 'cannotBypassGates'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_artifact_next_actions() -> list[dict]:
    records = []
    for action in ARTIFACT_NEXT_ACTIONS:
        record = dict(action)
        for key in ('fromArtifactTypes', 'requiredSatisfiedGates'):
            record[key] = list(record[key])
        records.append(record)
    return records


def expected_adapter_script_paths(adapter_root: Path) -> set[str]:
    return {f'scripts/{Path(rel).name}' for rel in installed_paths(adapter_root) if rel.startswith('scripts/')}


def manifest_values(manifest: dict, field: str, key: str | None = None) -> list:
    values = []
    for item in manifest.get(field, []):
        if key and isinstance(item, dict):
            values.append(item.get(key))
        else:
            values.append(item)
    return values


def parse_yaml_scalar(value: str):
    if value == '[]':
        return []
    if value == 'true':
        return True
    if value == 'false':
        return False
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_generated_workflow_yaml(path: Path) -> dict:
    metadata = {}
    lines = path.read_text(encoding='utf-8').splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            index += 1
            continue
        if raw.startswith('prompt:'):
            break
        if raw.startswith(' '):
            raise VerifyError(f'Unexpected indented metadata line in {path}: {raw}')
        if ':' not in raw:
            raise VerifyError(f'Invalid workflow metadata line in {path}: {raw}')

        key, _, value = raw.partition(':')
        key = key.strip()
        value = value.strip()
        if value:
            metadata[key] = parse_yaml_scalar(value)
            index += 1
            continue

        values = []
        index += 1
        while index < len(lines):
            child = lines[index]
            child_stripped = child.strip()
            if not child_stripped:
                index += 1
                continue
            if not child.startswith(' '):
                break
            if child_stripped == '[]':
                index += 1
                continue
            if not child_stripped.startswith('- '):
                raise VerifyError(f'Invalid list item in {path}: {child}')
            values.append(parse_yaml_scalar(child_stripped[2:].strip()))
            index += 1
        metadata[key] = values
    return metadata


def text_files(root: Path):
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix in {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico'}:
            continue
        try:
            path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        yield path


def verify_manifest(root: Path) -> dict:
    manifest_path = root / 'manifest.json'
    require_file(manifest_path)
    manifest = load_json(manifest_path)
    if manifest.get('generatedBy') != GENERATED_BY:
        raise VerifyError(f'Unexpected generatedBy in {manifest_path}')
    missing_caps = sorted(set(REQUIRED_CAPABILITIES) - set(manifest.get('requiredCapabilities', [])))
    if missing_caps:
        raise VerifyError(f'Manifest missing required capabilities: {missing_caps}')
    if manifest.get('runtimeRootEnv') != 'MULTICA_SUPERPOWERS_RUNTIME_ROOT':
        raise VerifyError('Manifest missing MULTICA_SUPERPOWERS_RUNTIME_ROOT runtimeRootEnv')
    if manifest.get('rootReplacement', {}).get('to') != MULTICA_TOOLS_ROOT_EXPR:
        raise VerifyError('Manifest rootReplacement does not point to Multica tools root')
    return manifest


def verify_expected_files(root: Path, adapter_root: Path) -> None:
    dist = root / 'dist'
    for workflow in EXPECTED_WORKFLOWS:
        require_file(dist / 'workflows' / workflow.filename)
    for agent_id in EXPECTED_ROLE_AGENTS:
        require_file(dist / 'agents' / f'{agent_id}.md')
    for gate_id in GATES:
        require_file(dist / 'gates' / f'{gate_id}.yaml')
    for trigger_id in TRIGGERS:
        require_file(dist / 'triggers' / f'{trigger_id}.yaml')
    for schema_name in SCHEMAS:
        require_file(dist / 'schemas' / schema_name)
    for mcp_name in MCP_EXAMPLES:
        require_file(dist / 'mcp' / mcp_name)
    for template_name in ISSUE_TEMPLATES:
        require_file(dist / 'multica' / 'issue-templates' / template_name)
    for autopilot_name in AUTOPILOTS:
        require_file(dist / 'multica' / 'autopilots' / autopilot_name)
    for validator_name in VALIDATORS:
        require_file(dist / 'tools' / 'validators' / validator_name)
    require_file(dist / 'multica' / 'agent-instructions.md')
    require_file(dist / 'tools' / 'tool-manifest.json')

    for rel in installed_paths(adapter_root):
        if not rel.startswith('scripts/'):
            continue
        require_file(dist / 'tools' / 'scripts' / Path(rel).name)


def verify_generated_text(root: Path) -> None:
    dist = root / 'dist'
    for path in text_files(dist):
        text = path.read_text(encoding='utf-8')
        for forbidden in FORBIDDEN_GENERATED_STRINGS:
            if forbidden in text:
                raise VerifyError(f'Forbidden generated string in {path}: {forbidden}')

    rendered_root_seen = False
    for path in (dist / 'workflows').glob('*.workflow.yaml'):
        text = path.read_text(encoding='utf-8')
        if MULTICA_TOOLS_ROOT_EXPR in text:
            rendered_root_seen = True
            break
    if not rendered_root_seen:
        raise VerifyError(f'No workflow references {MULTICA_TOOLS_ROOT_EXPR}')


def verify_workflow_content(root: Path) -> None:
    dist = root / 'dist'
    for spec in PATCHES:
        workflow_path = dist / 'workflows' / f'{spec.skill}.workflow.yaml'
        if not workflow_path.is_file():
            continue
        require_text(workflow_path, spec.start_marker)
        require_text(workflow_path, 'Generated by superpower-adapter')

    for workflow_id in ('init-wiki', 'import-wiki', 'migrate-wiki', 'lanhu-requirements', 'shared-wiki-mcp', 'publish-shared-wiki'):
        path = dist / 'workflows' / f'{workflow_id}.workflow.yaml'
        require_text(path, 'standalone')
        require_text(path, 'not user entrypoints')

    require_text(dist / 'workflows' / 'writing-plans.workflow.yaml', 'schemaVersion: 3')
    require_text(dist / 'workflows' / 'writing-plans.workflow.yaml', 'Referenced Project Wiki')
    require_text(dist / 'workflows' / 'executing-plans.workflow.yaml', 'wiki_context_render.py')
    require_text(dist / 'workflows' / 'subagent-driven-development.workflow.yaml', 'wiki_context_render.py')
    require_text(dist / 'workflows' / 'systematic-debugging.workflow.yaml', 'Do not call `wiki-researcher` at the start of debugging')


def verify_preflight_artifacts(root: Path, manifest: dict) -> None:
    preflight_dir = root / 'dist' / 'preflight'
    for name in PREFLIGHT_ARTIFACTS:
        require_file(preflight_dir / name)

    manifest_paths = {item.get('path') for item in manifest.get('preflightArtifacts', [])}
    expected_paths = {f'dist/preflight/{name}' for name in PREFLIGHT_ARTIFACTS}
    if manifest_paths != expected_paths:
        raise VerifyError(f'runtime manifest preflightArtifacts mismatch: missing={sorted(expected_paths - manifest_paths)} extra={sorted(manifest_paths - expected_paths)}')

    runtime_capabilities = load_json(preflight_dir / 'runtime-capabilities.json')
    missing_caps = sorted(set(REQUIRED_CAPABILITIES) - set(runtime_capabilities.get('requiredCapabilities', [])))
    if missing_caps:
        raise VerifyError(f'runtime capability preflight contract missing capabilities: {missing_caps}')
    if runtime_capabilities.get('runtimeRootEnv') != 'MULTICA_SUPERPOWERS_RUNTIME_ROOT':
        raise VerifyError('runtime capability preflight contract missing runtime root env')

    artifact_store = load_json(preflight_dir / 'artifact-store-contract.json')
    expected_store = expected_artifact_store_contract()
    for key, expected in expected_store.items():
        if artifact_store.get(key) != expected:
            raise VerifyError(f'artifact-store preflight contract {key} mismatch: expected={expected} actual={artifact_store.get(key)}')

    gate_transition = load_json(preflight_dir / 'gate-transition-contract.json')
    expected_transition = expected_gate_transition_contract()
    for key, expected in expected_transition.items():
        if gate_transition.get(key) != expected:
            raise VerifyError(f'gate-transition preflight contract {key} mismatch: expected={expected} actual={gate_transition.get(key)}')

    role_task = load_json(preflight_dir / 'role-task-contract.json')
    expected_role_task = expected_role_task_contract()
    for key, expected in expected_role_task.items():
        if role_task.get(key) != expected:
            raise VerifyError(f'role-task preflight contract {key} mismatch: expected={expected} actual={role_task.get(key)}')

    invocation_contract = load_json(preflight_dir / 'workflow-invocation-contract.json')
    if invocation_contract.get('artifactStoreContract') != expected_store:
        raise VerifyError('workflow invocation contract artifactStoreContract mismatch')
    if invocation_contract.get('gateTransitionContract') != expected_transition:
        raise VerifyError('workflow invocation contract gateTransitionContract mismatch')
    if invocation_contract.get('roleTaskContract') != expected_role_task:
        raise VerifyError('workflow invocation contract roleTaskContract mismatch')
    missing_contract_caps = sorted(set(REQUIRED_CAPABILITIES) - set(invocation_contract.get('requiredCapabilities', [])))
    if missing_contract_caps:
        raise VerifyError(f'workflow invocation contract missing capabilities: {missing_contract_caps}')
    workflows = invocation_contract.get('workflows', {})
    missing_workflows = sorted({workflow.workflow_id for workflow in EXPECTED_WORKFLOWS} - set(workflows))
    if missing_workflows:
        raise VerifyError(f'workflow invocation contract missing workflows: {missing_workflows}')
    rule_ids = {rule.get('id') for rule in invocation_contract.get('illegalTransitionRules', [])}
    missing_rules = sorted({rule['id'] for rule in ILLEGAL_TRANSITION_RULES} - rule_ids)
    if missing_rules:
        raise VerifyError(f'workflow invocation contract missing illegal transition rules: {missing_rules}')


def verify_validator_scripts(root: Path, manifest: dict) -> None:
    validators_dir = root / 'dist' / 'tools' / 'validators'
    for name in VALIDATOR_SCRIPTS:
        path = validators_dir / name
        require_file(path)
        if not os.access(path, os.R_OK):
            raise VerifyError(f'Validator script is not readable: {path}')
        if not os.access(path, os.X_OK):
            raise VerifyError(f'Validator script is not executable: {path}')

    expected_paths = {f'validators/{name}' for name in VALIDATOR_SCRIPTS}
    tool_manifest = load_json(root / 'dist' / 'tools' / 'tool-manifest.json')
    tool_paths = {item.get('path') for item in tool_manifest.get('validatorScripts', [])}
    manifest_paths = {item.get('path') for item in manifest.get('validatorScripts', [])}
    if tool_paths != expected_paths:
        raise VerifyError(f'tool-manifest validatorScripts mismatch: missing={sorted(expected_paths - tool_paths)} extra={sorted(tool_paths - expected_paths)}')
    if manifest_paths != expected_paths:
        raise VerifyError(f'runtime manifest validatorScripts mismatch: missing={sorted(expected_paths - manifest_paths)} extra={sorted(manifest_paths - expected_paths)}')

    for item in tool_manifest.get('validatorScripts', []):
        rel = item.get('path')
        expected_runtime_path = f'{MULTICA_TOOLS_ROOT_EXPR}/{rel}'
        if item.get('runtimePath') != expected_runtime_path:
            raise VerifyError(f'Invalid validator runtimePath for {rel}: {item.get("runtimePath")}')
        if item.get('entrypointType') != 'preflight-validator':
            raise VerifyError(f'Invalid validator entrypointType for {rel}')


def verify_sdd_task_graph(root: Path, manifest: dict) -> None:
    task_graph_dir = root / 'dist' / 'task-graphs'
    for name in TASK_GRAPHS:
        require_file(task_graph_dir / name)

    manifest_paths = {item.get('path') for item in manifest.get('taskGraphs', [])}
    expected_paths = {f'dist/task-graphs/{name}' for name in TASK_GRAPHS}
    if manifest_paths != expected_paths:
        raise VerifyError(f'runtime manifest taskGraphs mismatch: missing={sorted(expected_paths - manifest_paths)} extra={sorted(manifest_paths - expected_paths)}')

    graph = load_json(task_graph_dir / 'subagent-driven-development.task-graph.json')
    if graph.get('workflowId') != 'subagent-driven-development':
        raise VerifyError('SDD task graph workflowId mismatch')
    if graph.get('executionMode') != 'multica-sdd-task-graph':
        raise VerifyError('SDD task graph executionMode mismatch')
    missing_inputs = sorted({'implementation-plan', 'wiki-context'} - set(graph.get('requiredInputArtifacts', [])))
    if missing_inputs:
        raise VerifyError(f'SDD task graph missing required inputs: {missing_inputs}')

    nodes = graph.get('nodes', [])
    node_by_id = {node.get('nodeId'): node for node in nodes}
    for node_id in ('implementer', 'spec-compliance-reviewer', 'code-quality-reviewer', 'code-reviewer-final'):
        if node_id not in node_by_id:
            raise VerifyError(f'SDD task graph missing node: {node_id}')
    for node in nodes:
        if node.get('freshContext') != 'required':
            raise VerifyError(f'SDD task graph node does not require fresh context: {node.get("nodeId")}')
    final_node = node_by_id.get('code-reviewer-final', {})
    if final_node.get('roleAgent') != 'code-reviewer':
        raise VerifyError('SDD final review node must use code-reviewer role agent')

    graph_text = json.dumps(graph, ensure_ascii=False)
    if 'wiki_context_render.py' not in graph_text:
        raise VerifyError('SDD task graph must reference wiki_context_render.py')
    edges = {(edge.get('from'), edge.get('to'), edge.get('condition')) for edge in graph.get('edges', [])}
    if ('spec-compliance-reviewer', 'implementer', 'review-failed') not in edges:
        raise VerifyError('SDD task graph missing spec review failure loop')
    if ('code-quality-reviewer', 'implementer', 'review-failed') not in edges:
        raise VerifyError('SDD task graph missing code quality failure loop')


def verify_schemas(root: Path) -> None:
    schemas_dir = root / 'dist' / 'schemas'
    invocation = load_json(schemas_dir / 'workflow-invocation.schema.json')
    required = set(invocation.get('required', []))
    expected = {'workflowId', 'triggerSource', 'targetRepo', 'sourceArtifacts', 'gates', 'requiredCapabilities', 'mcpRequirements', 'executionMode'}
    missing = sorted(expected - required)
    if missing:
        raise VerifyError(f'workflow-invocation schema missing required fields: {missing}')

    properties = invocation.get('properties', {})
    workflow_enum = set(properties.get('workflowId', {}).get('enum', []))
    missing_workflows = sorted({workflow.workflow_id for workflow in EXPECTED_WORKFLOWS} - workflow_enum)
    if missing_workflows:
        raise VerifyError(f'workflow-invocation schema missing workflow ids: {missing_workflows}')
    capability_enum = set(properties.get('requiredCapabilities', {}).get('items', {}).get('enum', []))
    missing_caps = sorted(set(REQUIRED_CAPABILITIES) - capability_enum)
    if missing_caps:
        raise VerifyError(f'workflow-invocation schema missing capability enum values: {missing_caps}')
    if properties.get('sourceArtifacts', {}).get('items', {}).get('$ref') != '#/$defs/sourceArtifact':
        raise VerifyError('workflow-invocation sourceArtifacts must reference sourceArtifact contract')
    if properties.get('gates', {}).get('$ref') != '#/$defs/gateSet':
        raise VerifyError('workflow-invocation gates must reference gateSet contract')
    if properties.get('mcpRequirements', {}).get('items', {}).get('$ref') != '#/$defs/mcpRequirement':
        raise VerifyError('workflow-invocation mcpRequirements must reference mcpRequirement contract')
    if 'artifactPreflight' not in properties or 'preflight' not in properties:
        raise VerifyError('workflow-invocation schema missing preflight metadata contracts')

    defs = invocation.get('$defs', {})
    gate_enum = set(defs.get('gateSet', {}).get('properties', {}).get('required', {}).get('items', {}).get('enum', []))
    missing_gates = sorted(set(GATES) - gate_enum)
    if missing_gates:
        raise VerifyError(f'workflow-invocation schema missing gate enum values: {missing_gates}')
    preflight_props = defs.get('preflight', {}).get('properties', {})
    for field in ('artifactChecks', 'capabilityChecks', 'gateChecks', 'mcpChecks', 'illegalTransitionChecks'):
        if field not in preflight_props:
            raise VerifyError(f'workflow-invocation preflight contract missing {field}')

    wiki_context = load_json(schemas_dir / 'wiki-context-v3.schema.json')
    schema_version = wiki_context.get('properties', {}).get('schemaVersion', {})
    if schema_version.get('const') != 3:
        raise VerifyError('wiki-context-v3 schema must require schemaVersion const 3')

    schema_expectations = {
        'spec.schema.json': {'schemaVersion', 'title', 'userIntent', 'status', 'decisions', 'openQuestions'},
        'implementation-plan.schema.json': {'schemaVersion', 'specRef', 'status', 'tasks', 'referencedProjectWiki'},
        'lanhu-evidence-package.schema.json': {'schemaVersion', 'role', 'indexPath', 'confirmationGate', 'sourceFactCoverage'},
        'update-wiki-candidate.schema.json': {'schemaVersion', 'completedWorkSummary', 'candidates', 'decision'},
        'review-result.schema.json': {'schemaVersion', 'reviewerRole', 'status', 'findings'},
    }
    for schema_name, required_fields in schema_expectations.items():
        schema = load_json(schemas_dir / schema_name)
        missing_fields = sorted(required_fields - set(schema.get('required', [])))
        if missing_fields:
            raise VerifyError(f'{schema_name} missing required fields: {missing_fields}')
        if schema.get('properties', {}).get('schemaVersion', {}).get('const') != 1:
            raise VerifyError(f'{schema_name} must require schemaVersion const 1')

    gate_state = load_json(schemas_dir / 'gate-state.schema.json')
    required_gate_state_fields = {'schemaVersion', 'gateId', 'status', 'ownerRoleAgent', 'evidence'}
    missing_gate_state_fields = sorted(required_gate_state_fields - set(gate_state.get('required', [])))
    if missing_gate_state_fields:
        raise VerifyError(f'gate-state schema missing required fields: {missing_gate_state_fields}')
    gate_id_enum = set(gate_state.get('properties', {}).get('gateId', {}).get('enum', []))
    missing_gate_ids = sorted(set(GATES) - gate_id_enum)
    if missing_gate_ids:
        raise VerifyError(f'gate-state schema missing gate ids: {missing_gate_ids}')
    status_enum = gate_state.get('properties', {}).get('status', {}).get('enum', [])
    if status_enum != ['pending', 'satisfied', 'blocked']:
        raise VerifyError('gate-state schema status enum mismatch')

    sdd_graph = load_json(schemas_dir / 'sdd-task-graph.schema.json')
    required_graph_fields = {'schemaVersion', 'graphId', 'workflowId', 'executionMode', 'requiredInputArtifacts', 'nodes', 'edges'}
    missing_graph_fields = sorted(required_graph_fields - set(sdd_graph.get('required', [])))
    if missing_graph_fields:
        raise VerifyError(f'sdd-task-graph schema missing required fields: {missing_graph_fields}')
    if sdd_graph.get('properties', {}).get('workflowId', {}).get('const') != 'subagent-driven-development':
        raise VerifyError('sdd-task-graph schema must bind workflowId')

    for name in ('sdd-task-input.schema.json', 'sdd-task-output.schema.json'):
        schema = load_json(schemas_dir / name)
        if schema.get('properties', {}).get('schemaVersion', {}).get('const') != 1:
            raise VerifyError(f'{name} must require schemaVersion const 1')
        if not schema.get('required'):
            raise VerifyError(f'{name} must declare required fields')


def verify_tool_scripts(root: Path, adapter_root: Path, manifest: dict) -> None:
    scripts_dir = root / 'dist' / 'tools' / 'scripts'
    for name in SCRIPT_EXECUTABLES:
        path = scripts_dir / name
        require_file(path)
        if not os.access(path, os.R_OK):
            raise VerifyError(f'Script is not readable: {path}')
        if not os.access(path, os.X_OK):
            raise VerifyError(f'Script is not executable: {path}')

    expected_paths = {f'scripts/{Path(rel).name}' for rel in installed_paths(adapter_root) if rel.startswith('scripts/')}
    tool_manifest = load_json(root / 'dist' / 'tools' / 'tool-manifest.json')
    if tool_manifest.get('boundary') is None or 'not user entrypoints' not in tool_manifest['boundary']:
        raise VerifyError('tool-manifest must state scripts are not user entrypoints')

    records = tool_manifest.get('scripts', [])
    actual_paths = {item.get('path') for item in records}
    if actual_paths != expected_paths:
        raise VerifyError(f'tool-manifest script set mismatch: missing={sorted(expected_paths - actual_paths)} extra={sorted(actual_paths - expected_paths)}')
    for item in records:
        rel = item.get('path')
        if not isinstance(rel, str) or not rel.startswith('scripts/'):
            raise VerifyError(f'Invalid tool-manifest script path: {rel}')
        require_file(root / 'dist' / 'tools' / rel)
        expected_runtime_path = f'{MULTICA_TOOLS_ROOT_EXPR}/{rel}'
        if item.get('runtimePath') != expected_runtime_path:
            raise VerifyError(f'Invalid runtimePath for {rel}: {item.get("runtimePath")}')
        if item.get('entrypointType') != 'tool-runner-internal':
            raise VerifyError(f'Invalid entrypointType for {rel}')

    manifest_tool_paths = {item.get('path') for item in manifest.get('toolScripts', [])}
    if manifest_tool_paths != expected_paths:
        raise VerifyError(f'runtime manifest toolScripts mismatch: missing={sorted(expected_paths - manifest_tool_paths)} extra={sorted(manifest_tool_paths - expected_paths)}')
    if 'scripts/wiki_context_render.py' not in actual_paths:
        raise VerifyError('tool-manifest missing wiki_context_render.py')
    if 'scripts/wiki_settings.py' not in actual_paths:
        raise VerifyError('tool-manifest missing wiki_settings.py')


def verify_source_snapshots(root: Path) -> None:
    source = root / 'source'
    adapter_source = source / 'superpower-adapter'
    superpowers_source = source / 'superpowers'
    require_file(adapter_source / 'manifest.json')
    require_dir(adapter_source / 'overlays' / 'agents')
    require_dir(adapter_source / 'overlays' / 'skills')
    require_dir(adapter_source / 'overlays' / 'scripts')
    require_file(adapter_source / 'overlays' / 'scripts' / 'wiki_context_render.py')
    require_file(adapter_source / 'overlays' / 'scripts' / 'wiki_settings.py')
    require_dir(superpowers_source / 'skills')
    require_file(superpowers_source / 'skills' / 'writing-plans' / 'SKILL.md')


def verify_squad_contracts(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    expected_contracts = expected_squad_contracts()
    catalog = load_json(dist / 'multica' / 'squads' / 'squad-contracts.json')
    if catalog.get('generatedBy') != GENERATED_BY:
        raise VerifyError('squad-contracts catalog has invalid generatedBy')
    require_equal_list('squad-contracts catalog', expected_contracts, catalog.get('contracts', []))
    require_equal_list('runtime manifest squadContracts', expected_contracts, manifest.get('squadContracts', []))
    role_agents = set(EXPECTED_ROLE_AGENTS)
    for contract in expected_contracts:
        squad_id = contract['squadId']
        if contract.get('leaderAgent') != 'superpowers-orchestrator':
            raise VerifyError(f'Squad {squad_id} leader must be superpowers-orchestrator')
        if contract.get('gateOwner') != 'superpowers-orchestrator':
            raise VerifyError(f'Squad {squad_id} gate owner must be superpowers-orchestrator')
        if contract.get('freshContextRequired') is not True:
            raise VerifyError(f'Squad {squad_id} must require fresh context')
        require_equal_set(f'squad {squad_id} members', role_agents, contract.get('memberAgents', []))
        for action in ('advance-gates-directly', 'skip-orchestrator-preflight'):
            if action not in contract.get('forbiddenMemberActions', []):
                raise VerifyError(f'Squad {squad_id} missing forbidden member action: {action}')


def verify_autopilot_contracts(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    expected_contracts = expected_autopilot_contracts()
    catalog = load_json(dist / 'multica' / 'autopilots' / 'autopilot-contracts.json')
    if catalog.get('generatedBy') != GENERATED_BY:
        raise VerifyError('autopilot-contracts catalog has invalid generatedBy')
    require_equal_list('autopilot-contracts catalog', expected_contracts, catalog.get('contracts', []))
    require_equal_list('runtime manifest autopilotContracts', expected_contracts, manifest.get('autopilotContracts', []))
    template_files = {contract['templateFile'] for contract in expected_contracts}
    require_equal_set('autopilot contract template files', AUTOPILOTS, template_files)
    forbidden_required = {'brainstorming', 'writing-plans', 'implementation', 'update-wiki-write', 'shared-wiki-publish', 'pull-request-create'}
    for contract in expected_contracts:
        autopilot_id = contract['autopilotId']
        if contract.get('autoExecute') is not False:
            raise VerifyError(f'Autopilot contract {autopilot_id} must not auto-execute')
        missing_forbidden = sorted(forbidden_required - set(contract.get('forbiddenActions', [])))
        if missing_forbidden:
            raise VerifyError(f'Autopilot contract {autopilot_id} missing forbidden actions: {missing_forbidden}')
        unknown_caps = sorted(set(contract.get('requiredCapabilities', [])) - set(REQUIRED_CAPABILITIES))
        if unknown_caps:
            raise VerifyError(f'Autopilot contract {autopilot_id} references unknown capabilities: {unknown_caps}')
        require_text(dist / 'multica' / 'autopilots' / contract['templateFile'], 'check-class')


def verify_artifact_contracts(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    expected_contracts = expected_artifact_contracts()
    catalog = load_json(dist / 'schemas' / 'artifact-contracts.json')
    if catalog.get('generatedBy') != GENERATED_BY:
        raise VerifyError('artifact-contracts catalog has invalid generatedBy')
    require_equal_list('artifact-contracts catalog', expected_contracts, catalog.get('contracts', []))
    require_equal_list('runtime manifest artifactContracts', expected_contracts, manifest.get('artifactContracts', []))

    expected_store = expected_artifact_store_contract()
    store_contract = load_json(dist / 'preflight' / 'artifact-store-contract.json')
    if store_contract.get('generatedBy') != GENERATED_BY:
        raise VerifyError('artifact-store-contract has invalid generatedBy')
    for key, expected in expected_store.items():
        if store_contract.get(key) != expected:
            raise VerifyError(f'artifact-store-contract {key} mismatch: expected={expected} actual={store_contract.get(key)}')
    if store_contract.get('artifactContracts') != expected_contracts:
        raise VerifyError('artifact-store-contract artifactContracts mismatch')
    if manifest.get('artifactStoreContract') != expected_store:
        raise VerifyError('runtime manifest artifactStoreContract mismatch')
    for placeholder in ('{workflowId}', '{runId}', '{artifactType}', '{name}'):
        if placeholder not in expected_store.get('pathPattern', ''):
            raise VerifyError(f'artifact store pathPattern missing placeholder: {placeholder}')
    if expected_store.get('checksumAlgorithm') != 'sha256':
        raise VerifyError('artifact store checksum algorithm must be sha256')
    if 'approved' not in expected_store.get('requiresChecksumForStatuses', []) or 'current' not in expected_store.get('requiresChecksumForStatuses', []):
        raise VerifyError('artifact store must require checksums for approved/current artifacts')

    workflow_ids = {workflow.workflow_id for workflow in EXPECTED_WORKFLOWS}
    role_agent_ids = set(EXPECTED_ROLE_AGENTS)
    schema_names = set(SCHEMAS)
    artifact_types = set()
    for contract in expected_contracts:
        artifact_type = contract['artifactType']
        if artifact_type in artifact_types:
            raise VerifyError(f'Duplicate artifact contract type: {artifact_type}')
        artifact_types.add(artifact_type)
        schema_file = contract.get('schemaFile')
        if schema_file and schema_file not in schema_names:
            raise VerifyError(f'Artifact contract {artifact_type} references unknown schema: {schema_file}')
        for producer in contract.get('producedBy', []):
            if producer not in workflow_ids and producer not in role_agent_ids and producer != 'issue-template':
                raise VerifyError(f'Artifact contract {artifact_type} has unknown producer: {producer}')
        for consumer in contract.get('consumedBy', []):
            if consumer not in workflow_ids and consumer not in role_agent_ids:
                raise VerifyError(f'Artifact contract {artifact_type} has unknown consumer: {consumer}')
        for workflow_id in contract.get('requiredForWorkflows', []):
            if workflow_id not in workflow_ids:
                raise VerifyError(f'Artifact contract {artifact_type} requiredForWorkflows references unknown workflow: {workflow_id}')

    workflow_required_artifacts = {artifact for workflow in EXPECTED_WORKFLOWS for artifact in workflow.required_artifacts}
    missing_contracts = sorted(workflow_required_artifacts - artifact_types)
    if missing_contracts:
        raise VerifyError(f'Workflow required artifacts missing contracts: {missing_contracts}')


def verify_role_agent_contracts(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    agents_dir = dist / 'agents'
    expected_contracts = expected_role_agent_contracts()
    catalog = load_json(agents_dir / 'role-agent-contracts.json')
    if catalog.get('generatedBy') != GENERATED_BY or catalog.get('freshContext') != 'required':
        raise VerifyError('role-agent-contracts catalog has invalid metadata')
    require_equal_list('role-agent-contracts catalog', expected_contracts, catalog.get('contracts', []))
    require_equal_list('runtime manifest roleAgentContracts', expected_contracts, manifest.get('roleAgentContracts', []))

    seen = set()
    for contract in expected_contracts:
        agent_id = contract['agentId']
        if agent_id in seen:
            raise VerifyError(f'Duplicate role agent contract id: {agent_id}')
        seen.add(agent_id)
        if agent_id not in EXPECTED_ROLE_AGENTS:
            raise VerifyError(f'Role agent contract references unknown agent: {agent_id}')
        if contract.get('freshContext') != 'required':
            raise VerifyError(f'Role agent contract must require fresh context: {agent_id}')
        unknown_caps = sorted(set(contract.get('allowedCapabilities', [])) - set(REQUIRED_CAPABILITIES))
        if unknown_caps:
            raise VerifyError(f'Role agent contract {agent_id} references unknown capabilities: {unknown_caps}')
        if not contract.get('toolAccess'):
            raise VerifyError(f'Role agent contract {agent_id} must declare toolAccess')
        if contract.get('mayAdvanceGates') is True and agent_id != 'superpowers-orchestrator':
            raise VerifyError(f'Only superpowers-orchestrator may advance gates: {agent_id}')
        if contract.get('mayPerformExternalSideEffects') is True and agent_id != 'shared-wiki-publisher':
            raise VerifyError(f'Only shared-wiki-publisher may perform external side effects: {agent_id}')
        require_file(agents_dir / f'{agent_id}.md')

    require_equal_set('role-agent contract ids', EXPECTED_ROLE_AGENTS, [contract['agentId'] for contract in expected_contracts])

    expected_task = expected_role_task_contract()
    task_contract = load_json(dist / 'preflight' / 'role-task-contract.json')
    if task_contract.get('generatedBy') != GENERATED_BY:
        raise VerifyError('role-task-contract has invalid generatedBy')
    for key, expected in expected_task.items():
        if task_contract.get(key) != expected:
            raise VerifyError(f'role-task-contract {key} mismatch: expected={expected} actual={task_contract.get(key)}')
    if task_contract.get('roleAgentContracts') != expected_contracts:
        raise VerifyError('role-task-contract roleAgentContracts mismatch')
    if task_contract.get('artifactContracts') != expected_artifact_contracts():
        raise VerifyError('role-task-contract artifactContracts mismatch')
    if manifest.get('roleTaskContract') != expected_task:
        raise VerifyError('runtime manifest roleTaskContract mismatch')
    if task_contract.get('freshContext') != 'required':
        raise VerifyError('role task contract must require fresh context')
    if task_contract.get('createdBy') != 'superpowers-orchestrator':
        raise VerifyError('role task contract must be orchestrator-created')


def verify_gate_contracts(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    gates_dir = dist / 'gates'
    expected_contracts = expected_gate_contracts()
    catalog = load_json(gates_dir / 'gate-contracts.json')
    if catalog.get('generatedBy') != GENERATED_BY:
        raise VerifyError('gate-contracts catalog has invalid generatedBy')
    if catalog.get('statusValues') != ['pending', 'satisfied', 'blocked']:
        raise VerifyError('gate-contracts catalog statusValues mismatch')
    require_equal_list('gate-contracts catalog', expected_contracts, catalog.get('contracts', []))
    require_equal_list('runtime manifest gateContracts', expected_contracts, manifest.get('gateContracts', []))

    seen = set()
    role_agent_ids = set(EXPECTED_ROLE_AGENTS)
    for contract in expected_contracts:
        gate_id = contract['gateId']
        if gate_id in seen:
            raise VerifyError(f'Duplicate gate contract id: {gate_id}')
        seen.add(gate_id)
        if gate_id not in GATES:
            raise VerifyError(f'Gate contract references unknown gate: {gate_id}')
        if contract.get('ownerRoleAgent') not in role_agent_ids:
            raise VerifyError(f'Gate contract {gate_id} references unknown owner role agent: {contract.get("ownerRoleAgent")}')
        if not contract.get('gateType'):
            raise VerifyError(f'Gate contract {gate_id} missing gateType')
        if contract.get('userAuthorizationRequired') is not True:
            raise VerifyError(f'Gate contract {gate_id} must declare userAuthorizationRequired=true')
        path = gates_dir / f'{gate_id}.yaml'
        require_text(path, f'gateId: "{gate_id}"')
        require_text(path, f'gateType: "{contract["gateType"]}"')
        require_text(path, f'owner: "{contract["ownerRoleAgent"]}"')
        require_text(path, 'requiredArtifacts:')
        require_text(path, 'satisfiedBy:')
        require_text(path, f'userAuthorizationRequired: {str(contract["userAuthorizationRequired"]).lower()}')
        require_text(path, f'externalSideEffect: {str(contract["blocksExternalSideEffects"]).lower()}')

    side_effect_gates = {contract['gateId'] for contract in expected_contracts if contract.get('blocksExternalSideEffects')}
    expected_side_effect_gates = {'shared-wiki-publish-authorization', 'external-pr-creation-authorization'}
    if side_effect_gates != expected_side_effect_gates:
        raise VerifyError(f'External side-effect gate set mismatch: {side_effect_gates}')

    expected_transition = expected_gate_transition_contract()
    transition_contract = load_json(dist / 'preflight' / 'gate-transition-contract.json')
    if transition_contract.get('generatedBy') != GENERATED_BY:
        raise VerifyError('gate-transition-contract has invalid generatedBy')
    for key, expected in expected_transition.items():
        if transition_contract.get(key) != expected:
            raise VerifyError(f'gate-transition-contract {key} mismatch: expected={expected} actual={transition_contract.get(key)}')
    if transition_contract.get('gateContracts') != expected_contracts:
        raise VerifyError('gate-transition-contract gateContracts mismatch')
    if manifest.get('gateTransitionContract') != expected_transition:
        raise VerifyError('runtime manifest gateTransitionContract mismatch')
    if transition_contract.get('advancePolicy') != 'gate-owner-or-orchestrator-only':
        raise VerifyError('gate transition advancePolicy mismatch')
    transitions = {(item.get('from'), item.get('to')) for item in transition_contract.get('allowedTransitions', [])}
    for transition in (('pending', 'satisfied'), ('pending', 'blocked'), ('blocked', 'pending'), ('blocked', 'satisfied')):
        if transition not in transitions:
            raise VerifyError(f'gate transition missing allowed edge: {transition}')


def verify_trigger_contracts(root: Path) -> None:
    triggers_dir = root / 'dist' / 'triggers'
    for trigger_id in TRIGGERS:
        path = triggers_dir / f'{trigger_id}.yaml'
        require_text(path, 'normalizesTo: WorkflowInvocation')
        require_text(path, 'requiredInputs:')
        require_text(path, 'preflightChecks:')
        require_text(path, 'schema: workflow-invocation.schema.json')
        contract = TRIGGER_CONTRACTS[trigger_id]
        for field in contract['requiredInputs']:
            require_text(path, field)
        for check in contract['preflightChecks']:
            require_text(path, check)

    require_text(triggers_dir / 'issue-template-bindings.yaml', 'bindingCatalog: issue-template-bindings.json')
    require_text(triggers_dir / 'artifact-next-actions.yaml', 'actionCatalog: artifact-next-actions.json')
    require_text(triggers_dir / 'artifact-next-actions.yaml', 'autoExecute: false')

    illegal_path = triggers_dir / 'illegal-transition-rules.yaml'
    require_text(illegal_path, 'rules:')
    for rule in ILLEGAL_TRANSITION_RULES:
        require_text(illegal_path, rule['id'])
        require_text(illegal_path, rule['description'])


def verify_trigger_catalogs(root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    workflows = workflow_by_id()
    triggers_dir = dist / 'triggers'
    compatibility_catalog = load_json(triggers_dir / 'compatibility-commands.json')
    issue_catalog = load_json(triggers_dir / 'issue-template-bindings.json')
    intent_catalog = load_json(triggers_dir / 'intent-router-rules.json')
    next_action_catalog = load_json(triggers_dir / 'artifact-next-actions.json')
    expected_commands = expected_compatibility_commands()
    expected_bindings = expected_issue_template_bindings()
    expected_intents = expected_intent_router_rules()
    expected_actions = expected_artifact_next_actions()

    if compatibility_catalog.get('generatedBy') != GENERATED_BY or compatibility_catalog.get('normalizesTo') != 'WorkflowInvocation':
        raise VerifyError('compatibility-commands catalog has invalid metadata')
    if issue_catalog.get('generatedBy') != GENERATED_BY or issue_catalog.get('normalizesTo') != 'WorkflowInvocation':
        raise VerifyError('issue-template-bindings catalog has invalid metadata')
    if intent_catalog.get('generatedBy') != GENERATED_BY or intent_catalog.get('normalizesTo') != 'WorkflowInvocation':
        raise VerifyError('intent-router-rules catalog has invalid metadata')
    if intent_catalog.get('suggestOnly') is not True or intent_catalog.get('gateAware') is not True:
        raise VerifyError('intent-router-rules catalog must be gate-aware and suggest-only')
    if next_action_catalog.get('generatedBy') != GENERATED_BY or next_action_catalog.get('normalizesTo') != 'WorkflowInvocation':
        raise VerifyError('artifact-next-actions catalog has invalid metadata')
    if next_action_catalog.get('autoExecute') is not False or next_action_catalog.get('gateAware') is not True:
        raise VerifyError('artifact-next-actions catalog must be gate-aware and non-auto-executing')

    require_equal_list('compatibility-commands catalog', expected_commands, compatibility_catalog.get('commands', []))
    require_equal_list('issue-template-bindings catalog', expected_bindings, issue_catalog.get('bindings', []))
    require_equal_list('intent-router-rules catalog', expected_intents, intent_catalog.get('rules', []))
    require_equal_list('artifact-next-actions catalog', expected_actions, next_action_catalog.get('actions', []))
    require_equal_list('runtime manifest compatibilityCommands', expected_commands, manifest.get('compatibilityCommands', []))
    require_equal_list('runtime manifest issueTemplateBindings', expected_bindings, manifest.get('issueTemplateBindings', []))
    require_equal_list('runtime manifest intentRouterRules', expected_intents, manifest.get('intentRouterRules', []))
    require_equal_list('runtime manifest artifactNextActions', expected_actions, manifest.get('artifactNextActions', []))

    seen_command_ids = set()
    for command in expected_commands:
        command_id = command['commandId']
        if command_id in seen_command_ids:
            raise VerifyError(f'Duplicate compatibility command id: {command_id}')
        seen_command_ids.add(command_id)
        if command['workflowId'] not in workflows:
            raise VerifyError(f'Compatibility command {command_id} references unknown workflow: {command["workflowId"]}')
        if not command['phrases']:
            raise VerifyError(f'Compatibility command {command_id} must declare phrases')
        for gate_id in command['requiredGates']:
            if gate_id not in GATES:
                raise VerifyError(f'Compatibility command {command_id} references unknown gate: {gate_id}')

    seen_intent_ids = set()
    for rule in expected_intents:
        intent_id = rule['intentId']
        if intent_id in seen_intent_ids:
            raise VerifyError(f'Duplicate intent router rule id: {intent_id}')
        seen_intent_ids.add(intent_id)
        if rule['candidateWorkflowId'] not in workflows:
            raise VerifyError(f'Intent router rule {intent_id} references unknown workflow: {rule["candidateWorkflowId"]}')
        if not rule['matches']:
            raise VerifyError(f'Intent router rule {intent_id} must declare match terms')
        for gate_id in rule['cannotBypassGates']:
            if gate_id not in GATES:
                raise VerifyError(f'Intent router rule {intent_id} references unknown gate: {gate_id}')

    template_files = {binding['templateFile'] for binding in expected_bindings}
    require_equal_set('issue-template binding files', ISSUE_TEMPLATES, template_files)
    seen_template_ids = set()
    for binding in expected_bindings:
        template_id = binding['templateId']
        if template_id in seen_template_ids:
            raise VerifyError(f'Duplicate issue template binding id: {template_id}')
        seen_template_ids.add(template_id)
        if binding['defaultWorkflowId'] not in workflows:
            raise VerifyError(f'Issue template {template_id} defaultWorkflowId is unknown: {binding["defaultWorkflowId"]}')
        for workflow_id in binding['allowedWorkflowIds']:
            if workflow_id not in workflows:
                raise VerifyError(f'Issue template {template_id} allowedWorkflowId is unknown: {workflow_id}')
        for gate_id in binding['requiredStartGates'] + binding['managedGates']:
            if gate_id not in GATES:
                raise VerifyError(f'Issue template {template_id} references unknown gate: {gate_id}')
        template_path = dist / 'multica' / 'issue-templates' / binding['templateFile']
        require_text(template_path, f"templateId: {template_id}")
        require_text(template_path, f"defaultWorkflowId: {binding['defaultWorkflowId']}")
        require_text(template_path, 'WorkflowInvocation candidate')

    known_artifact_types = {contract['artifactType'] for contract in expected_artifact_contracts()}
    seen_action_ids = set()
    for action in expected_actions:
        action_id = action['actionId']
        if action_id in seen_action_ids:
            raise VerifyError(f'Duplicate artifact next action id: {action_id}')
        seen_action_ids.add(action_id)
        if action['suggestedWorkflowId'] not in workflows:
            raise VerifyError(f'Artifact next action {action_id} suggests unknown workflow: {action["suggestedWorkflowId"]}')
        if not action['fromArtifactTypes']:
            raise VerifyError(f'Artifact next action {action_id} must declare source artifact types')
        unknown_artifacts = sorted(set(action['fromArtifactTypes']) - known_artifact_types)
        if unknown_artifacts:
            raise VerifyError(f'Artifact next action {action_id} references unknown artifact types: {unknown_artifacts}')
        for gate_id in action['requiredSatisfiedGates']:
            if gate_id not in GATES:
                raise VerifyError(f'Artifact next action {action_id} references unknown gate: {gate_id}')


def verify_cross_artifact_contracts(root: Path, adapter_root: Path, manifest: dict) -> None:
    dist = root / 'dist'
    workflows = workflow_by_id()
    workflow_ids = [workflow.workflow_id for workflow in EXPECTED_WORKFLOWS]
    role_agent_ids = list(EXPECTED_ROLE_AGENTS)
    expected_tool_paths = expected_adapter_script_paths(adapter_root)
    expected_preflight_paths = [f'dist/preflight/{name}' for name in PREFLIGHT_ARTIFACTS]
    expected_task_graph_paths = [f'dist/task-graphs/{name}' for name in TASK_GRAPHS]
    expected_validator_paths = [f'validators/{name}' for name in VALIDATOR_SCRIPTS]

    manifest_workflow_ids = [item.get('workflowId') for item in manifest.get('workflows', [])]
    require_equal_list('runtime manifest workflows', workflow_ids, manifest_workflow_ids)
    require_equal_set('runtime manifest roleAgents', role_agent_ids, [item.get('agentId') for item in manifest.get('roleAgents', [])])
    require_equal_list('runtime manifest requiredCapabilities', REQUIRED_CAPABILITIES, manifest.get('requiredCapabilities', []))
    require_equal_list('runtime manifest optionalMcpServers', OPTIONAL_MCP_SERVERS, manifest.get('optionalMcpServers', []))
    require_equal_list('runtime manifest gates', GATES, manifest_values(manifest, 'gates'))
    require_equal_list('runtime manifest triggers', TRIGGERS, manifest_values(manifest, 'triggers'))
    require_equal_list('runtime manifest schemas', SCHEMAS, manifest_values(manifest, 'schemas'))
    require_equal_list('runtime manifest mcpExamples', MCP_EXAMPLES, manifest_values(manifest, 'mcpExamples'))
    require_equal_list('runtime manifest issueTemplates', ISSUE_TEMPLATES, manifest_values(manifest, 'issueTemplates'))
    require_equal_list('runtime manifest autopilots', AUTOPILOTS, manifest_values(manifest, 'autopilots'))
    require_equal_list('runtime manifest validators', VALIDATORS, manifest_values(manifest, 'validators'))
    require_equal_list('runtime manifest taskGraphs', expected_task_graph_paths, manifest_values(manifest, 'taskGraphs', 'path'))
    require_equal_list('runtime manifest preflightArtifacts', expected_preflight_paths, manifest_values(manifest, 'preflightArtifacts', 'path'))
    require_equal_list('runtime manifest validatorScripts', expected_validator_paths, manifest_values(manifest, 'validatorScripts', 'path'))
    require_equal_set('runtime manifest toolScripts', expected_tool_paths, manifest_values(manifest, 'toolScripts', 'path'))

    manifest_workflows = {item.get('workflowId'): item for item in manifest.get('workflows', []) if isinstance(item, dict)}
    manifest_role_agents = {item.get('agentId') for item in manifest.get('roleAgents', []) if isinstance(item, dict)}
    manifest_gates = set(manifest_values(manifest, 'gates'))
    for workflow in EXPECTED_WORKFLOWS:
        path = dist / 'workflows' / workflow.filename
        metadata = parse_generated_workflow_yaml(path)
        record = manifest_workflows.get(workflow.workflow_id, {})
        if record.get('file') != f'dist/workflows/{workflow.filename}':
            raise VerifyError(f'Runtime manifest workflow file mismatch for {workflow.workflow_id}')
        if record.get('sourceKind') != workflow.source_kind:
            raise VerifyError(f'Runtime manifest workflow sourceKind mismatch for {workflow.workflow_id}')
        if record.get('sourcePath') != workflow.source_path.as_posix():
            raise VerifyError(f'Runtime manifest workflow sourcePath mismatch for {workflow.workflow_id}')

        expected_metadata = {
            'workflowId': workflow.workflow_id,
            'sourceKind': workflow.source_kind,
            'sourcePath': workflow.source_path.as_posix(),
            'executionMode': workflow.execution_mode,
        }
        for key, expected in expected_metadata.items():
            if metadata.get(key) != expected:
                raise VerifyError(f'{path} {key} mismatch: expected={expected} actual={metadata.get(key)}')
        require_equal_list(f'{workflow.workflow_id} requiredCapabilities', REQUIRED_CAPABILITIES, metadata.get('requiredCapabilities', []))
        require_equal_list(f'{workflow.workflow_id} requiredArtifacts', workflow.required_artifacts, metadata.get('requiredArtifacts', []))
        require_equal_list(f'{workflow.workflow_id} outputArtifacts', workflow.output_artifacts, metadata.get('outputArtifacts', []))
        require_equal_list(f'{workflow.workflow_id} gates', workflow.gate_ids, metadata.get('gates', []))
        require_equal_list(f'{workflow.workflow_id} roleAgents', workflow.role_agent_ids, metadata.get('roleAgents', []))

        for agent_id in metadata.get('roleAgents', []):
            if agent_id not in EXPECTED_ROLE_AGENTS or agent_id not in manifest_role_agents:
                raise VerifyError(f'{path} references unknown role agent: {agent_id}')
            require_file(dist / 'agents' / f'{agent_id}.md')
        for gate_id in metadata.get('gates', []):
            if gate_id not in GATES or gate_id not in manifest_gates:
                raise VerifyError(f'{path} references unknown gate: {gate_id}')
            require_file(dist / 'gates' / f'{gate_id}.yaml')

    runtime_capabilities = load_json(dist / 'preflight' / 'runtime-capabilities.json')
    require_equal_list('runtime-capabilities requiredCapabilities', REQUIRED_CAPABILITIES, runtime_capabilities.get('requiredCapabilities', []))
    require_equal_list('runtime-capabilities optionalMcpServers', OPTIONAL_MCP_SERVERS, runtime_capabilities.get('optionalMcpServers', []))

    invocation_contract = load_json(dist / 'preflight' / 'workflow-invocation-contract.json')
    require_equal_list('workflow-invocation-contract requiredCapabilities', REQUIRED_CAPABILITIES, invocation_contract.get('requiredCapabilities', []))
    if invocation_contract.get('artifactStoreContract') != expected_artifact_store_contract():
        raise VerifyError('workflow-invocation-contract artifactStoreContract mismatch')
    if invocation_contract.get('gateTransitionContract') != expected_gate_transition_contract():
        raise VerifyError('workflow-invocation-contract gateTransitionContract mismatch')
    if invocation_contract.get('roleTaskContract') != expected_role_task_contract():
        raise VerifyError('workflow-invocation-contract roleTaskContract mismatch')
    require_equal_list('workflow-invocation-contract optionalMcpServers', OPTIONAL_MCP_SERVERS, invocation_contract.get('optionalMcpServers', []))
    contract_workflows = invocation_contract.get('workflows', {})
    require_equal_set('workflow-invocation-contract workflows', workflow_ids, contract_workflows.keys())
    require_equal_list('workflow-invocation-contract artifactContracts', expected_artifact_contracts(), invocation_contract.get('artifactContracts', []))
    require_equal_list('workflow-invocation-contract roleAgentContracts', expected_role_agent_contracts(), invocation_contract.get('roleAgentContracts', []))
    require_equal_list('workflow-invocation-contract gateContracts', expected_gate_contracts(), invocation_contract.get('gateContracts', []))
    require_equal_list('workflow-invocation-contract compatibilityCommands', expected_compatibility_commands(), invocation_contract.get('compatibilityCommands', []))
    require_equal_list('workflow-invocation-contract issueTemplateBindings', expected_issue_template_bindings(), invocation_contract.get('issueTemplateBindings', []))
    require_equal_list('workflow-invocation-contract intentRouterRules', expected_intent_router_rules(), invocation_contract.get('intentRouterRules', []))
    require_equal_list('workflow-invocation-contract artifactNextActions', expected_artifact_next_actions(), invocation_contract.get('artifactNextActions', []))
    for workflow_id, workflow in workflows.items():
        contract = contract_workflows.get(workflow_id, {})
        if contract.get('workflowId') != workflow_id:
            raise VerifyError(f'workflow-invocation-contract workflowId mismatch for {workflow_id}')
        if contract.get('executionMode') != workflow.execution_mode:
            raise VerifyError(f'workflow-invocation-contract executionMode mismatch for {workflow_id}')
        require_equal_list(f'{workflow_id} contract requiredArtifacts', workflow.required_artifacts, contract.get('requiredArtifacts', []))
        require_equal_list(f'{workflow_id} contract outputArtifacts', workflow.output_artifacts, contract.get('outputArtifacts', []))
        require_equal_list(f'{workflow_id} contract requiredGates', workflow.gate_ids, contract.get('requiredGates', []))
        require_equal_list(f'{workflow_id} contract requiredCapabilities', REQUIRED_CAPABILITIES, contract.get('requiredCapabilities', []))
        require_equal_list(f'{workflow_id} contract mcpRequirements', WORKFLOW_MCP_REQUIREMENTS.get(workflow_id, ()), contract.get('mcpRequirements', []))

    rule_ids = [rule['id'] for rule in ILLEGAL_TRANSITION_RULES]
    contract_rules = invocation_contract.get('illegalTransitionRules', [])
    require_equal_list('workflow-invocation-contract illegalTransitionRules', rule_ids, [rule.get('id') for rule in contract_rules])
    contract_rule_by_id = {rule.get('id'): rule for rule in contract_rules}
    for expected_rule in ILLEGAL_TRANSITION_RULES:
        actual_rule = contract_rule_by_id.get(expected_rule['id'], {})
        if actual_rule.get('blocks') != expected_rule['blocks']:
            raise VerifyError(f'Illegal transition rule blocks mismatch for {expected_rule["id"]}')
        if actual_rule.get('description') != expected_rule['description']:
            raise VerifyError(f'Illegal transition rule description mismatch for {expected_rule["id"]}')
        require_equal_list(f'{expected_rule["id"]} requiresArtifacts', expected_rule['requiresArtifacts'], actual_rule.get('requiresArtifacts', []))
        require_equal_list(f'{expected_rule["id"]} requiresGates', expected_rule['requiresGates'], actual_rule.get('requiresGates', []))
        unknown_gates = sorted(set(actual_rule.get('requiresGates', [])) - set(GATES))
        if unknown_gates:
            raise VerifyError(f'Illegal transition rule {expected_rule["id"]} references unknown gates: {unknown_gates}')

    invocation_schema = load_json(dist / 'schemas' / 'workflow-invocation.schema.json')
    properties = invocation_schema.get('properties', {})
    defs = invocation_schema.get('$defs', {})
    require_equal_list('workflow-invocation schema workflow enum', workflow_ids, properties.get('workflowId', {}).get('enum', []))
    require_equal_list('workflow-invocation schema executionMode enum', sorted({workflow.execution_mode for workflow in EXPECTED_WORKFLOWS}), properties.get('executionMode', {}).get('enum', []))
    require_equal_list('workflow-invocation schema issueTemplateId enum', [binding['templateId'] for binding in ISSUE_TEMPLATE_BINDINGS], properties.get('issueTemplateId', {}).get('enum', []))
    require_equal_list('workflow-invocation schema artifactNextActionId enum', [action['actionId'] for action in ARTIFACT_NEXT_ACTIONS], properties.get('artifactNextActionId', {}).get('enum', []))
    require_equal_list('workflow-invocation schema capability enum', REQUIRED_CAPABILITIES, properties.get('requiredCapabilities', {}).get('items', {}).get('enum', []))
    require_equal_list('workflow-invocation schema gate enum', GATES, defs.get('gateSet', {}).get('properties', {}).get('required', {}).get('items', {}).get('enum', []))
    require_equal_list('workflow-invocation schema MCP enum', OPTIONAL_MCP_SERVERS, defs.get('mcpRequirement', {}).get('properties', {}).get('name', {}).get('enum', []))
    require_equal_list('workflow-invocation schema artifact type enum', [contract['artifactType'] for contract in ARTIFACT_CONTRACTS], defs.get('sourceArtifact', {}).get('properties', {}).get('type', {}).get('enum', []))
    require_equal_list('workflow-invocation schema producedByWorkflow enum', workflow_ids, defs.get('sourceArtifact', {}).get('properties', {}).get('producedByWorkflow', {}).get('enum', []))
    for workflow_id, mcp_requirements in WORKFLOW_MCP_REQUIREMENTS.items():
        if workflow_id not in workflows:
            raise VerifyError(f'WORKFLOW_MCP_REQUIREMENTS references unknown workflow: {workflow_id}')
        unknown_mcp = sorted(set(mcp_requirements) - set(OPTIONAL_MCP_SERVERS))
        if unknown_mcp:
            raise VerifyError(f'WORKFLOW_MCP_REQUIREMENTS for {workflow_id} references unknown MCP servers: {unknown_mcp}')

    sdd_workflow = workflows['subagent-driven-development']
    graph = load_json(dist / 'task-graphs' / 'subagent-driven-development.task-graph.json')
    if graph.get('workflowId') != sdd_workflow.workflow_id:
        raise VerifyError('SDD task graph workflowId does not match workflow spec')
    if graph.get('executionMode') != sdd_workflow.execution_mode:
        raise VerifyError('SDD task graph executionMode does not match workflow spec')
    require_equal_list('SDD task graph requiredInputArtifacts', sdd_workflow.required_artifacts, graph.get('requiredInputArtifacts', []))

    tool_manifest = load_json(dist / 'tools' / 'tool-manifest.json')
    require_equal_set('tool-manifest scripts', expected_tool_paths, [item.get('path') for item in tool_manifest.get('scripts', [])])
    require_equal_list('tool-manifest validatorScripts', expected_validator_paths, [item.get('path') for item in tool_manifest.get('validatorScripts', [])])
    tool_runtime_paths = {item.get('runtimePath') for item in tool_manifest.get('scripts', [])}
    nodes = graph.get('nodes', [])
    node_ids = [node.get('nodeId') for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise VerifyError(f'SDD task graph has duplicate node ids: {node_ids}')
    node_id_set = set(node_ids)
    for node in nodes:
        node_id = node.get('nodeId')
        role_agent = node.get('roleAgent')
        if role_agent not in sdd_workflow.role_agent_ids:
            raise VerifyError(f'SDD task graph node {node_id} role agent is not in workflow contract: {role_agent}')
        if role_agent not in manifest_role_agents:
            raise VerifyError(f'SDD task graph node {node_id} references missing manifest role agent: {role_agent}')
        require_file(dist / 'agents' / f'{role_agent}.md')
        if node.get('freshContext') != 'required':
            raise VerifyError(f'SDD task graph node {node_id} does not require fresh context')
        for dependency in node.get('toolDependencies', []):
            if dependency not in tool_runtime_paths:
                raise VerifyError(f'SDD task graph node {node_id} references unknown tool dependency: {dependency}')
    for edge in graph.get('edges', []):
        from_id = edge.get('from')
        to_id = edge.get('to')
        if from_id not in node_id_set or to_id not in node_id_set:
            raise VerifyError(f'SDD task graph edge references unknown node: {from_id} -> {to_id}')


def verify(root: Path, adapter_root: Path) -> None:
    root = root.resolve()
    adapter_root = adapter_root.resolve()
    if not root.is_dir():
        raise VerifyError(f'Missing runtime root: {root}')
    if not (adapter_root / 'manifest.json').is_file():
        raise VerifyError(f'Missing adapter root manifest: {adapter_root}')
    manifest = verify_manifest(root)
    verify_expected_files(root, adapter_root)
    verify_source_snapshots(root)
    verify_generated_text(root)
    verify_workflow_content(root)
    verify_squad_contracts(root, manifest)
    verify_autopilot_contracts(root, manifest)
    verify_artifact_contracts(root, manifest)
    verify_role_agent_contracts(root, manifest)
    verify_gate_contracts(root, manifest)
    verify_trigger_contracts(root)
    verify_trigger_catalogs(root, manifest)
    verify_preflight_artifacts(root, manifest)
    verify_sdd_task_graph(root, manifest)
    verify_schemas(root)
    verify_validator_scripts(root, manifest)
    verify_tool_scripts(root, adapter_root, manifest)
    verify_cross_artifact_contracts(root, adapter_root, manifest)
    print(f'Multica Superpowers runtime OK: {root}')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime_root')
    parser.add_argument('--adapter-root', default=Path(__file__).resolve().parents[1].as_posix())
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    verify(Path(args.runtime_root), Path(args.adapter_root))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
