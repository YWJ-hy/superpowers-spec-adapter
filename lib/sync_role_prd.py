#!/usr/bin/env python3
"""Generate self-contained Lanhu role PRD analyst agents."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from subagent_models import apply_agent_model

COMMON_SKELETON = Path('overlays/agents/lanhu-requirements-analyst.common.md')


@dataclass(frozen=True)
class RoleConfig:
    role: str
    label: str
    agent_name: str
    template_path: Path
    output_h1: str
    allowed_content: str

    @property
    def agent_path(self) -> Path:
        return Path('overlays/agents') / f'{self.agent_name}.md'

    @property
    def prd_template(self) -> str:
        return f'{self.role}_role_prd'


ROLE_CONFIGS = (
    RoleConfig(
        role='frontend',
        label='frontend',
        agent_name='lanhu-frontend-requirements-analyst',
        template_path=Path('role-prd/frontend.md'),
        output_h1='# 前端开发角色视角 PRD',
        allowed_content='frontend UI control types and interaction expectations, page display, page state flow, permission visibility, analytics needs, and frontend/backend collaboration information, without component library or code implementation details',
    ),
    RoleConfig(
        role='backend',
        label='backend',
        agent_name='lanhu-backend-requirements-analyst',
        template_path=Path('role-prd/backend.md'),
        output_h1='# 后端开发角色视角 PRD',
        allowed_content='backend business objects, business flows, business rules, data needs, permissions, audit/logging requirements, statistics/query needs, and security/compliance requirements, without database/API/architecture implementation details',
    ),
)


def fence_for(text: str) -> str:
    longest = 0
    current = 0
    for char in text:
        if char == '`':
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return '`' * max(3, longest + 1)


def render_template_block(root: Path, config: RoleConfig) -> str:
    content = (root / config.template_path).read_text(encoding='utf-8').rstrip()
    fence = fence_for(content)
    return '\n'.join(
        [
            f'### {config.label.title()} role PRD source template',
            '',
            f'Generated verbatim from `{config.template_path.as_posix()}`. Treat the template content below as the selected role PRD contract and the complete {config.role} role PRD source template.',
            '',
            f'{fence}markdown',
            content,
            fence,
        ]
    )


def render_agent(root: Path, config: RoleConfig) -> str:
    skeleton = (root / COMMON_SKELETON).read_text(encoding='utf-8')
    replacements = {
        '{{AGENT_NAME}}': config.agent_name,
        '{{ROLE}}': config.role,
        '{{ROLE_LABEL}}': config.label,
        '{{PRD_TEMPLATE}}': config.prd_template,
        '{{ROLE_PRD_TEMPLATE_PATH}}': config.template_path.as_posix(),
        '{{ROLE_OUTPUT_H1}}': config.output_h1,
        '{{ROLE_ALLOWED_CONTENT}}': config.allowed_content,
        '{{ROLE_PRD_TEMPLATE_BLOCK}}': render_template_block(root, config),
    }
    rendered = skeleton
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    unresolved = [token for token in replacements if token in rendered]
    if unresolved:
        raise SystemExit(f'Unresolved placeholders in generated {config.agent_name}: {unresolved}')
    return rendered.rstrip() + '\n'


def installed_relative(relative: Path) -> Path:
    parts = relative.parts
    if parts and parts[0] == 'overlays':
        return Path(*parts[1:])
    return relative


def sync(root: Path) -> bool:
    changed = False
    for config in ROLE_CONFIGS:
        path = root / config.agent_path
        rendered = render_agent(root, config)
        original = path.read_text(encoding='utf-8') if path.exists() else None
        if original != rendered:
            path.write_text(rendered, encoding='utf-8')
            changed = True
            print(f'Updated {config.agent_path.as_posix()}')
    return changed


def check(root: Path, target_root: Path | None = None) -> bool:
    ok = True
    check_root = target_root or root
    for config in ROLE_CONFIGS:
        rendered = render_agent(root, config)
        if target_root:
            from subagent_models import model_for_agent

            model = model_for_agent(root, config.agent_name)
            if model:
                rendered = apply_agent_model(rendered, config.agent_name, model)
        relative = installed_relative(config.agent_path) if target_root else config.agent_path
        path = check_root / relative
        if not path.is_file():
            location = 'installed file' if target_root else 'overlay file'
            print(f'Missing generated Lanhu role analyst {location}: {relative.as_posix()}', file=sys.stderr)
            ok = False
            continue
        original = path.read_text(encoding='utf-8')
        if original != rendered:
            location = 'installed file' if target_root else 'overlay file'
            print(f'Lanhu role analyst is out of sync in {location}: {relative.as_posix()}', file=sys.stderr)
            ok = False
    return ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate self-contained Lanhu role PRD analyst agents.')
    parser.add_argument('mode', choices=('sync', 'check'))
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--target-root')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    target_root = Path(args.target_root).resolve() if args.target_root else None
    if args.mode == 'sync':
        sync(root)
    else:
        if not check(root, target_root):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
