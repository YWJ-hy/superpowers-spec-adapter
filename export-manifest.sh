#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_INPUT="${1:-}"
REPO_ROOT="$(cd "${2:-$(pwd)}" && pwd)"
TARGET_JSON="$(python3 "$SCRIPT_DIR/lib/resolve_target.py" "$TARGET_INPUT")"
TARGET_DIR="$(python3 - <<'PY' "$TARGET_JSON"
import json, sys
print(json.loads(sys.argv[1])['target'])
PY
)"
OUTPUT_PATH="${3:-}"
MANIFEST_PATH="$SCRIPT_DIR/manifest.json"
VERIFY_STATUS="passed"
if ! "$SCRIPT_DIR/verify.sh" "$TARGET_INPUT" >/dev/null 2>&1; then
  VERIFY_STATUS="failed"
fi

MANIFEST_JSON=$(python3 - <<'PY' "$MANIFEST_PATH" "$REPO_ROOT" "$TARGET_DIR" "$VERIFY_STATUS"
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
target_dir = Path(sys.argv[3])
verify_status = sys.argv[4]
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
marker = manifest['generatedMarker']
installed = []
missing = []
for rel in manifest['installedPaths']:
    path = target_dir / rel
    if path.is_file():
        installed.append(rel)
    else:
        missing.append(rel)

hook_states = {}
for rel in manifest.get('optionalPatchedPaths', []):
    path = target_dir / rel
    hook_states[rel] = path.is_file()

spec_root = repo_root / '.superpowers' / 'spec'
entry_index = spec_root / 'index.md'
ignore_file = spec_root / '.adapter-ignore'
ignored = []
default_ignored = ['draft', 'archive', 'examples']
if ignore_file.is_file():
    for line in ignore_file.read_text(encoding='utf-8').splitlines():
        value = line.strip()
        if value and not value.startswith('#'):
            ignored.append(value)

effective_ignored = sorted({*default_ignored, *ignored})


def is_ignored(path: Path) -> bool:
    return any(part in effective_ignored for part in path.parts)

raw_tree = []
effective_tree = []
raw_index_files = []
raw_leaf_files = []
effective_index_files = []
effective_leaf_files = []

if spec_root.is_dir():
    for path in sorted(spec_root.rglob('*')):
        if path.name.startswith('.'):
            continue
        rel = path.relative_to(spec_root).as_posix()
        depth = len(path.relative_to(spec_root).parts)
        entry = {'path': rel, 'type': 'dir' if path.is_dir() else 'file', 'depth': depth}
        raw_tree.append(entry)
        if not is_ignored(path.relative_to(spec_root)):
            effective_tree.append(entry)

        if path.is_file() and path.suffix == '.md':
            if rel != '.adapter-ignore':
                if path.name == 'index.md':
                    raw_index_files.append(rel)
                    if not is_ignored(path.relative_to(spec_root)):
                        effective_index_files.append(rel)
                else:
                    raw_leaf_files.append(rel)
                    if not is_ignored(path.relative_to(spec_root)):
                        effective_leaf_files.append(rel)

payload = {
    'adapter': {
        'name': manifest['name'],
        'version': manifest['version'],
        'description': manifest['description'],
    },
    'target': {
        'repoRoot': str(repo_root),
        'superpowersPath': str(target_dir),
        'exists': target_dir.is_dir(),
    },
    'installState': {
        'generatedMarker': marker,
        'installedFiles': installed,
        'missingFiles': missing,
    },
    'patchedState': hook_states,
    'specState': {
        'specRoot': str(spec_root),
        'exists': spec_root.is_dir(),
        'entryIndexExists': entry_index.is_file(),
        'ignoreFileExists': ignore_file.is_file(),
        'defaultIgnoredDirectories': default_ignored,
        'customIgnoredDirectories': ignored,
        'effectiveIgnoredDirectories': effective_ignored,
        'rawView': {
            'indexFiles': raw_index_files,
            'leafFiles': raw_leaf_files,
            'tree': raw_tree,
        },
        'effectiveView': {
            'indexFiles': effective_index_files,
            'leafFiles': effective_leaf_files,
            'tree': effective_tree,
        },
    },
    'verify': {
        'status': verify_status,
    },
}
print(json.dumps(payload, indent=2))
PY
)

if [[ -n "$OUTPUT_PATH" ]]; then
  printf '%s\n' "$MANIFEST_JSON" > "$OUTPUT_PATH"
  printf 'Exported manifest to %s\n' "$OUTPUT_PATH"
else
  printf '%s\n' "$MANIFEST_JSON"
fi
