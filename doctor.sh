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
MANIFEST_PATH="$SCRIPT_DIR/manifest.json"

VERIFY_STATUS="passed"
if ! "$SCRIPT_DIR/verify.sh" "$TARGET_INPUT" >/dev/null 2>&1; then
  VERIFY_STATUS="failed"
fi

MANIFEST_JSON="$($SCRIPT_DIR/export-manifest.sh "$TARGET_INPUT" "$REPO_ROOT")"

python3 - <<'PY' "$MANIFEST_PATH" "$TARGET_DIR" "$VERIFY_STATUS" "$MANIFEST_JSON"
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
target = Path(sys.argv[2])
verify_status = sys.argv[3]
state = json.loads(sys.argv[4])

installed = 0
missing = []
for rel in manifest['installedPaths']:
    path = target / rel
    if path.is_file():
        installed += 1
    else:
        missing.append(rel)

spec = state['specState']
raw_leaf_count = len(spec['rawView']['leafFiles'])
effective_leaf_count = len(spec['effectiveView']['leafFiles'])
missing_entry = not spec['entryIndexExists'] and spec['exists']
ignore_present_but_empty = spec['ignoreFileExists'] and not spec['customIgnoredDirectories']
diff_count = raw_leaf_count - effective_leaf_count
missing_index_links = []
for leaf in spec['effectiveView']['leafFiles']:
    parent = Path(leaf).parent
    if str(parent) == '.':
        continue
    expected = f"{parent.as_posix()}/index.md"
    if expected not in spec['effectiveView']['indexFiles']:
        missing_index_links.append(leaf)

print('Adapter doctor')
print(f"  adapter: {manifest['name']}@{manifest['version']}")
print(f"  target: {target}")
print(f"  installState: {'OK' if not missing else 'FAIL'} ({installed}/{len(manifest['installedPaths'])} managed files present)")
print(f"  verifyState: {'OK' if verify_status == 'passed' else 'FAIL'}")
for rel in manifest.get('optionalPatchedPaths', []):
    print(f"  patchTarget: {rel} -> {'present' if (target / rel).is_file() else 'missing'}")
print(f"  specState: {'OK' if spec['exists'] else 'WARN'}")
print(f"  specEntryIndex: {'OK' if spec['entryIndexExists'] else 'WARN'}")
print(f"  specIgnoredDirs: {len(spec['effectiveIgnoredDirectories'])} effective ({len(spec['customIgnoredDirectories'])} custom)")
print(f"  specLeafs: raw={raw_leaf_count} effective={effective_leaf_count}")

print('')
print('Recommendations')
if missing:
    for rel in missing:
        print(f'  - Missing managed file: {rel}')
    print(f'  - Run: {target.parent / "superpower-adapter" / "install.sh"} {target.parent}')
if missing_entry:
    print('  - .superpowers/spec exists but index.md is missing. Run bootstrap-spec or recreate the entry index.')
if ignore_present_but_empty:
    print('  - .adapter-ignore exists but has no custom entries. Remove it if unused or add custom ignored directory names.')
if diff_count > 0:
    print(f'  - rawView has {diff_count} more leaf specs than effectiveView. Review ignored directories if that is unexpected.')
if missing_index_links:
    print('  - Some effective leaf specs do not have a matching parent index.md in the effective view:')
    for leaf in missing_index_links:
        print(f'    - {leaf}')
if not any([missing, missing_entry, ignore_present_but_empty, diff_count > 0, missing_index_links]):
    print('  - No action needed. Adapter looks healthy.')
PY

if [[ "$VERIFY_STATUS" != "passed" ]]; then
  printf '\nverify.sh failed. Run ./superpower-adapter/manage.sh verify for details.\n'
  exit 1
fi
