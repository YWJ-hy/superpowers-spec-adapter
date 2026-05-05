#!/usr/bin/env python3
"""Synchronize role PRD source templates into self-contained overlays."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

START_MARKER = '<!-- superpower-adapter:role-prd-templates:start -->'
END_MARKER = '<!-- superpower-adapter:role-prd-templates:end -->'

TARGET_FILES = (
    Path('overlays/agents/lanhu-requirements-analyst.md'),
    Path('overlays/commands/lanhu-requirements.md'),
)

TEMPLATE_FILES = (
    ('Frontend', Path('role-prd/frontend.md')),
    ('Backend', Path('role-prd/backend.md')),
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


def render_block(root: Path) -> str:
    sections = [
        START_MARKER,
        '<!-- Generated from role-prd/*.md. Run `./manage.sh install` or `python3 lib/sync_role_prd.py sync` to refresh. -->',
    ]
    for label, relative in TEMPLATE_FILES:
        content = (root / relative).read_text(encoding='utf-8').rstrip()
        fence = fence_for(content)
        sections.extend(
            [
                '',
                f'### {label} role PRD source template',
                '',
                f'Generated verbatim from `{relative.as_posix()}`. Treat the template content below as the selected role PRD contract.',
                '',
                f'{fence}markdown',
                content,
                fence,
            ]
        )
    sections.extend(['', END_MARKER])
    return '\n'.join(sections)


def replace_block(text: str, replacement: str, path: Path) -> str:
    start = text.find(START_MARKER)
    if start == -1:
        raise SystemExit(f'Missing role PRD sync start marker: {path}')
    end = text.find(END_MARKER, start)
    if end == -1:
        raise SystemExit(f'Missing role PRD sync end marker: {path}')
    end += len(END_MARKER)
    return text[:start] + replacement + text[end:]


def sync(root: Path) -> bool:
    replacement = render_block(root)
    changed = False
    for relative in TARGET_FILES:
        path = root / relative
        original = path.read_text(encoding='utf-8')
        updated = replace_block(original, replacement, path)
        if updated != original:
            path.write_text(updated, encoding='utf-8')
            changed = True
            print(f'Updated {relative.as_posix()}')
    return changed


def installed_relative(relative: Path) -> Path:
    parts = relative.parts
    if parts and parts[0] == 'overlays':
        return Path(*parts[1:])
    return relative


def check(root: Path, target_root: Path | None = None) -> bool:
    replacement = render_block(root)
    ok = True
    check_root = target_root or root
    for relative in TARGET_FILES:
        check_relative = installed_relative(relative) if target_root else relative
        path = check_root / check_relative
        original = path.read_text(encoding='utf-8')
        updated = replace_block(original, replacement, path)
        if updated != original:
            location = 'installed file' if target_root else 'overlay file'
            print(f'Role PRD templates are out of sync in {location}: {check_relative.as_posix()}', file=sys.stderr)
            ok = False
    return ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Synchronize role PRD source templates into overlays.')
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
