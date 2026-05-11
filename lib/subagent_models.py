#!/usr/bin/env python3
"""Subagent model configuration helpers for superpower-adapter."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_FILE = 'adapter.config.json'
MODEL_PATTERN = re.compile(r'^[A-Za-z0-9._@/+:\-\[\]]+$')
SHORT_MODEL_NAMES = {'inherit', 'opus', 'sonnet', 'haiku'}

ADAPTER_AGENT_IDS = frozenset(
    {
        'wiki-researcher',
        'graphify-researcher',
        'lanhu-frontend-requirements-analyst',
        'lanhu-backend-requirements-analyst',
    }
)

UPSTREAM_TEMPLATE_IDS = frozenset(
    {
        'spec-document-reviewer',
        'plan-document-reviewer',
        'code-reviewer',
        'final-code-reviewer',
        'implementer',
        'spec-compliance-reviewer',
        'code-quality-reviewer',
    }
)


@dataclass(frozen=True)
class SubagentModelConfig:
    agents: dict[str, str]
    upstream_prompt_templates: dict[str, str]

    @property
    def has_effective_upstream_models(self) -> bool:
        return bool(self.upstream_prompt_templates)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise SystemExit(f'Invalid {CONFIG_FILE}: {exc}') from exc
    if not isinstance(data, dict):
        raise SystemExit(f'Invalid {CONFIG_FILE}: root must be an object')
    return data


def _normalize_section(raw: Any, known_ids: frozenset[str], section_name: str, allow_inherit: bool) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SystemExit(f'Invalid {CONFIG_FILE}: subagentModels.{section_name} must be an object')

    unknown = sorted(set(raw) - known_ids)
    if unknown:
        valid = ', '.join(sorted(known_ids))
        raise SystemExit(
            f'Invalid {CONFIG_FILE}: unknown subagentModels.{section_name} key(s): '
            f'{", ".join(unknown)}. Valid keys: {valid}'
        )

    normalized: dict[str, str] = {}
    for key, value in raw.items():
        model = _normalize_model(value, section_name, key)
        if model is None:
            continue
        if model == 'inherit' and not allow_inherit:
            continue
        normalized[key] = model
    return normalized


def _normalize_model(value: Any, section_name: str, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f'Invalid {CONFIG_FILE}: model for {section_name}.{key} must be a string or null')
    model = value.strip()
    if not model:
        return None
    if not MODEL_PATTERN.fullmatch(model):
        raise SystemExit(
            f'Invalid {CONFIG_FILE}: model for {section_name}.{key} contains unsupported characters: {value!r}'
        )
    if model in SHORT_MODEL_NAMES:
        return model
    return model


def load_subagent_model_config(root: Path) -> SubagentModelConfig:
    data = _load_json(root / CONFIG_FILE)
    raw = data.get('subagentModels', {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise SystemExit(f'Invalid {CONFIG_FILE}: subagentModels must be an object')

    allowed_top_keys = {'agents', 'upstreamPromptTemplates'}
    unknown_top_keys = sorted(set(raw) - allowed_top_keys)
    if unknown_top_keys:
        raise SystemExit(
            f'Invalid {CONFIG_FILE}: unknown subagentModels key(s): {", ".join(unknown_top_keys)}. '
            'Valid keys: agents, upstreamPromptTemplates'
        )

    agents = _normalize_section(raw.get('agents', {}), ADAPTER_AGENT_IDS, 'agents', allow_inherit=True)
    upstream = _normalize_section(
        raw.get('upstreamPromptTemplates', {}),
        UPSTREAM_TEMPLATE_IDS,
        'upstreamPromptTemplates',
        allow_inherit=False,
    )
    return SubagentModelConfig(agents=agents, upstream_prompt_templates=upstream)


def model_for_agent(root: Path, agent_name: str) -> str | None:
    return load_subagent_model_config(root).agents.get(agent_name)


def apply_agent_model_override(text: str, root: Path, relative: str | Path) -> str:
    relative_path = Path(relative)
    if len(relative_path.parts) != 2 or relative_path.parts[0] != 'agents':
        return text
    agent_name = relative_path.stem
    if agent_name not in ADAPTER_AGENT_IDS:
        return text
    model = model_for_agent(root, agent_name)
    if not model:
        return text
    return apply_agent_model(text, agent_name, model)


def apply_agent_model(text: str, agent_name: str, model: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        raise SystemExit(f'Missing frontmatter in adapter agent: {agent_name}')

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == '---':
            end_index = index
            break
    if end_index is None:
        raise SystemExit(f'Malformed frontmatter in adapter agent: {agent_name}')

    found_name = False
    model_index = None
    for index in range(1, end_index):
        line = lines[index]
        if line.startswith('name:') and line.split(':', 1)[1].strip() == agent_name:
            found_name = True
        if line.startswith('model:'):
            model_index = index
    if not found_name:
        raise SystemExit(f'Adapter agent frontmatter name does not match expected agent: {agent_name}')
    newline = '\n' if lines[0].endswith('\n') else ''
    model_line = f'model: {model}{newline}'
    if model_index is None:
        insert_at = end_index
        lines.insert(insert_at, model_line)
    else:
        lines[model_index] = model_line
    return ''.join(lines)
