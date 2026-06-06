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

# Claude Code PostToolUse hook: remind the agent to run update-wiki after a merge
# that integrates a development branch (a "work accepted" moment), so durable
# knowledge review is not lost when the user merges outside
# finishing-a-development-branch. Matcher targets the Bash tool by name.
POST_TOOL_USE_MATCHER = 'Bash'
POST_TOOL_USE_COMMANDS = [
    '"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" post-merge-update-wiki',
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def _session_start_install(data: dict) -> bool:
    hooks = data.setdefault('hooks', {}).setdefault('SessionStart', [])
    if not hooks:
        hooks.append({'matcher': 'startup|clear|compact', 'hooks': []})
    event = hooks[0]
    commands = event.setdefault('hooks', [])
    changed = False
    before = len(commands)
    commands[:] = [h for h in commands if h.get('command') not in DEPRECATED_CLAUDE_COMMANDS]
    if len(commands) != before:
        changed = True
    existing_commands = {h.get('command') for h in commands}
    for command in CLAUDE_COMMANDS:
        if command not in existing_commands:
            commands.append({'type': 'command', 'command': command, 'async': False})
            changed = True
    return changed


def _post_tool_use_install(data: dict) -> bool:
    events = data.setdefault('hooks', {}).setdefault('PostToolUse', [])
    event = next((e for e in events if e.get('matcher') == POST_TOOL_USE_MATCHER), None)
    changed = False
    if event is None:
        event = {'matcher': POST_TOOL_USE_MATCHER, 'hooks': []}
        events.append(event)
        changed = True
    commands = event.setdefault('hooks', [])
    existing_commands = {h.get('command') for h in commands}
    for command in POST_TOOL_USE_COMMANDS:
        if command not in existing_commands:
            commands.append({'type': 'command', 'command': command, 'async': False})
            changed = True
    return changed


def _session_start_uninstall(data: dict) -> bool:
    hooks = data.get('hooks', {}).get('SessionStart', [])
    if not hooks:
        return False
    event = hooks[0]
    commands = event.get('hooks', [])
    filtered = [h for h in commands if h.get('command') not in [*CLAUDE_COMMANDS, *DEPRECATED_CLAUDE_COMMANDS]]
    if len(filtered) != len(commands):
        event['hooks'] = filtered
        return True
    return False


def _post_tool_use_uninstall(data: dict) -> bool:
    hooks_root = data.get('hooks', {})
    events = hooks_root.get('PostToolUse', [])
    if not events:
        return False
    changed = False
    remaining = []
    for event in events:
        commands = event.get('hooks', [])
        filtered = [h for h in commands if h.get('command') not in POST_TOOL_USE_COMMANDS]
        if len(filtered) != len(commands):
            changed = True
            # Drop only an event we just emptied via our own matcher.
            if event.get('matcher') == POST_TOOL_USE_MATCHER and not filtered:
                continue
        event['hooks'] = filtered
        remaining.append(event)
    if changed:
        if remaining:
            hooks_root['PostToolUse'] = remaining
        else:
            hooks_root.pop('PostToolUse', None)
    return changed


def _session_start_verify(path: Path, data: dict) -> None:
    commands = []
    hooks = data.get('hooks', {}).get('SessionStart', [])
    if hooks:
        commands = hooks[0].get('hooks', [])
    existing_commands = {h.get('command') for h in commands}
    missing = [command for command in CLAUDE_COMMANDS if command not in existing_commands]
    if missing:
        raise SystemExit(f'Missing adapter SessionStart hooks in {path}: {", ".join(missing)}')
    deprecated = [command for command in DEPRECATED_CLAUDE_COMMANDS if command in existing_commands]
    if deprecated:
        raise SystemExit(f'Deprecated adapter SessionStart hooks remain in {path}: {", ".join(deprecated)}')


def _post_tool_use_verify(path: Path, data: dict) -> None:
    present = set()
    for event in data.get('hooks', {}).get('PostToolUse', []):
        if event.get('matcher') != POST_TOOL_USE_MATCHER:
            continue
        for h in event.get('hooks', []):
            present.add(h.get('command'))
    missing = [command for command in POST_TOOL_USE_COMMANDS if command not in present]
    if missing:
        raise SystemExit(f'Missing adapter PostToolUse hooks in {path}: {", ".join(missing)}')


def patch_claude(path: Path, mode: str) -> bool:
    data = load_json(path)

    if mode == 'install':
        changed = False
        changed |= _session_start_install(data)
        changed |= _post_tool_use_install(data)
        if changed:
            save_json(path, data)
        return changed

    if mode == 'uninstall':
        changed = False
        changed |= _session_start_uninstall(data)
        changed |= _post_tool_use_uninstall(data)
        if changed:
            save_json(path, data)
        return changed

    _session_start_verify(path, data)
    _post_tool_use_verify(path, data)
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



def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", newline="\n")
        except (OSError, ValueError):
            pass

def main() -> int:
    _configure_stdio()
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
