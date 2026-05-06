#!/usr/bin/env python3
"""Resolve adapter target directories."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def installed_superpowers_entries() -> list[dict[str, object]]:
    installed = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'
    if not installed.is_file():
        return []
    data = json.loads(installed.read_text(encoding='utf-8'))
    entries = data.get('plugins', {}).get('superpowers@claude-plugins-official', [])
    targets: list[dict[str, object]] = []
    seen: set[Path] = set()
    for entry in entries:
        install_path = entry.get('installPath')
        if not install_path:
            continue
        path = Path(str(install_path)).expanduser().resolve()
        if not path.is_dir() or path in seen:
            continue
        seen.add(path)
        targets.append({
            'target': path.as_posix(),
            'mode': 'installed-plugin',
            'version': entry.get('version'),
            'scope': entry.get('scope'),
            'projectPath': entry.get('projectPath'),
        })
    return targets


def resolve_installed_superpowers() -> Path | None:
    entries = installed_superpowers_entries()
    if not entries:
        return None
    return Path(str(entries[0]['target']))


def resolve_target(base: Path, explicit: str | None) -> tuple[Path, str]:
    targets = resolve_targets(base, explicit)
    first = targets[0]
    return Path(str(first['target'])), str(first['mode'])


def resolve_targets(base: Path, explicit: str | None) -> list[dict[str, object]]:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if (candidate / 'hooks' / 'hooks.json').is_file():
            return [{'target': candidate.as_posix(), 'mode': 'explicit-plugin-dir'}]
        if (candidate / 'superpowers' / 'hooks' / 'hooks.json').is_file():
            return [{'target': (candidate / 'superpowers').as_posix(), 'mode': 'explicit-repo-root'}]
        raise SystemExit(f'Unsupported target: {candidate}')

    installed = installed_superpowers_entries()
    if installed:
        return installed

    repo_local = base / 'superpowers'
    if (repo_local / 'hooks' / 'hooks.json').is_file():
        return [{'target': repo_local.as_posix(), 'mode': 'repo-local'}]

    raise SystemExit('Could not resolve a Superpowers target. Pass an explicit path or install the plugin first.')


def main() -> int:
    args = sys.argv[1:]
    all_targets = bool(args and args[0] == '--all')
    if all_targets:
        args = args[1:]
    explicit = args[0] if args and args[0] else None
    targets = resolve_targets(Path.cwd(), explicit)
    if all_targets:
        print(json.dumps({'targets': targets}))
    else:
        first = targets[0]
        print(json.dumps({'target': first['target'], 'mode': first['mode']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
