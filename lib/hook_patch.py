#!/usr/bin/env python3
"""Clean or verify legacy Superpowers SessionStart hook config for superpower-adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CLAUDE_COMMANDS = []
CURSOR_COMMANDS = []
DEPRECATED_CLAUDE_COMMANDS = [
    '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-spec-index',
    '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-plan-context',
]
DEPRECATED_CURSOR_COMMANDS = [
    './hooks/session-spec-index',
    './hooks/session-plan-context',
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def patch_claude(path: Path, mode: str) -> bool:
    data = load_json(path)
    hooks = data.setdefault('hooks', {}).setdefault('SessionStart', [])
    if not hooks:
        hooks.append({'matcher': 'startup|clear|compact', 'hooks': []})
    event = hooks[0]
    commands = event.setdefault('hooks', [])
    existing_commands = {h.get('command') for h in commands}
    changed = False

    if mode == 'install':
        before = len(commands)
        commands[:] = [h for h in commands if h.get('command') not in DEPRECATED_CLAUDE_COMMANDS]
        if len(commands) != before:
            existing_commands = {h.get('command') for h in commands}
            changed = True
        for command in CLAUDE_COMMANDS:
            if command not in existing_commands:
                commands.append({'type': 'command', 'command': command, 'async': False})
                changed = True
        if changed:
            save_json(path, data)
        return changed

    if mode == 'uninstall':
        filtered = [h for h in commands if h.get('command') not in [*CLAUDE_COMMANDS, *DEPRECATED_CLAUDE_COMMANDS]]
        if len(filtered) != len(commands):
            event['hooks'] = filtered
            save_json(path, data)
            return True
        return False

    missing = [command for command in CLAUDE_COMMANDS if command not in existing_commands]
    if missing:
        raise SystemExit(f'Missing adapter SessionStart hooks in {path}: {", ".join(missing)}')
    deprecated = [command for command in DEPRECATED_CLAUDE_COMMANDS if command in existing_commands]
    if deprecated:
        raise SystemExit(f'Deprecated adapter SessionStart hooks remain in {path}: {", ".join(deprecated)}')
    return False


def patch_cursor(path: Path, mode: str) -> bool:
    data = load_json(path)
    hooks = data.setdefault('hooks', {}).setdefault('sessionStart', [])
    existing_commands = {h.get('command') for h in hooks}

    if mode == 'install':
        changed = False
        before = len(hooks)
        hooks[:] = [h for h in hooks if h.get('command') not in DEPRECATED_CURSOR_COMMANDS]
        if len(hooks) != before:
            existing_commands = {h.get('command') for h in hooks}
            changed = True
        for command in CURSOR_COMMANDS:
            if command not in existing_commands:
                hooks.append({'command': command})
                changed = True
        if changed:
            save_json(path, data)
        return changed

    if mode == 'uninstall':
        filtered = [h for h in hooks if h.get('command') not in [*CURSOR_COMMANDS, *DEPRECATED_CURSOR_COMMANDS]]
        if len(filtered) != len(hooks):
            data['hooks']['sessionStart'] = filtered
            save_json(path, data)
            return True
        return False

    missing = [command for command in CURSOR_COMMANDS if command not in existing_commands]
    if missing:
        raise SystemExit(f'Missing adapter sessionStart hooks in {path}: {", ".join(missing)}')
    deprecated = [command for command in DEPRECATED_CURSOR_COMMANDS if command in existing_commands]
    if deprecated:
        raise SystemExit(f'Deprecated adapter sessionStart hooks remain in {path}: {", ".join(deprecated)}')
    return False


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: hook_patch.py <install|uninstall|verify> <superpowers-dir>')

    mode = sys.argv[1]
    target = Path(sys.argv[2]).resolve()
    if mode not in {'install', 'uninstall', 'verify'}:
        raise SystemExit(f'Unsupported mode: {mode}')

    hook_dir = target / 'hooks'
    claude_path = hook_dir / 'hooks.json'
    cursor_path = hook_dir / 'hooks-cursor.json'

    changed = False
    changed |= patch_claude(claude_path, mode)
    changed |= patch_cursor(cursor_path, mode)

    if mode == 'verify':
        print('Hook config OK')
    elif changed:
        print(f'Hook config updated via {mode}')
    else:
        print(f'Hook config already satisfied for {mode}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
