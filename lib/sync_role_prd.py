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
    output_format: str
    prd_template_name: str
    primary_artifact: str
    fallback_artifact: str

    @property
    def agent_path(self) -> Path:
        return Path('overlays/agents') / f'{self.agent_name}.md'

    @property
    def prd_template(self) -> str:
        return self.prd_template_name


ROLE_CONFIGS = (
    RoleConfig(
        role='frontend',
        label='frontend markdown',
        agent_name='lanhu-frontend-requirements-analyst',
        template_path=Path('role-prd/frontend.md'),
        output_h1='# 前端开发角色视角 PRD',
        allowed_content='frontend UI control types and interaction expectations, page display, page state flow, permission visibility, analytics needs, and frontend/backend collaboration information, without component library or code implementation details',
        output_format='markdown',
        prd_template_name='frontend_role_prd',
        primary_artifact='index.md plus prd.md or prds/*.md',
        fallback_artifact='not applicable',
    ),
    RoleConfig(
        role='frontend',
        label='frontend html',
        agent_name='lanhu-frontend-html-requirements-analyst',
        template_path=Path('role-prd/frontend_outputHtml.md'),
        output_h1='# 前端开发角色视角 PRD',
        allowed_content='complete frontend PRD content split between a visual HTML PRD main document and a 1:1 Lanhu interaction prototype, including page display, field UI, interaction rules, page state flow, permission visibility, exceptions, analytics needs, and frontend/backend collaboration information, without production frontend implementation details',
        output_format='html',
        prd_template_name='frontend_html_role_prd',
        primary_artifact='index.md plus index.html plus prototype/index.html',
        fallback_artifact='index.md plus prd.md when the requirement is text-only and has no page, UI, or interaction surface',
    ),
    RoleConfig(
        role='backend',
        label='backend markdown',
        agent_name='lanhu-backend-requirements-analyst',
        template_path=Path('role-prd/backend.md'),
        output_h1='# 后端开发角色视角 PRD',
        allowed_content='backend business objects, business flows, business rules, data needs, permissions, audit/logging requirements, statistics/query needs, and security/compliance requirements, without database/API/architecture implementation details',
        output_format='markdown',
        prd_template_name='backend_role_prd',
        primary_artifact='index.md plus prd.md or prds/*.md',
        fallback_artifact='not applicable',
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
            f'Generated verbatim from `{config.template_path.as_posix()}`. Treat the template content below as the selected role PRD contract and the complete {config.label} role PRD source template.',
            '',
            f'{fence}markdown',
            content,
            fence,
        ]
    )


def render_format_contract(config: RoleConfig) -> str:
    if config.output_format == 'html':
        return '\n'.join(
            [
                'This agent is the frontend HTML PRD analyst. It is separate from `lanhu-frontend-requirements-analyst` and must not generate the Markdown-mode frontend PRD package unless the text-only fallback applies.',
                '',
                'Required output contract for `outputPreference.format: html`:',
                '- Create `index.md` as the package entrypoint, role marker, reading guide, and relationship authority.',
                '- For page/UI/interaction requirements, write package-root `index.html` as the complete frontend PRD main document by copying the fixed canonical shell fenced in `role-prd/frontend_outputHtml.md` and replacing only placeholders plus section content slots.',
                '- For page/UI/interaction requirements, also write `prototype/index.html` as the 1:1 Lanhu interaction prototype for visual layout, page structure, source-region control placement, state probes, dialogs, drawers, and multi-step interaction visualization; simple CSS/JS is allowed for layout and basic interaction display, but not complex implementation.',
                '- Do not write a full `prd.md` in normal HTML mode; `index.html` and `prototype/index.html` together are the detailed PRD artifacts.',
                '- If the requirement is text-only and has no page, field UI, operation, page state, or interaction surface, set `htmlPrdCompliance.fallbackToMarkdown: true`, explain `fallbackReason`, and write `index.md` plus `prd.md` instead of forcing HTML.',
                '- `index.md` must explain file roles and instruct Superpowers / AI to parse current HTML sections dynamically; it must not hard-code or rely on a fixed list of internal HTML chapters.',
                '- `index.html` and `prototype/index.html` must link to each other and must be interpreted together. Any conflict between them must be raised as a confirmation question instead of being resolved by assumption.',
                '- `index.html` and `prototype/index.html` must avoid external assets except the required Mermaid CDN module script, framework code, production component structure, real API calls, or implementation architecture.',
                '- `index.html` and `prototype/index.html` must render Mermaid in the browser with `startOnLoad: false` and explicit DOM-time rendering so hidden navigation sections do not suppress diagrams.',
                '- Mermaid diagrams must remain visible in the browser; if mindmap is unstable because of CDN version, initialization timing, hidden containers, or complexity, switch to flowchart or split the diagram instead of leaving it invisible.',
                '- Backend output must never use this agent or write `.html` files.',
            ]
        )
    return '\n'.join(
        [
            f'This agent handles `{config.output_format}` output only.',
            '',
            f'Required output contract for `outputPreference.format: {config.output_format}`:',
            '- Create `index.md` as the package entrypoint, role marker, reading guide, and relationship authority.',
            '- Write either `prd.md` or `prds/*.md` depending on `deliveryBoundaryCount`.',
            '- Do not write `index.html` or any `.html` file.',
            '- If the main session passes `outputPreference.format: html` to this Markdown agent, return `status: need_role` or `status: partial` with a caveat asking the main session to route to the HTML frontend analyst instead.',
        ]
    )


