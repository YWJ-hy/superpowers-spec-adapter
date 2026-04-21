#!/usr/bin/env python3
"""Resolve adapter target directories."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def resolve_installed_superpowers() -> Path | None:
    installed = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'
    if not installed.is_file():
        return None
    data = json.loads(installed.read_text(encoding='utf-8'))
    entries = data.get('plugins', {}).get('superpowers@claude-plugins-official', [])
    if not entries:
        return None
    install_path = entries[0].get('installPath')
    if not install_path:
        return None
    path = Path(install_path)
    return path if path.is_dir() else None


def resolve_target(base: Path, explicit: str | None) -> tuple[Path, str]:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if (candidate / 'hooks' / 'hooks.json').is_file():
            return candidate, 'explicit-plugin-dir'
        if (candidate / 'superpowers' / 'hooks' / 'hooks.json').is_file():
            return candidate / 'superpowers', 'explicit-repo-root'
        raise SystemExit(f'Unsupported target: {candidate}')

    installed = resolve_installed_superpowers()
    if installed:
        return installed, 'installed-plugin'

    repo_local = base / 'superpowers'
    if (repo_local / 'hooks' / 'hooks.json').is_file():
        return repo_local, 'repo-local'

    raise SystemExit('Could not resolve a Superpowers target. Pass an explicit path or install the plugin first.')


def main() -> int:
    explicit = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    target, mode = resolve_target(Path.cwd(), explicit)
    print(json.dumps({'target': str(target), 'mode': mode}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
