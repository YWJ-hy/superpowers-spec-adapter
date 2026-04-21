#!/usr/bin/env python3
"""Patch or verify Superpowers SessionStart hook config for superpower-adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CLAUDE_COMMAND = '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-spec-index'
CURSOR_COMMAND = './hooks/session-spec-index'


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
    exists = any(h.get('command') == CLAUDE_COMMAND for h in commands)

    if mode == 'install' and not exists:
        commands.append({'type': 'command', 'command': CLAUDE_COMMAND, 'async': False})
        save_json(path, data)
        return True
    if mode == 'uninstall' and exists:
        event['hooks'] = [h for h in commands if h.get('command') != CLAUDE_COMMAND]
        save_json(path, data)
        return True
    if mode == 'verify' and not exists:
        raise SystemExit(f'Missing session-spec-index hook in {path}')
    return False


def patch_cursor(path: Path, mode: str) -> bool:
    data = load_json(path)
    hooks = data.setdefault('hooks', {}).setdefault('sessionStart', [])
    exists = any(h.get('command') == CURSOR_COMMAND for h in hooks)

    if mode == 'install' and not exists:
        hooks.append({'command': CURSOR_COMMAND})
        save_json(path, data)
        return True
    if mode == 'uninstall' and exists:
        data['hooks']['sessionStart'] = [h for h in hooks if h.get('command') != CURSOR_COMMAND]
        save_json(path, data)
        return True
    if mode == 'verify' and not exists:
        raise SystemExit(f'Missing session-spec-index hook in {path}')
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