def render_html_compliance_contract(config: RoleConfig) -> str:
    if config.output_format != 'html':
        return 'HTML PRD compliance is not applicable for this agent. Return `htmlPrdCompliance.applicable: false` and do not write `.html` files.'
    return '\n'.join(
        [
            'HTML PRD compliance is mandatory for successful non-fallback HTML output:',
            '- `htmlPrdCompliance.applicable: true`',
            '- `checkedAgainstFullHtmlSourceTemplate: true`',
            '- `canonicalIndexHtmlShell: true`',
            '- `canonicalIndexHtmlShellVersion: lanhu-frontend-html-prd-index-shell-v1`',
            '- `selfContained: true` means no external resources except the required Mermaid CDN module script',
            '- `prototypeArtifactPresent: true`',
            '- `prototypeVisualLayoutMatchesLanhuEvidence: true`',
            '- `prototypeControlsRemainInSourceRegions: true`',
            '- `prototypeLayoutApproximationCaveats: []` unless source evidence is insufficient to reproduce exact dimensions or spacing',
            '- `prototypeDirectoryized: true`',
            '- `prototypeLinkedFromIndexHtml: true`',
            '- `indexMdDynamicHtmlParsingGuidance: true`',
            '- `mermaidModuleScriptPresent: true`',
            '- `mermaidBlocksBrowserRenderable: true`',
            '- `onlyAllowedExternalAssetIsMermaidCdn: true`',
            '- `prdPrototypeConflictQuestionsRaised: true` when conflicts exist, otherwise `false` with no unresolved conflict',
            '- `externalAssetsDetected: []` except the required Mermaid CDN module script must not be reported as a violation',
            '- `productionImplementationDetected: []`',
            '- `rawHtmlInjectionDetected: []`',
            '- `fallbackToMarkdown: false` unless the text-only fallback is used',
            '- `fallbackReason: null` unless the text-only fallback is used',
        ]
    )


def render_agent(root: Path, config: RoleConfig) -> str:
    skeleton = (root / COMMON_SKELETON).read_text(encoding='utf-8')
    replacements = {
        '{{AGENT_NAME}}': config.agent_name,
        '{{ROLE}}': config.role,
        '{{ROLE_LABEL}}': config.label,
        '{{OUTPUT_FORMAT}}': config.output_format,
        '{{PRD_TEMPLATE}}': config.prd_template,
        '{{ROLE_PRD_TEMPLATE_PATH}}': config.template_path.as_posix(),
        '{{ROLE_PRD_SOURCE_PATHS}}': f'`{config.template_path.as_posix()}`',
        '{{ROLE_OUTPUT_H1}}': config.output_h1,
        '{{ROLE_ALLOWED_CONTENT}}': config.allowed_content,
        '{{PRIMARY_ARTIFACT}}': config.primary_artifact,
        '{{FALLBACK_ARTIFACT}}': config.fallback_artifact,
        '{{FORMAT_CONTRACT}}': render_format_contract(config),
        '{{HTML_PRD_COMPLIANCE_CONTRACT}}': render_html_compliance_contract(config),
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
