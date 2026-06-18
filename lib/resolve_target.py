#!/usr/bin/env python3
"""Resolve adapter target directories."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter_manifest import min_superpowers_version, version_below  # noqa: E402

# manifest.json lives at the adapter root (the parent of this lib/ dir).
ADAPTER_ROOT = Path(__file__).resolve().parent.parent


def _floor() -> str:
    try:
        return min_superpowers_version(ADAPTER_ROOT)
    except Exception:
        return ''


def _split_by_floor(
    entries: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Partition discovered targets into (compatible, below-floor) by the adapter's minimum version.

    A target with no/unparseable version is treated as compatible — we only drop one we can prove is
    below the floor. This keeps the adapter from ever auto-installing into an incompatible (e.g.
    pre-6.0.0) Superpowers it was not written for.
    """
    floor = _floor()
    compatible: list[dict[str, object]] = []
    below: list[dict[str, object]] = []
    for entry in entries:
        if version_below(str(entry.get('version') or ''), floor):
            below.append(entry)
        else:
            compatible.append(entry)
    return compatible, below


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
    compatible, _ = _split_by_floor(installed_superpowers_entries())
    if not compatible:
        return None
    return Path(str(compatible[0]['target']))


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
        compatible, below = _split_by_floor(installed)
        for entry in below:
            print(
                f"Skipping incompatible Superpowers {entry.get('version')} at {entry.get('target')} "
                f"(adapter requires >= {_floor()}).",
                file=sys.stderr,
            )
        if compatible:
            return compatible
        # Every discovered target is below the floor: fail loudly rather than silently falling
        # through to a repo-local guess, so the user upgrades or passes an explicit target.
        raise SystemExit(
            f'All {len(below)} installed Superpowers target(s) are below the minimum {_floor()}; '
            'adapter requires >= ' + _floor() + '. Upgrade Superpowers, or pass an explicit target path.'
        )

    repo_local = base / 'superpowers'
    if (repo_local / 'hooks' / 'hooks.json').is_file():
        return [{'target': repo_local.as_posix(), 'mode': 'repo-local'}]

    raise SystemExit('Could not resolve a Superpowers target. Pass an explicit path or install the plugin first.')



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
